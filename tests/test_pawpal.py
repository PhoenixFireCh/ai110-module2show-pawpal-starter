"""Small pytest checks for core PawPal+ behaviors."""

from datetime import time

from pawpal_system import Scheduler, Owner, Priority, Recurrence, TimeWindow, Task


def test_toggle_complete_changes_status():
    """toggle_complete should flip a task's completed status."""
    task = Task("Walk Bon", Priority.LOW)
    assert task.completed is False
    task.toggle_complete()
    assert task.completed is True


def test_add_task_with_valid_pet():
    """Adding a task with a valid pet should store the task and keep that pet attached."""
    acc = Scheduler(Owner("Harrison", TimeWindow(time(6, 0), time(20, 0))))
    acc.add_pet("Alex", "Cat", "Calico", 2.2, "Orange", "Female")
    pet = acc.pets[0]

    acc.add_task("Feed Alex", Priority.HIGH, Recurrence.DAILY, pet=pet)

    assert len(acc.tasks) == 1
    assert acc.tasks[0].title == "Feed Alex"
    assert acc.tasks[0].pet is pet
