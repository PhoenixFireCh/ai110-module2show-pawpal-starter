"""Agentic scheduling for PawPal+.

``Schedule`` delegates plan creation to one of two agents:

- ``HeuristicScheduleAgent`` — deterministic offline planner; keeps the
  user's entered time windows.
- ``GeminiScheduleAgent`` — LLM-backed planner (Gemini API); interprets the
  requested day from the user's instruction, may propose new times, and may
  invent temporary one-off tasks (never persisted to the Scheduler's task list).

Both return a ``ScheduleResult``. The only output guardrail is
``_OutputSanitizer``, which drops entries (including temporary ones) outside
the owner's availability or overlapping another entry, and strips any pet the
owner doesn't actually have.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime, time

# pawpal_system imports this module lazily, so this import is safe.
from pawpal_system import Owner, Pet, Priority, Recurrence, Task, TimeWindow

from agent_helper import (
    SCHEDULE_SCHEMA_WITH_NEW,
    _parse_iso_date,
    _parse_time,
    _strip_code_fences,
    _system_prompt,
)

MODEL = "gemini-flash-latest"

# Map priority strings back to the enum; default LOW for anything unexpected.
_PRIORITY_BY_NAME = {p.value: p for p in Priority}


@dataclass
class ScheduleResult:
    """An agent's plan: kept tasks, dropped (task, reason) pairs, reasoning,
    and the day planned for (``None`` when the agent used the given day)."""

    entries: list[Task] = field(default_factory=list)
    removed: list = field(default_factory=list)
    reasoning: str = ""
    scheduled_date: date | None = None


def _day_activity_reason(task: Task, day: date) -> str | None:
    """Return why ``task`` is not due on ``day``, or None if it is due.

    Used only by the offline planner. A task needs a time window, must be
    pending (recurring tasks become pending again in a new period), and its
    recurrence/date must land on ``day``.
    """
    if task.time_window is None:
        return "no time window set"
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
    if task.repeats is Recurrence.DAILY:
        return None
    if task.repeats is Recurrence.NONE:
        if task.task_date == day:
            return None
        return f"dated {task.task_date}, not {day}"
    # Weekly: due on the same weekday as task_date.
    if task.task_date is not None and task.task_date.weekday() == day.weekday():
        return None
    weekday = task.task_date.strftime("%A") + "s" if task.task_date else "an unset weekday"
    return f"repeats weekly on {weekday}, but {day} is a {day.strftime('%A')}"


class HeuristicScheduleAgent:
    """Deterministic offline planner (no LLM, no API key).

    Keeps tasks due on ``day``, drops those outside the owner's availability,
    then greedily packs non-overlapping tasks: higher priority first, earliest
    finish first. Ignores ``instruction`` and keeps entered time windows.
    """

    def plan(self, day: date, owner: Owner, tasks: list[Task], instruction: str) -> ScheduleResult:
        entries: list[Task] = []
        removed: list = []
        rank = {Priority.LOW: 0, Priority.MEDIUM: 1, Priority.HIGH: 2}

        # Keep only tasks due on this day.
        active = [task for task in tasks if _day_activity_reason(task, day) is None]

        # Drop tasks outside the owner's availability.
        candidates = []
        for task in active:
            if owner.availability.contains(task.time_window.start) and owner.availability.contains(
                task.time_window.end
            ):
                candidates.append(task)
            else:
                removed.append((task, "outside the owner's availability window"))

        # Highest priority first; within a priority, earliest end time first.
        candidates.sort(key=lambda task: (-rank[task.priority], task.time_window.end))

        # Add each task unless it overlaps one already chosen.
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


class GeminiScheduleAgent:
    """LLM-backed planner using Google Gemini.

    Sends the owner's availability, all tasks (by index), and the user's
    instruction to the model. No calendar date is given — the model interprets
    the requested day itself and returns a structured answer mapped back onto
    real ``Task`` objects. Falls back to ``HeuristicScheduleAgent`` on any API
    or parsing failure.
    """

    def __init__(self, api_key: str | None = None, model: str = MODEL):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        self.model = model
        # Sole output guardrail: availability + no-overlap.
        self._sanitizer = _OutputSanitizer()

    def plan(self, day: date, owner: Owner, tasks: list[Task], instruction: str) -> ScheduleResult:
        # `day` is used only by the offline fallback.
        try:
            from google import genai
        except ImportError:
            return self._fallback(
                day, owner, tasks, instruction,
                "The `google-genai` package is not installed, so the offline planner was used.",
            )

        if not self.api_key:
            return self._fallback(
                day, owner, tasks, instruction,
                "No Google AI Studio API key was available, so the offline planner was used.",
            )

        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=self._user_prompt(owner, tasks, instruction),
                config={
                    "system_instruction": self._system_prompt(),
                    "response_mime_type": "application/json",
                    "response_json_schema": SCHEDULE_SCHEMA_WITH_NEW,
                },
            )
            raw = response.text or ""
        except Exception as exc:  # network, auth, rate limit, etc.
            return self._fallback(
                day, owner, tasks, instruction,
                f"The AI request failed ({type(exc).__name__}), so the offline planner was used.",
            )

        try:
            data = json.loads(_strip_code_fences(raw))
        except (json.JSONDecodeError, TypeError):
            return self._fallback(
                day, owner, tasks, instruction,
                "The AI returned output that could not be parsed, so the offline planner was used.",
            )

        result = self._build_result(data, tasks)
        # Real pets the owner has, keyed by name — the sanitizer's anti-hallucination set.
        known_pets = {t.pet.name: t.pet for t in tasks if t.pet}
        return self._sanitizer.validate(result, owner, known_pets)

    # -- prompt construction -------------------------------------------------
    _system_prompt = staticmethod(_system_prompt)

    def _user_prompt(
        self,
        owner: Owner,
        tasks: list[Task],
        instruction: str,
    ) -> str:
        avail = owner.availability
        lines = [
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
    def _build_result(self, data: dict, tasks: list[Task]) -> ScheduleResult:
        entries: list[Task] = []
        for item in data.get("entries", []):
            idx = item.get("task_index")
            if not isinstance(idx, int) or not (0 <= idx < len(tasks)):
                continue  # skip out-of-range indices
            base = tasks[idx]
            start = _parse_time(item.get("start"))
            end = _parse_time(item.get("end"))
            if start is None or end is None or start >= end:
                # Unusable times: fall back to the entered window.
                if base.time_window is None:
                    continue
                entries.append(base)
                continue
            if base.time_window and base.time_window.start == start and base.time_window.end == end:
                entries.append(base)  # unchanged — reuse the original task
            else:
                # New time: build a copy with a fresh window.
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

        # Temporary AI-invented tasks: scheduled into this plan (and guardrailed
        # like any entry) but never added to the Scheduler's persistent task list.
        for item in data.get("new_entries", []):
            title = str(item.get("title", "")).strip()
            start = _parse_time(item.get("start"))
            end = _parse_time(item.get("end"))
            if not title or start is None or end is None or start >= end:
                continue  # unusable suggestion
            priority = _PRIORITY_BY_NAME.get(str(item.get("priority", "")).lower(), Priority.LOW)
            # Typed pet name is unverified here; the sanitizer drops hallucinated pets.
            name = str(item.get("pet", "")).strip()
            pet = Pet(name, "", "", 0.0, "", "") if name else None
            entries.append(Task(title, priority, time_window=TimeWindow(start, end), pet=pet))

        removed: list = []
        for item in data.get("removed", []):
            idx = item.get("task_index")
            if isinstance(idx, int) and 0 <= idx < len(tasks):
                removed.append((tasks[idx], str(item.get("reason", "not scheduled"))))

        return ScheduleResult(
            entries=entries,
            removed=removed,
            reasoning=str(data.get("reasoning", "")),
            # The day the model resolved from the instruction (None if unparseable).
            scheduled_date=_parse_iso_date(data.get("scheduled_date")),
        )

    def _fallback(
        self, day: date, owner: Owner, tasks: list[Task], instruction: str, note: str
    ) -> ScheduleResult:
        result = HeuristicScheduleAgent().plan(day, owner, tasks, instruction)
        result.reasoning = f"{note}\n\n{result.reasoning}"
        return result


class _OutputSanitizer:
    """Output guard for the LLM agent: drops entries outside the owner's
    availability or overlapping an earlier entry, moving them into ``removed``.
    Also strips any pet the owner doesn't actually have (anti-hallucination)."""

    def validate(
        self, result: ScheduleResult, owner: Owner, known_pets: dict[str, Pet] | None = None
    ) -> ScheduleResult:
        known_pets = known_pets or {}
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
                # Pet guardrail: resolve to the real pet, or drop a hallucinated name.
                if entry.pet is not None:
                    entry.pet = known_pets.get(entry.pet.name)
                kept.append(entry)
            else:
                removed.append((entry, f"overlaps with '{conflict.title}'"))
        result.entries = kept
        result.removed = removed
        return result
