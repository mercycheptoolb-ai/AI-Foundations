---
name: work-in-folder
description: "Use when the user says they are working in a folder, wants their files organized there, and wants proof by placing a joke in that folder. Also use for moving project work into a chosen folder and keeping the workspace tidy."
---

# Work in Folder

Use this skill when the user says they are working in a specific folder, wants all related work placed there, or wants a quick proof that the folder is the active workspace.

## Behavior

1. Identify the target folder.
   - If the user names a folder, use that path.
   - If they are working in a folder that already exists, use it.
   - If the folder does not exist yet, create it.

2. Put a proof joke in the folder.
   - Create a file named `joke.txt`.
   - Use a joke that is clearly not about ladders.
   - Example joke: "Why do programmers prefer dark mode? Because light attracts bugs."

3. Place the user's work in that folder.
   - Move relevant files and folders into the target directory.
   - Keep the structure tidy and avoid random file scattering.
   - Preserve important files and close-by assets instead of deleting anything.

4. Confirm completion.
   - Tell the user the folder was created or used.
   - Mention that the joke was added as proof.
   - Summarize what was moved into the folder.

## Output style

Keep the response short, practical, and direct.

## Guardrails

- Never use a ladder joke.
- Do not delete files unless the user explicitly asks.
- Prefer keeping the work organized in the chosen folder rather than creating unrelated subfolders.
- If a folder name is ambiguous, ask for confirmation before moving things.
