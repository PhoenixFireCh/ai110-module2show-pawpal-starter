"""PawPal+ domain model — class stubs (no logic yet).

Generated from diagrams/uml.mmd. These stubs define the structure that app.py
(the Streamlit UI) imports and calls. Implement method bodies incrementally.

Suggested usage from app.py:
    from logic import Owner, Pet, Task, Schedule, Priority, Recurrence, TimeWindow

    owner = Owner(name="Jordan", availability=TimeWindow(time(8, 0), time(17, 0)))
    schedule = Schedule(day=date.today(), owner=owner)
    schedule.generate_plan(tasks)        # builds schedule.entries from tasks
    for entry in schedule.entries:       # render entry.start_time / entry.task ...
        ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from enum import Enum


class Priority(Enum):
    """Relative importance of a task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Recurrence(Enum):
    """How often a task repeats."""

    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class TimeWindow:
    """A span of time, e.g. an owner's daily availability (8:00am–5:00pm)."""

    start: time
    end: time

    def duration_minutes(self) -> int:
        """Total minutes between start and end."""
        raise NotImplementedError

    def contains(self, t: time) -> bool:
        """True if t falls within [start, end]."""
        raise NotImplementedError


@dataclass
class Pet:
    """A pet being cared for."""

    name: str
    species: str
    breed: str
    height: float
    color: str
    extra_info: str = ""

    def describe(self) -> str:
        """Human-readable summary of the pet."""
        raise NotImplementedError


@dataclass
class Owner:
    """The pet owner and their availability constraints."""

    name: str
    availability: TimeWindow
    time_constraint: time
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Associate a pet with this owner."""
        raise NotImplementedError

    def available_minutes(self) -> int:
        """Minutes available for care tasks, derived from availability/constraints."""
        raise NotImplementedError


@dataclass
class Task:
    """A unit of pet care to be scheduled (walk, feeding, meds, etc.)."""

    title: str
    priority: Priority
    duration_minutes: int
    repeats: Recurrence = Recurrence.NONE
    completed: bool = False

    def toggle_complete(self) -> None:
        """Flip the completed flag."""
        raise NotImplementedError


@dataclass
class PlanEntry:
    """A task placed at a concrete time slot within a schedule."""

    task: Task
    start_time: time
    end_time: time


@dataclass
class Schedule:
    """A day's plan. Building it generates entries from an input list of tasks."""

    day: date
    owner: Owner
    entries: list[PlanEntry] = field(default_factory=list)

    def generate_plan(self, tasks: list[Task]) -> None:
        """Populate self.entries from tasks, honoring owner availability/priority."""
        raise NotImplementedError

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks ordered by priority (highest first)."""
        raise NotImplementedError

    def filter_by_time(self, tasks: list[Task], available: int) -> list[Task]:
        """Return the subset of tasks that fit within `available` minutes."""
        raise NotImplementedError

    def resolve_conflicts(self, entries: list[PlanEntry]) -> list[PlanEntry]:
        """Return entries with overlapping time slots resolved."""
        raise NotImplementedError

    def add_entry(self, entry: PlanEntry) -> None:
        """Append a single plan entry to the schedule."""
        raise NotImplementedError

    def total_minutes(self) -> int:
        """Total minutes consumed by all scheduled entries."""
        raise NotImplementedError

    def explain(self) -> str:
        """Human-readable explanation of why the plan looks the way it does."""
        raise NotImplementedError
