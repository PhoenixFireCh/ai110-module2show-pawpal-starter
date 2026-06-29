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
    repeats: Recurrence = Recurrence.NONE
    completed: bool = False
    time_window: TimeWindow | None = None
    pet: Pet | None = None

    def toggle_complete(self) -> None:
        """Flip the completed flag."""
        raise NotImplementedError


@dataclass
class Schedule:
    """A day's plan. Building it generates entries from an input list of tasks."""

    day: date
    owner: Owner
    entries: list[Task] = field(default_factory=list)

    def generate_plan(self, tasks: list[Task]) -> None:
        """Populate self.entries from tasks, honoring owner availability/priority."""
        raise NotImplementedError

    def add_entry(self, task: Task) -> None:
        """Append a single scheduled task to the schedule."""
        raise NotImplementedError

    def total_minutes(self) -> int:
        """Total minutes consumed by all scheduled entries."""
        raise NotImplementedError


@dataclass
class Account:
    """The current app instance: the owner, their pets, all tasks, and the plan."""

    owner: Owner
    pets: list[Pet] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    schedule: Schedule | None = None

    def add_pet(self, pet: Pet) -> None:
        """Track a new pet on this account."""
        raise NotImplementedError

    def add_task(self, task: Task) -> None:
        """Add a task to the unsorted task list."""
        raise NotImplementedError

    def create_schedule(self) -> Schedule:
        """Build the current schedule from the account's owner and tasks."""
        raise NotImplementedError
