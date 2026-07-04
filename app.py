import streamlit as st

from datetime import date, time

from pawpal_system import Scheduler, Owner, TimeWindow, Priority, Recurrence

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Plan daily pet care tasks for an owner and their pets.")

with st.expander("Scenario", expanded=False):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and recurrence.
"""
    )

st.divider()

st.subheader("Account Setup")

if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler(Owner("Jordan", TimeWindow(time(8, 0), time(17, 0))))

scheduler = st.session_state.scheduler

owner_name = st.text_input("Owner name", value=scheduler.owner.name)
avail_cols = st.columns(2)
with avail_cols[0]:
    available_from = st.time_input("Available from", value=time(8, 0))
with avail_cols[1]:
    available_until = st.time_input("Available until", value=time(17, 0))
scheduler.owner = Owner(owner_name, TimeWindow(available_from, available_until))
# Warn when the availability window is invalid (start not before end).
owner_time_invalid = available_from >= available_until
if owner_time_invalid:
    st.warning("Invalid availability time: 'Available from' must be earlier than 'Available until'.")

st.markdown("#### Pets")
pet_cols = st.columns(3)
with pet_cols[0]:
    pet_name = st.text_input("Pet name", value="Mochi")
    pet_color = st.text_input("Color", value="brown")
with pet_cols[1]:
    pet_species = st.selectbox("Species", ["dog", "cat", "other"])
    pet_gender = st.selectbox("Gender", ["Male", "Female"])
with pet_cols[2]:
    pet_breed = st.text_input("Breed", value="Mixed")
    pet_height = st.number_input("Height (ft)", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
pet_extra = st.text_input("Extra info", value="")

if st.button("Add pet"):
    scheduler.add_pet(pet_name, pet_species, pet_breed, float(pet_height), pet_color, pet_gender, pet_extra)

if scheduler.pets:
    st.write("Pets on this account:")
    for pet in scheduler.pets:
        st.write("•", pet.describe())
else:
    st.info("No pets yet. Add one above.")

st.divider()

st.subheader("Tasks")

task_cols = st.columns(3)
with task_cols[0]:
    task_title = st.text_input("Task title", value="Morning walk")
with task_cols[1]:
    task_priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
with task_cols[2]:
    task_repeats = st.selectbox("Repeats", ["singular", "daily", "weekly"])

time_cols = st.columns(2)
with time_cols[0]:
    task_start = st.time_input("Start time", value=time(8, 0))
with time_cols[1]:
    task_end = st.time_input("End time", value=time(8, 30))

# Warn when the task's time window is invalid (start not before end).
task_time_invalid = task_start >= task_end
if task_time_invalid:
    st.warning("Invalid task time: start time must be earlier than end time.")

pet_choices = [pet.name for pet in scheduler.pets]
selected_pet_name = st.selectbox("Pet", pet_choices) if pet_choices else None
# Daily tasks ignore the date, so hide the picker and default it for them.
if task_repeats == "daily":
    task_day = date.today()
else:
    task_day = st.date_input("Date (used for singular and weekly tasks)", value=date.today())

if st.button("Add task", disabled=task_time_invalid):
    repeats = {"singular": Recurrence.NONE, "daily": Recurrence.DAILY, "weekly": Recurrence.WEEKLY}[task_repeats]
    selected_pet = next((pet for pet in scheduler.pets if pet.name == selected_pet_name), None)
    scheduler.add_task(
        task_title,
        Priority(task_priority),
        repeats,
        TimeWindow(task_start, task_end),
        selected_pet,
        task_day,
    )

if scheduler.tasks:
    st.write("Current tasks (check to mark completed for today):")
    for i, task in enumerate(scheduler.tasks):
        window = f"{task.time_window.start.strftime('%H:%M')}-{task.time_window.end.strftime('%H:%M')}"
        pet_part = f" with {task.pet.name}" if task.pet else ""
        if task.repeats is Recurrence.WEEKLY:
            when = f" on {task.task_date.strftime('%A')}"
            repeat_text = "repeats weekly"
        elif task.repeats is Recurrence.DAILY:
            when = ""
            repeat_text = "repeats daily"
        else:
            when = f" on {task.task_date.strftime('%B %d, %Y')}"
            repeat_text = "no repeat"
        label = f"{task.title}{pet_part} from {window}{when}, {task.priority.value} priority, {repeat_text}"
        # Toggle only on a real change so completing a task also stamps last_completed (for refresh).
        checked = st.checkbox(label, value=task.completed, key=f"task_complete_{i}")
        if checked != task.completed:
            task.toggle_complete()
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")

# Let the user pick which day to plan for, defaulting to today.
schedule_day = st.date_input("Schedule day", value=date.today())

if st.button("Generate schedule", disabled=owner_time_invalid):
    # Build the plan for the chosen day from the scheduler's owner and tasks.
    schedule = scheduler.create_schedule(schedule_day)
    st.write(f"Daily plan for {schedule.day} ({schedule.day.strftime('%A')})")
    if schedule.entries:
        rows = [
            {
                "Time": f"{entry.time_window.start.strftime('%H:%M')}-{entry.time_window.end.strftime('%H:%M')}",
                "Task": entry.title,
                "Pet": entry.pet.name if entry.pet else "-",
                "Priority": entry.priority.value,
            }
            for entry in schedule.entries
        ]
        st.table(rows)
    else:
        st.info("No valid tasks for today. Add incomplete tasks within the owner's availability.")

    # Notify which active tasks were dropped due to conflicts, and why.
    if schedule.removed:
        st.warning("Some tasks were removed from the plan:")
        for task, reason in schedule.removed:
            window = f"{task.time_window.start.strftime('%H:%M')}-{task.time_window.end.strftime('%H:%M')}"
            st.write(f"- {task.title} ({window}) — {reason}")
