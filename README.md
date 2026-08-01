# PawPal+ (Module 2 Project)

It's goal is to allow for pet owners to schedule and create and manage tasks easily and effectively. It can take in created account, pets, and tasks to create a rigid schedule based on priorities.

Now with...

# PawPal++
You are able to do the previous, but you are able to more flexibly and easily change schedules or tasks on a dime. Since planning is long an tedious and a task may change at any moment, using the built in agentic AI, it is able to adjust to new parameters you put in as well as generating a schedule.

# Architecture Overview
- In pawpal_system.py, it includes the basic objects to tasks, schedule, pets, and owner, where schedule calls functions in schedule_agent.py to build the schedule itself.

- In schedule_agent.py, there are functions that prepares the prompt, generates it via the LLM or heuristicly, ensures output are correct via a guardrail, and puts out a resoning and the formatted output.

# Instructions
First, create your account, add pets, and add any tasks.
Second, ask a question such as "can you generate me a schedule for today"?
Finally, done! Output should be given at the bottom of the prompt window which includes the schedule and reason. 

# Sample Inputs & Outputs
The examples below are live outputs from the Gemini agent (`gemini-flash-lite-latest`). Each shows the account, pets, tasks, and free-text instruction that go in, and the plan, removed tasks, and AI reasoning that come out.

## Example 1 — keep entered times, resolve conflicts
**Input**
- Owner: Jordan — available 08:00–17:00
- Pets: Mochi (Male tan Corgi dog, 1.0 ft), Luna (Female gray Tabby cat, 0.8 ft)
- Tasks:
  - Morning walk — high, daily, 08:00–08:30, Mochi
  - Morning feeding — high, daily, 08:15–08:45, Luna
  - Afternoon meds — medium, daily, 13:00–13:15, Luna
  - Evening walk — low, daily, 18:00–18:30, Mochi
- Instruction: *"Plan my tasks for August 3, 2026 using the times I entered."*

**Output** — Daily plan for 2026-08-03 (Monday)

| Time | Task | Pet | Priority |
| --- | --- | --- | --- |
| 08:00–08:30 | Morning walk | Mochi | high |
| 13:00–13:15 | Afternoon meds | Luna | medium |

Removed:
- Morning feeding (08:15–08:45) — Clashes with higher priority task [0] at 08:00-08:30
- Evening walk (18:00–18:30) — Outside owner's availability window of 08:00-17:00

AI reasoning: Scheduled tasks [0], [1], and [2] within availability. Task [1] (08:15-08:45) clashes with task [0] (08:00-08:30). Task [0] has high priority and is kept, while task [1] is removed due to overlap and lower priority sequence. Task [3] is removed because its entered time (18:00-18:30) is outside the owner's availability (08:00-17:00).

## Example 2 — recommended plan (re-times tasks) with a weekly task
**Input**
- Owner: Priya — available 07:00–20:00
- Pets: Rex (Male black Labrador dog, 2.0 ft)
- Tasks:
  - Morning walk — high, daily, 07:00–07:30, Rex
  - Lunch feeding — high, daily, 12:00–12:20, Rex
  - Evening walk — medium, daily, 17:00–17:45, Rex
  - Grooming — low, weekly (Saturdays), 10:00–11:00, Rex
- Instruction: *"Give me a recommended schedule for Saturday, August 1, 2026 that spaces the walks and feedings evenly through the day."*

**Output** — Daily plan for 2026-08-01 (Saturday)

| Time | Task | Pet | Priority |
| --- | --- | --- | --- |
| 07:00–07:30 | Morning walk | Rex | high |
| 11:00–11:20 | Lunch feeding | Rex | high |
| 13:00–14:00 | Grooming | Rex | low |
| 17:30–18:15 | Evening walk | Rex | medium |

Removed: (none)

AI reasoning: Scheduled tasks for Saturday, August 1, 2026, including daily walks/feedings and weekly grooming. Adjusted walk and feeding times to space them evenly throughout Priya's 07:00-20:00 availability.

## Example 3 — add a new task on request (pinned to a pet)
**Input**
- Owner: Sam — available 09:00–18:00
- Pets: Biscuit (Female brown Beagle dog, 1.2 ft)
- Tasks:
  - Morning walk — high, daily, 09:00–09:30, Biscuit
  - Afternoon feeding — medium, daily, 13:00–13:20, Biscuit
- Instruction: *"Plan August 3, 2026 with my entered times, and also add a 15-minute water refill for Biscuit in the early afternoon."*

**Output** — Daily plan for 2026-08-03 (Monday)

| Time | Task | Pet | Priority |
| --- | --- | --- | --- |
| 09:00–09:30 | Morning walk | Biscuit | high |
| 13:00–13:20 | Afternoon feeding | Biscuit | medium |
| 13:30–13:45 | Water refill | Biscuit | medium |

Removed: (none)

AI reasoning: Scheduled tasks 0 and 1 within the owner's availability using their entered times, and added the new water refill task for Biscuit as requested in the early afternoon without overlap.

# Design decisions
Certain features such as the ability to modify the user's task list is not added due to the un-predictable and possibly destructive nature of the AI, which necessicated further complicated output guardrails that I do not have enough time to add. However, I was still able to add the core feature of this addition which enables the user to generate and modify their plans on the fly, which only requires basic sanitation guardrails.




