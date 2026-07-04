# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
#Daily plan for Bon (German Shepard):
#08:30 — Take Bon to Training (60 min) [priority: high]
#18:45 — Wash Bon (15 min) [priority: high]
#11:00 — Walk Bon (150 min) [priority: medium]
#Daily plan for Alex (Calico):
#13:30 — Play with Alex (60 min) [priority: low]
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
Daily plan for Bon (German Shepard):
  18:45 — Wash Bon (15 min) [priority: high]
  11:00 — Walk Bon (150 min) [priority: medium]
Daily plan for Alex (Calico):
  08:00 — Groom Alex (60 min) [priority: medium]
  13:30 — Play with Alex (60 min) [priority: low]
```

## 📐 Smarter Scheduling

> Fill in once you've implemented scheduling logic.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | | e.g., by priority, duration |
| Filtering | | e.g., skip tasks if time runs out |
| Conflict handling | | e.g., overlapping time slots |
| Recurring tasks | | e.g., daily vs. weekly |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. Create a new pet and your time slots 8:00 to 19:00
2. Add a new task with the selected time, 11:30 to 12:00, daily, High priority
3. Add another task 11:45 to 13:45 (or any combination that overlaps with the first) Weekly on wednesday, low priority.
4. Run the scheduler with today's date (assuming today is wednesday)
5. Only the first task would be scheduled. 
6. Click complete on the first task. Only the second task would be scheduled. 
7. Generate a schedule for tomorrow, the first task reappears as it would have refreshed. Second task is not scheduled as it's not wednesday.
8. Click complete on both tasks, select the next week's wednesday and generate a schedule. Only the first task should generate but a message about the second task being dropped due to conflicts appears below the scheduler.

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
