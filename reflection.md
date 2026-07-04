# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- In this design for my UML, I made it such that each important category such as a schedule, pet, or task have an individual class to improve readability of the whole system as each class has their individual tasks.
- Classes I included and their function:
> TimeWindow: Describes a time span and it's duration in minutes. 
> Pet: The pet with all information of the pet
> Owner: The owner with information such name, and avaiability.
> Task: A task that contains the title, pet to be cared for, whether it is daily or weekly, when it is done, the priority, and whether it is completed.
> Schedule: Houses a complete schedule for the day based on the costraints such as owner and priorities.
> Scheduler: represents this instance of the app, pulls everything together. 

**b. Design changes**

- During the desig phase, I found a new way to represent weekly or singular tasks, which is to use a date system to assign the tasks instead of a clunkly mon, tue, wed system. 

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- Some of the constraints my scheduler consider is the availability of the owner, the priority of each task, whether the task is daily, weekly, or once and the day it is scheduled for, and the timeslot of each task.
- How did you decide which constraints mattered most?
- I decided which constraints mattered the most by seeing what features a basic task manager should have, and that those are would be checking whether timeslots intersect. Then I build off of that feature.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- One tradeoff my scheduler makes is in the customizability of the schedule, since all schedules are created in the Schedule class and it is finely tuned, the user cannot create more custom schedules based on their preferences for the day.
- Why is that tradeoff reasonable for this scenario?
- I believe this tradeoff is reasonable as it reduces the number of errors and mistakes on the algorithms part and my part which improves the implementability of the program. Since adding extra inputs and outputs would mean implementing more safeguards for the user to not break the program which would add more time to implementation. 

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- During this project, I use AI to debugg code and assist in refactoring along with building the framework of the project. 

- What kinds of prompts or questions were most helpful?
- The kind of prompts that were the most helpful were the ones I made with the most detail and parameters, as those are the ones that are specific enough that the AI can nail my vision of how the program should run.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- One moment I did not accept an AI suggestion is in the drafting of the mmd, it gave more vague ideas and methods that in my mind did not fit the implementation. And thus over several itterations, I fixed the draft based on my idea on what the project should look like. 

- How did you evaluate or verify what the AI suggested?
- I evaluated what the AI suggested by looking at the code and seeing the vauge operations of each dif along with testing the implementation though either pytest or my own inputs into the program.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- The behaviors I tested included the generation of at least a valid schedule along with whether the data being inputted is correct.
- Why were these tests important?
- These tests are important because they are the foundation of the app, if it cannot generate a barebone valid schedule, it is not a scheduler, and if it cannot store the data correctly, then it isn't even a task holder app. 

**b. Confidence**

- How confident are you that your scheduler works correctly?
- Overall, I think my app would work 8.5/10 times as I would have loved to have more time and knowledge on python to analyze the code more througouly and ensure all edge cases are flushed out.
- What edge cases would you test next if you had more time?
- The edge cases I would have tested includes brute force number of tasks and whether the tasks would reset upon passing the next week. 

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
- Overall what went well with the project is the implementation and design of it, the features I want to add are added and I am satisfied it works on the top end.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
- If I hadd another iteration, I would add more features and test out the app more to esure it is more air tight.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
- One important thing I have learned about working with AI is how the design is more on you rather than the AI, and letting it think for you will cause more headaches than progress.