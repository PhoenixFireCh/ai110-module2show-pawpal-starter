from pawpal_system import Priority, Recurrence, TimeWindow, Pet, Owner, Task, Schedule, Scheduler

from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum

acc = Scheduler(Owner("Harrison", TimeWindow(time(6, 00), time(20, 45))))
acc.add_pet("Bon", "Dog", "German Shepard", 3.3, "Brown", "Male","Bold boi")
acc.add_pet("Alex", "Cat", "Calico", 2.2, "Orange", "Female")
acc.add_task("Wash Bon", Priority.HIGH, Recurrence.DAILY, TimeWindow(time(18, 45), time(19, 00)), acc.pets[0])
acc.add_task("Play with Alex", Priority.LOW, Recurrence.DAILY, TimeWindow(time(13, 30), time(14, 30)), acc.pets[1])
acc.add_task("Walk Bon", Priority.MEDIUM, Recurrence.DAILY, TimeWindow(time(11, 00), time(13, 30)), acc.pets[0])
acc.add_task("Feed Alex", Priority.HIGH, Recurrence.DAILY, TimeWindow(time(4, 00), time(4, 30)), acc.pets[1])
acc.add_task("Groom Alex", Priority.MEDIUM, Recurrence.DAILY, TimeWindow(time(8, 00), time(9, 00)), acc.pets[1])
acc.add_task("Take Bon to Training", Priority.HIGH, Recurrence.WEEKLY, TimeWindow(time(8, 30), time(9, 30)), acc.pets[0], date(2026, 6, 29))
acc.add_task("Take Alex to Fair", Priority.HIGH, Recurrence.NONE, TimeWindow(time(8, 30), time(9, 30)), acc.pets[0], date(2026, 6, 30))
acc.create_schedule(date.today()).print_plan()