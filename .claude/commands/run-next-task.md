1. Read docs/tasks/tasks.md.

2. Find the first "[ ]" line.

3. Ask Claude to implement that task only following the instruction below.

# Code
When you have a thorough implementation task, you are ready to start writing code.

**IMPORTANT: When writing code, always use subagents to edit files. Do not edit files directly in the main thread.**

**NOTE: When modifying files in the main thread during implementation, read them directly. The subagent requirement from the Explore phase only applies to exploration, not to files you're actively editing.**

Make sure to run our autoformatting script when you're done, and fix linter warnings that seem reasonable to you.

**IMPORTANT**: You should follow the instructions in the CLAUDE.md for implementing the tasks.

4. On success replace "[ ]" with "[X]" for that line, always start checking from the top and from the child tasks.

5. Save tasks.md and then stop.

$ARGUMENTS
