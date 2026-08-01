# PawPal++ Project Reflection

# Limitations and biases
Some limitations of this AI system is that it cannot edit the user's lists of task directly and thus
it will not have a memory of past prompts that includes new tasks.

# Misuse
One way this system can be misused is the usage of vulgar words by the user, which could be solved by adding a profanity filter as an input guardrail.
Another way is calling the API too much and overloading the system or using up all calls, this could be solved by having a memory that logs the amount of calls per day and stopping the user from using the LLM version of the scheduler if it goes above a certain point.

# Surprises
One thing that surprised me during testing is how interesting the responses of the AI as although the response is technically "correct" it does not follow my expectation of correct. This may be due to the fact I (as the user) have not typed enough constraints and thus the AI uses it to modify the schedule to fit loose instructions. This is in the similar manner to how regular chatbots execute instructions if you gave it vague instructions.

# AI collaboration
During this project, I use agentic AI extensively in order to build up the framework and code of the project. However, one of the choices it made regarding the input of data to the project AI was incorrect. This caused endless headaches as the project AI spat back responses that are too restricted. However, one instance it gave a helpful advice is how the API does not recognize the model I am trying to use, so I asked claude and it helped to idenfity a working model that I can use.