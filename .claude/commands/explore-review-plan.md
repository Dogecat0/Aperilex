At the end of this message, I will ask you to do something. Please follow the "Explore, Plan, Code, Test" workflow when you start.

# Explore
First, use parallel subagents to find and read all files that may be useful for implementing the task/ticket, either as examples or as edit targets. The subagents should return relevant file paths, and any other info that may be useful. During this step, you should ignore all the existing tests files.

# Review
Before implementing the plan, it's important to review the existing codebase and any relevant documentation. This will help ensure that the implementation is consistent with the project's standards and practices.

Think hard and write up the current state of the codebase, including any relevant architectural decisions, design patterns, and coding conventions that are in use.

# Plan
Next, think hard and write up a detailed implementation plan. Don't forget to include tests, lookbook components, and documentation. Use your judgement as to what is necessary, given the standards of this repo.

If there are things you are not sure about, use parallel subagents to do some web research. They should only return useful information, no noise.

If there are things you still do not understand or questions you have for the user, pause here to ask them before continuing.

$ARGUMENTS