"""Agentic scheduling for PawPal+.

The UI and the ``Schedule`` class delegate schedule creation to a
``ScheduleAgent``. Two implementations ship here:

- ``HeuristicScheduleAgent`` — the original deterministic greedy planner. No
  network, no key; always keeps the user's entered time windows. This is the
  offline fallback and preserves the exact behaviour the app had before.
- ``GeminiScheduleAgent`` — an LLM-backed agent (Google AI Studio's Gemini
  API). It reads the current pet tasks plus a free-text instruction and,
  depending on what the user asks for, either keeps the entered time windows
  or proposes a recommended day plan.

Both return a ``ScheduleResult`` (entries / removed / reasoning / scheduled_date),
which is exactly what ``Schedule`` needs to expose. The generated-schedule output
format is therefore unchanged — ``entries`` is still a list of ``Task`` objects
and ``removed`` is still a list of ``(Task, reason)`` tuples.

The LLM agent has no input guardrails: every task is offered to the model, which
resolves the day the user is asking about (``today``, ``tomorrow``, ``the day
after``, an explicit date, …) relative to today's date and decides which tasks
occur on that day. The only always-on guardrail is ``_OutputSanitizer`` — the
sole output check — which drops entries that fall outside the owner's
availability or overlap another entry.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime, time

# NOTE: pawpal_system imports this module lazily (inside Schedule.generate_plan)
# to avoid a circular import, so importing from it at module load is safe here.
from pawpal_system import Owner, Priority, Recurrence, Task, TimeWindow

MODEL = "gemini-flash-latest"


@dataclass
class ScheduleResult:
    """What an agent produces for a given day.

    Mirrors the attributes ``Schedule`` exposes so the UI renders identically:
    ``entries`` are the chosen ``Task`` objects, ``removed`` pairs each dropped
    task with a human-readable reason, and ``reasoning`` explains the plan.
    ``scheduled_date`` is the day the agent actually planned for — the LLM agent
    resolves it from the user's instruction (e.g. "tomorrow"); it is ``None`` when
    the agent simply used the day it was given (the offline planner).
    """

    entries: list[Task] = field(default_factory=list)
    removed: list = field(default_factory=list)
    reasoning: str = ""
    scheduled_date: date | None = None


class ScheduleAgent:
    """Abstract base: turn (day, owner, tasks, instruction) into a plan."""

    def plan(self, day: date, owner: Owner, tasks: list[Task], instruction: str) -> ScheduleResult:
        raise NotImplementedError


def _day_activity_reason(task: Task, day: date) -> str | None:
    """Return why ``task`` is not due on ``day``, or None if it is due.

    Used only by the offline ``HeuristicScheduleAgent``, which has no language
    understanding and so plans for the day it is handed (today). The LLM agent
    does its own day resolution from the user's instruction instead. A task needs
    a time window, must be pending (a completed recurring task counts as pending
    again once ``day`` falls in a new period than when it was last completed),
    and its recurrence/date must land on ``day``.
    """
    if task.time_window is None:
        return "no time window set"
    # Completed tasks are only due again in a new recurrence period.
    if task.completed:
        due_again = (
            task.repeats is Recurrence.DAILY
            and task.last_completed is not None
            and task.last_completed < day
        ) or (
            task.repeats is Recurrence.WEEKLY
            and task.last_completed is not None
            and task.last_completed.isocalendar()[:2] < day.isocalendar()[:2]
        )
        if not due_again:
            return "already completed"
    # The task's recurrence/date must match the schedule's day.
    if task.repeats is Recurrence.DAILY:
        return None
    if task.repeats is Recurrence.NONE:
        if task.task_date == day:
            return None
        return f"dated {task.task_date}, not {day}"
    # Weekly: due only on the same weekday as its task_date.
    if task.task_date is not None and task.task_date.weekday() == day.weekday():
        return None
    weekday = task.task_date.strftime("%A") + "s" if task.task_date else "an unset weekday"
    return f"repeats weekly on {weekday}, but {day} is a {day.strftime('%A')}"


# ---------------------------------------------------------------------------
# Heuristic agent — the original greedy algorithm, moved out of Schedule.
# ---------------------------------------------------------------------------
class HeuristicScheduleAgent(ScheduleAgent):
    """Deterministic offline planner (no LLM, no API key).

    This is the verbatim behaviour the app shipped with: keep tasks active on
    ``day``, drop those outside the owner's availability, then greedily pack
    non-overlapping tasks with higher priority first and, within a priority,
    earliest finish time first. It ignores ``instruction`` (it has no language
    understanding) and always keeps each task's entered ``time_window``.
    """

    def plan(self, day: date, owner: Owner, tasks: list[Task], instruction: str) -> ScheduleResult:
        entries: list[Task] = []
        removed: list = []
        # Rank priorities so HIGH outranks MEDIUM outranks LOW.
        rank = {Priority.LOW: 0, Priority.MEDIUM: 1, Priority.HIGH: 2}

        # Keep only tasks due on this day — the shared day-activity rules
        # (pending, window set, recurrence/date landing on `day`). Read-only:
        # never unmarks a task's completed flag.
        active = [task for task in tasks if _day_activity_reason(task, day) is None]

        # Drop active tasks that fall outside the owner's availability, recording the reason.
        candidates = []
        for task in active:
            if owner.availability.contains(task.time_window.start) and owner.availability.contains(
                task.time_window.end
            ):
                candidates.append(task)
            else:
                removed.append((task, "outside the owner's availability window"))

        # Highest priority first; within a priority, earliest end time maximizes how many fit.
        candidates.sort(key=lambda task: (-rank[task.priority], task.time_window.end))

        # Greedily add each task unless it overlaps one already chosen; record the clash otherwise.
        for task in candidates:
            conflict = next(
                (
                    entry
                    for entry in entries
                    if task.time_window.start < entry.time_window.end
                    and entry.time_window.start < task.time_window.end
                ),
                None,
            )
            if conflict is None:
                entries.append(task)
            else:
                removed.append((task, f"overlaps with '{conflict.title}'"))

        reasoning = (
            "Offline planner (no AI key set): kept your entered times and packed the "
            "highest-priority, non-overlapping tasks first, preferring earlier finish "
            "times so more tasks fit. Tasks outside your availability or that clash with "
            "a higher-priority task were dropped."
        )
        return ScheduleResult(entries=entries, removed=removed, reasoning=reasoning)


# ---------------------------------------------------------------------------
# LLM agent — Google Gemini (Google AI Studio).
# ---------------------------------------------------------------------------
# Structured-output schema: the model returns the date it resolved from the
# user's instruction plus, for each scheduled task, its index into the task list
# and the start/end times it wants, so we can map its answer back onto real Task
# objects.
SCHEDULE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["scheduled_date", "reasoning", "entries", "removed"],
    "properties": {
        "scheduled_date": {"type": "string"},  # "YYYY-MM-DD" — the resolved day
        "reasoning": {"type": "string"},
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["task_index", "start", "end"],
                "properties": {
                    "task_index": {"type": "integer"},
                    "start": {"type": "string"},  # "HH:MM"
                    "end": {"type": "string"},  # "HH:MM"
                },
            },
        },
        "removed": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["task_index", "reason"],
                "properties": {
                    "task_index": {"type": "integer"},
                    "reason": {"type": "string"},
                },
            },
        },
    },
}


class GeminiScheduleAgent(ScheduleAgent):
    """LLM-backed planner using Google Gemini (Google AI Studio API).

    Describes today's date, the owner's availability, and every task (by index,
    with its recurrence/date/completion) to the model along with the user's
    instruction. The model resolves which calendar day the user is asking about
    ("tomorrow", "the day after", an explicit date, …) relative to today, decides
    which tasks occur on that day, and returns a structured answer that is mapped
    back onto real ``Task`` objects. If the user asks for a "recommended" plan the
    model may propose new times; if they ask to use their entered times it keeps
    each task's ``time_window``. There are no input guardrails; the only output
    guard is availability + no-overlap.

    On any API or parsing failure it degrades gracefully to
    ``HeuristicScheduleAgent`` and notes the fallback in ``reasoning`` so the app
    never crashes on a bad key or a network error.
    """

    def __init__(self, api_key: str | None = None, model: str = MODEL):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        self.model = model
        # There are no input guardrails: every task is offered to the model. The
        # sole output guardrail is the sanitizer, which enforces the owner's
        # availability and no-overlap on whatever the model returns.
        self._sanitizer = _OutputSanitizer()

    def plan(self, today: date, owner: Owner, tasks: list[Task], instruction: str) -> ScheduleResult:
        try:
            from google import genai
        except ImportError:
            return self._fallback(
                today, owner, tasks, instruction,
                "The `google-genai` package is not installed, so the offline planner was used.",
            )

        if not self.api_key:
            return self._fallback(
                today, owner, tasks, instruction,
                "No Google AI Studio API key was available, so the offline planner was used.",
            )

        # Resolves the requested day from the instruction (relative to today) and decides
        # which tasks occur on that day.
        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=self._user_prompt(today, owner, tasks, instruction),
                config={
                    "system_instruction": self._system_prompt(),
                    # Constrain the reply to JSON matching our schema.
                    "response_mime_type": "application/json",
                    "response_json_schema": SCHEDULE_SCHEMA,
                },
            )
            raw = response.text or ""
        except Exception as exc:  # network, auth, rate limit, etc.
            return self._fallback(
                today, owner, tasks, instruction,
                f"The AI request failed ({type(exc).__name__}), so the offline planner was used.",
            )

        try:
            data = json.loads(_strip_code_fences(raw))
        except (json.JSONDecodeError, TypeError):
            return self._fallback(
                today, owner, tasks, instruction,
                "The AI returned output that could not be parsed, so the offline planner was used.",
            )

        result = self._build_result(data, tasks, today)
        # Sole output guardrail: availability + no-overlap. Day matching is the
        # model's responsibility now, so nothing here re-checks the date.
        return self._sanitizer.validate(result, today, owner, tasks)

    # -- prompt construction -------------------------------------------------
    def _system_prompt(self) -> str:
        return (
            "You are PawPal+, a pet-care scheduling assistant. You are given today's "
            "date, a pet owner's daily availability window, and a numbered list of ALL "
            "of the owner's care tasks (each with its recurrence, date, completion "
            "status, and entered time). Build the best day plan you can and return it "
            "as JSON matching the provided schema.\n\n"
            "STEP 1 — resolve the day. Read the user's instruction and work out which "
            "calendar day they want a schedule for, RELATIVE TO TODAY'S DATE:\n"
            "  - 'today' = today's date; 'tomorrow' = today + 1 day; 'the day after "
            "tomorrow' / 'the day after' = today + 2 days; 'in N days' = today + N days.\n"
            "  - A weekday name ('Monday', 'next Friday') = the next occurrence of that "
            "weekday on or after today.\n"
            "  - An explicit date, in any format ('8/5/2026', '2026-08-05', 'August 5') "
            "= that exact date.\n"
            "  - If the instruction names no day, default to today.\n"
            "  Put the resolved day in `scheduled_date` as 'YYYY-MM-DD'. Compute it "
            "yourself from today's date — never assume today.\n\n"
            "STEP 2 — pick the tasks that occur on the resolved day:\n"
            "  - A 'daily' task occurs EVERY day, so it always occurs on the resolved day.\n"
            "  - A 'weekly' task occurs only on the same weekday as its listed date. "
            "Include it only if the resolved day falls on that weekday.\n"
            "  - A 'none' (singular/one-off) task occurs only on its exact listed date. "
            "Include it only if that date equals the resolved day.\n"
            "  - Exclude any task that does NOT occur on the resolved day, and any task "
            "already completed for that day (a daily task completed today is done for "
            "today but due again tomorrow; a weekly task completed this week is done for "
            "this week). Put every excluded task in `removed` with a short reason.\n\n"
            "STEP 3 — schedule the included tasks:\n"
            "  - Scheduled tasks must fit within the owner's availability window and must "
            "not overlap each other.\n"
            "  - If the user asks to use the times they entered, keep each task's given "
            "start/end. If the user asks for a recommended plan (e.g. spacing out walks "
            "and feedings), you may choose better start/end times, but stay within "
            "availability.\n"
            "  - Respect task priority (high > medium > low) when time is tight; drop the "
            "lower-priority task into `removed` when two clash.\n"
            "  - Refer to each task by its integer index. Times are 24-hour 'HH:MM'.\n"
            "  - Explain your day resolution and choices briefly in `reasoning`."
        )

    def _user_prompt(
        self,
        today: date,
        owner: Owner,
        tasks: list[Task],
        instruction: str,
    ) -> str:
        avail = owner.availability
        lines = [
            f"Today's date: {today.isoformat()} ({today.strftime('%A')})",
            f"Owner: {owner.name}",
            f"Availability: {avail.start.strftime('%H:%M')}-{avail.end.strftime('%H:%M')}",
            "",
            "All tasks (decide for yourself which occur on the day the user asks for):",
        ]
        for i, t in enumerate(tasks):
            window = (
                f"{t.time_window.start.strftime('%H:%M')}-{t.time_window.end.strftime('%H:%M')}"
                if t.time_window
                else "no time set"
            )
            pet = t.pet.name if t.pet else "no pet"
            if t.repeats is Recurrence.WEEKLY and t.task_date is not None:
                task_day = f"{t.task_date.isoformat()} ({t.task_date.strftime('%A')})"
            else:
                task_day = t.task_date.isoformat() if t.task_date else "-"
            completed = "yes" if t.completed else "no"
            last_done = t.last_completed.isoformat() if t.last_completed else "never"
            lines.append(
                f"[{i}] {t.title} | pet: {pet} | priority: {t.priority.value} | "
                f"repeats: {t.repeats.value} | date: {task_day} | entered time: {window} | "
                f"completed: {completed} | last completed: {last_done}"
            )
        lines.append("")
        lines.append(f"User instruction: {instruction.strip() or '(no instruction given)'}")
        return "\n".join(lines)

    # -- response mapping ----------------------------------------------------
    def _build_result(self, data: dict, tasks: list[Task], today: date) -> ScheduleResult:
        entries: list[Task] = []
        for item in data.get("entries", []):
            idx = item.get("task_index")
            if not isinstance(idx, int) or not (0 <= idx < len(tasks)):
                continue  # sanitizer-style guard: skip out-of-range indices
            base = tasks[idx]
            start = _parse_time(item.get("start"))
            end = _parse_time(item.get("end"))
            if start is None or end is None or start >= end:
                # Fall back to the entered window if the model's times are unusable.
                if base.time_window is None:
                    continue
                entries.append(base)
                continue
            if base.time_window and base.time_window.start == start and base.time_window.end == end:
                entries.append(base)  # unchanged — reuse the original task
            else:
                # Recommended (or newly-set) time: build a copy with a fresh window.
                entries.append(
                    Task(
                        base.title,
                        base.priority,
                        base.repeats,
                        time_window=TimeWindow(start, end),
                        pet=base.pet,
                        task_date=base.task_date,
                    )
                )

        removed: list = []
        for item in data.get("removed", []):
            idx = item.get("task_index")
            if isinstance(idx, int) and 0 <= idx < len(tasks):
                removed.append((tasks[idx], str(item.get("reason", "not scheduled"))))

        return ScheduleResult(
            entries=entries,
            removed=removed,
            reasoning=str(data.get("reasoning", "")),
            # The day the model resolved from the instruction; falls back to today
            # if the model returned an unparseable/absent date.
            scheduled_date=_parse_iso_date(data.get("scheduled_date")) or today,
        )

    def _fallback(
        self, day: date, owner: Owner, tasks: list[Task], instruction: str, note: str
    ) -> ScheduleResult:
        result = HeuristicScheduleAgent().plan(day, owner, tasks, instruction)
        result.reasoning = f"{note}\n\n{result.reasoning}"
        return result


class _OutputSanitizer:
    """Always-on output guard used by the LLM agent.

    Protects the display by dropping entries that fall outside the owner's
    availability or overlap an earlier entry — the same invariants the offline
    planner guarantees. Dropped entries are moved into ``removed`` with a reason.
    """

    def validate(
        self, result: ScheduleResult, owner: Owner
    ) -> ScheduleResult:
        kept: list[Task] = []
        removed = list(result.removed)
        for entry in result.entries:
            tw = entry.time_window
            if tw is None:
                removed.append((entry, "no time window"))
                continue
            if not (owner.availability.contains(tw.start) and owner.availability.contains(tw.end)):
                removed.append((entry, "outside the owner's availability window"))
                continue
            conflict = next(
                (
                    e
                    for e in kept
                    if tw.start < e.time_window.end and e.time_window.start < tw.end
                ),
                None,
            )
            if conflict is None:
                kept.append(entry)
            else:
                removed.append((entry, f"overlaps with '{conflict.title}'"))
        result.entries = kept
        result.removed = removed
        return result


def _strip_code_fences(text: str) -> str:
    """Return the JSON payload with any wrapping ```/```json markdown fence removed."""
    stripped = text.strip()
    if stripped.startswith("```"):
        # Drop the opening fence line (``` or ```json) and any closing fence.
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[: -len("```")]
    return stripped.strip()


def _parse_time(value) -> time | None:
    """Parse a 'HH:MM' string into a time, or None if it can't be parsed."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except ValueError:
        return None


def _parse_iso_date(value) -> date | None:
    """Parse a 'YYYY-MM-DD' string into a date, or None if it can't be parsed."""
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None
