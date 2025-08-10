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

Once you're done with the plan, stop.

$ARGUMENTS
