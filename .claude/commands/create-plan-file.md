Description: Save the current outline to a versioned plan file allowed-tools: Bash(echo:), Bash(date:)

1. Read the latest outline from the conversation.

2. Determine the next version number (v001, then v002, …).

3. Create plan-$NEXT_VERSION.md in the docs/plans/.

4. Add heading: "Plan $NEXT_VERSION".

5. Paste the outline below the heading.

6. Append "Created: <GMT timestamp>".

7. Confirm the file is saved.

$ARGUMENTS
