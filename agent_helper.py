"""Shared helpers for ``schedule_agent`` — the Gemini response schema, the
system prompt, and small parsing utilities. Kept dependency-free (datetime only)
so importing it never risks a circular import."""

from __future__ import annotations

from datetime import date, datetime, time

# JSON schema the model must return: the resolved date, plus each scheduled and
# removed task by index (scheduled ones also carry HH:MM start/end).
SCHEDULE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["scheduled_date", "reasoning", "entries", "removed"],
    "properties": {
        "scheduled_date": {"type": "string"},  # "YYYY-MM-DD"
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


# A brand-new task the model may propose (no existing index; carries its own title).
_NEW_ENTRY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "priority", "start", "end"],
    "properties": {
        "title": {"type": "string"},
        "priority": {"type": "string"},  # low | medium | high
        "start": {"type": "string"},  # "HH:MM"
        "end": {"type": "string"},  # "HH:MM"
        "pet": {"type": "string"},  # optional: an existing pet's name
    },
}

# SCHEDULE_SCHEMA plus a `new_entries` array for the model's temporary tasks.
SCHEDULE_SCHEMA_WITH_NEW = {
    **SCHEDULE_SCHEMA,
    "required": [*SCHEDULE_SCHEMA["required"], "new_entries"],
    "properties": {
        **SCHEDULE_SCHEMA["properties"],
        "new_entries": {"type": "array", "items": _NEW_ENTRY_SCHEMA},
    },
}


def _system_prompt() -> str:
    """System instruction driving the Gemini scheduling agent."""
    return (
        "You are PawPal+, a pet-care scheduler. You get the owner's daily "
        "availability and a numbered list of ALL their tasks (recurrence, date, "
        "completion, entered time). Return a JSON day plan matching the schema.\n\n"
        "1. DAY: resolve the day the instruction asks for — interpret relative "
        "phrases ('tomorrow', a weekday) or explicit dates yourself; default to "
        "today. Put it in `scheduled_date` as 'YYYY-MM-DD'.\n"
        "2. PICK tasks due that day: daily = every day; weekly = only its listed "
        "weekday; none = only its exact date. Exclude tasks not due that day or "
        "already completed for the period; list each in `removed` with a reason.\n"
        "3. SCHEDULE the rest within availability, no overlaps unless stated in the instruction. "
        "Keep entered times unless the user asks you to recommend new ones. On a clash keep the higher "
        "priority (high>medium>low) and drop the other into `removed`. Reference "
        "tasks by integer index; use 24-hour 'HH:MM'. Explain briefly in "
        "`reasoning`.\n"
        "4. NEW TASKS: only if the instruction explicitly asks you to add a task, "
        "put it in `new_entries` (title, priority, 'HH:MM' start/end within "
        "availability, no overlaps; optional `pet` = an exact name from the list, "
        "else omit). Otherwise `new_entries` must be empty."
    )


def _strip_code_fences(text: str) -> str:
    """Return the JSON payload with any wrapping ```/```json markdown fence removed."""
    stripped = text.strip()
    if stripped.startswith("```"):
        # Drop the opening fence line and any closing fence.
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
