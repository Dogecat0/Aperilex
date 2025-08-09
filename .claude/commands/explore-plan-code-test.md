At the end of this message, I will ask you to do something. Please follow the "Explore, Plan, Code, Test" workflow when you are in each phase and use relevant subagents to perform the tasks (Using defined or default agents depends on your choice after a thorough and hard think).

# Explore
First, use parallel subagents to find and read files that may be useful for implementing the task/ticket.

**IMPORTANT: You MUST use subagents to read ANY file during exploration. DO NOT read files directly in the main thread.**

**PROHIBITED: Do NOT use grep, find, awk, sed, or any bash command tools for text searching or content extraction. Use file listing tools like glob to find files, then delegate actual file reading to subagents.**

**SUBAGENT GUIDANCE: Within subagents, always read files directly rather than using search tools. Extract information by reading the full file content and filtering programmatically.**

**READ TOOL: When using the Read tool, always read all lines of the file, do not read in sections.**

Design specific tasks for each subagent based on what you need to understand. Give focused missions like:
- "Extract authentication system interface and dependencies"
- "Find repository patterns and method signatures"
- "Identify domain layer error handling patterns"
- "Map database schema for entities X, Y, Z"
- "Extract configuration and environment patterns"
- "Find API endpoint patterns and schemas"
- "Get coding style examples for feature X"

Subagents should return only task-relevant information, creating focused codemaps not exhaustive dumps. Target specific concepts: interface contracts, class hierarchies, configuration patterns, error handling, data flows, external integrations.

Always identify files to modify vs. reference examples.

Ignore test files during exploration - examine them in Test phase.

# Plan
Next, think ultrahard and write up a detailed implementation plan. Don't forget to include tests, lookbook components, and documentation. Use your judgement as to what is necessary, given the standards of this repo.

If there are things you are not sure about, use parallel subagents to do some only necessary web research. They should only return useful information, no noise.

If there are things you still do not understand or questions you have for the user, pause here to ask them before continuing.

# Code
When you have a thorough implementation plan, you are ready to start writing code. Follow the style of the existing codebase (e.g. we prefer clearly named variables and methods to extensive comments).

**IMPORTANT: When writing code, always use subagents to edit files. Do not edit files directly in the main thread.**

**NOTE: When modifying files in the main thread during implementation, read them directly. The subagent requirement from the Explore phase only applies to exploration, not to files you're actively editing.**

Make sure to run our autoformatting script when you're done, and fix linter warnings that seem reasonable to you.

# Test
Use parallel subagents to run tests, and make sure they all pass.

**TEST EXECUTION: When running tests, always run the entire test suite to ensure no regressions. Do not run partial test suites even when debugging a particular component - always run the full suite.**

**BASH COMMANDS: When running any bash commands, do not limit or truncate the output using `head`, `tail`, `more`, `less`, piping to `head`/`tail`, or any other commands that limit output display. Always show full output for proper debugging and validation.**

If your changes touch the UX in a major way, use the browser to make sure that everything works correctly. Make a list of what to test for, and use a subagent for this step.

If your testing shows problems, go back to the planning stage and think ultrahard.

Once you are satisfied with your code, run the tests and do the code quality check again to make sure everything is still passing. When you run python commands, remember we are using Poetry, so use `poetry run` before the command. When you run frontend commands, use `yarn` or `npm` as appropriate. Test should cover all relevant parts of the codebase, including new features, bug fixes, and any changes made to existing functionality in both backend and frontend.

# Write up your work
When you are happy with your work, write up a short report that could be used as the PR description. Include what you set out to do, the choices you made with their brief justification, and any commands you ran in the process that may be useful for future developers to know about.

**GIT COMMITS: When committing changes, split them into logical groups of files and changes. Create separate commits for different aspects like domain changes, infrastructure updates, tests, configuration, etc. This makes the change history clearer and easier to review.**

$ARGUMENTS
