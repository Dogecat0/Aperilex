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

$ARGUMENTS
