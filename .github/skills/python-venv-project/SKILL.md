---
name: python-venv-project
description: "Use when the user specifies a folder and a list of Python packages to install. Creates a local Python virtual environment in that folder, writes a requirements.txt file, and installs the packages into the venv."
---

# Python Venv Project Setup

Use this skill when the user says they want a folder set up for Python work and gives a package list to install.

## Behavior

1. Confirm the target folder.
   - If the folder exists, use it.
   - If it does not exist, create it.
   - Keep the folder path explicit and stable.

2. Create a virtual environment in that folder.
   - Use a local environment named `.venv` inside the target folder.
   - Run:
     - `python3 -m venv .venv`

3. Create a requirements file in that same folder.
   - Write a `requirements.txt` file containing the exact packages the user requested.
   - Preserve the package names exactly as given, one per line.
   - If the user provides version pins, keep them.

4. Install the packages into the new environment.
   - Use the venv’s Python executable.
   - Run:
     - `.venv/bin/python -m pip install -r requirements.txt`

5. Verify the setup.
   - Confirm the virtual environment was created.
   - Confirm the requirements file exists.
   - Confirm package installation succeeded.

## Example workflow

If the user says:
- folder: `project-a`
- packages: `pandas`, `numpy`, `requests`

Then the workflow should do this:
- create `project-a/`
- run `python3 -m venv project-a/.venv`
- write `project-a/requirements.txt` with:
  - `pandas`
  - `numpy`
  - `requests`
- run `project-a/.venv/bin/python -m pip install -r project-a/requirements.txt`

## Guardrails

- Never install packages globally.
- Always install into the local `.venv` inside the target folder.
- Keep the environment isolated and project-specific.
- If the user provides a folder name but no packages, ask for the package list before proceeding.
- If the user provides a path that is not valid, ask for clarification instead of guessing.

## Response style

Keep the answer brief, direct, and completion-focused. Tell the user what folder was created, which packages were installed, and where the venv is. The user should be able to immediately continue working in that project folder.
