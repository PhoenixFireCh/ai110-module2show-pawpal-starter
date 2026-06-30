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
from datetime import date, datetime, time
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
    """A span of time (8:00am–5:00pm)."""

    start: time
    end: time

    def duration_minutes(self) -> int:
        """Return the number of whole minutes spanned from start to end."""
        # Anchor both times to the same date so datetime can subtract them.
        delta = datetime.combine(date.min, self.end) - datetime.combine(date.min, self.start)
        return int(delta.total_seconds() // 60)

    def contains(self, t: time) -> bool:
        """Return True if time t lies within the inclusive range [start, end]."""
        return self.start <= t <= self.end


@dataclass
class Pet:
    """A pet being cared for."""

    name: str
    species: str
    breed: str
    height: float
    color: str
    gender: str
    extra_info: str = ""

    def describe(self) -> str:
        """Return a short human-readable summary string describing the pet."""
        summary = f"{self.name} is a {self.gender} {self.color} {self.breed} {self.species}, {self.height} ft tall"
        # Append any extra info only when it has been provided.
        if self.extra_info:
            summary += f" ({self.extra_info})"
        return summary


@dataclass
class Owner:
    """The pet owner and their availability constraints."""

    name: str
    availability: TimeWindow

    def available_minutes(self) -> int:
        """Return care-task minutes from the total duration of the availability TimeWindow."""
        return self.availability.duration_minutes()


@dataclass
class Task:
    """A unit of pet care to be scheduled (walk, feeding, meds, etc.)."""

    title: str
    priority: Priority
    repeats: Recurrence = Recurrence.NONE
    completed: bool = False
    time_window: TimeWindow | None = None
    pet: Pet | None = None
    # Calendar date for the task: the exact day for NONE, the weekday source for WEEKLY,
    # and ignored for DAILY (which only cares about time_window's time of day).
    task_date: date | None = None
    last_completed: date | None = None

    def toggle_complete(self) -> None:
        """Flip the completed flag, stamping today's date when marking done."""
        self.completed = not self.completed
        # Track when it was completed so recurring resets know the period start.
        self.last_completed = date.today() if self.completed else None

    def refresh_recurrence(self) -> None:
        """Reset completed to False once the daily/weekly recurrence period has elapsed."""
        # Nothing to reset if it was never completed or doesn't repeat.
        if self.last_completed is None or self.repeats is Recurrence.NONE:
            return
        today = date.today()
        if self.repeats is Recurrence.DAILY and self.last_completed < today:
            # A new day has started, so the daily task is due again.
            self.completed = False
            self.last_completed = None
        elif self.repeats is Recurrence.WEEKLY and self.last_completed.isocalendar()[:2] < today.isocalendar()[:2]:
            # A new ISO week has started, so the weekly task is due again.
            self.completed = False
            self.last_completed = None


@dataclass
class Schedule:
    """A day's plan. Building it generates entries from an input list of tasks."""

    day: date
    entries: list[Task] = field(default_factory=list)

    def generate_plan(self, owner: Owner, tasks: list[Task]) -> None:
        """Build self.entries to fit as many non-overlapping tasks as possible: higher-priority
        tasks claim slots first, and within each priority earliest-finishing tasks are preferred."""
        self.entries = []
        # Rank priorities so HIGH outranks MEDIUM outranks LOW.
        rank = {Priority.LOW: 0, Priority.MEDIUM: 1, Priority.HIGH: 2}

        # Keep only tasks that are incomplete, have a window, and fit inside the owner's window.
        # Recurrence also decides how task_date is used:
        #   DAILY  -> date ignored, scheduled every day on its time_window.
        #   NONE   -> kept only on its exact date.
        #   WEEKLY -> kept only when its date's weekday matches the schedule's weekday.
        candidates = [
            task
            for task in tasks
            if not task.completed
            and task.time_window is not None
            and owner.availability.contains(task.time_window.start)
            and owner.availability.contains(task.time_window.end)
            and (
                task.repeats is Recurrence.DAILY
                or (task.repeats is Recurrence.NONE and task.task_date == self.day)
                or (
                    task.repeats is Recurrence.WEEKLY
                    and task.task_date is not None
                    and task.task_date.weekday() == self.day.weekday()
                )
            )
        ]

        # Highest priority first; within a priority, earliest end time maximizes how many fit.
        candidates.sort(key=lambda task: (-rank[task.priority], task.time_window.end))

        # Greedily add each task unless its window overlaps one already chosen.
        for task in candidates:
            overlaps = any(
                task.time_window.start < entry.time_window.end
                and entry.time_window.start < task.time_window.end
                for entry in self.entries
            )
            if not overlaps:
                self.entries.append(task)

    def total_minutes(self) -> int:
        """Total minutes consumed by all scheduled entries."""
        return sum(entry.time_window.duration_minutes() for entry in self.entries)

    def print_plan(self) -> None:
        """Print a separate daily plan per pet, each listing only that pet's tasks."""
        # Collect each distinct pet in first-seen order so every pet gets its own section.
        pets = []
        for entry in self.entries:
            if not any(entry.pet is p for p in pets):
                pets.append(entry.pet)
        # Print one headed section per pet, listing only that pet's entries.
        for pet in pets:
            if pet is not None:
                print(f"Daily plan for {pet.name} ({pet.breed}):")
            else:
                print(f"Daily plan for {self.day}:")
            for entry in self.entries:
                if entry.pet is pet:
                    start = entry.time_window.start.strftime("%H:%M")
                    minutes = entry.time_window.duration_minutes()
                    print(f"  {start} — {entry.title} ({minutes} min) [priority: {entry.priority.value}]")


@dataclass
class Account:
    """The current app instance: the owner, their pets, all tasks, and the plan."""

    owner: Owner
    pets: list[Pet] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    schedule: Schedule | None = None

    def add_pet(
        self,
        name: str,
        species: str,
        breed: str,
        height: float,
        color: str,
        gender: str,
        extra_info: str = "",
    ) -> None:
        """Build a Pet from the given details and track it on this account."""
        self.pets.append(Pet(name, species, breed, height, color, gender, extra_info))

    def add_task(
        self,
        title: str,
        priority: Priority,
        repeats: Recurrence = Recurrence.NONE,
        time_window: TimeWindow | None = None,
        pet: Pet | None = None,
        task_date: date | None = None,
    ) -> None:
        """Build a Task from the given details and add it to the unsorted task list.

        A date is required for one-off (NONE) and weekly tasks; daily tasks ignore it.
        """
        if repeats in (Recurrence.NONE, Recurrence.WEEKLY) and task_date is None:
            raise ValueError(f"A {repeats.value} task requires a date.")
        self.tasks.append(
            Task(title, priority, repeats, time_window=time_window, pet=pet, task_date=task_date)
        )

    def create_schedule(self) -> Schedule:
        """Build today's schedule from the owner and tasks, store it, and return it."""
        schedule = Schedule(day=date.today())
        schedule.generate_plan(self.owner, self.tasks)
        self.schedule = schedule
        return schedule
