# activitywatch-obsidian Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Isolate the `activitywatch_obsidian` project dependencies into a local Python `venv` and create a local `launch_sync.bat` to serve as the stable entry point for the external unified scheduler.

**Architecture:** Create a local `.venv` for Python 3.13, install dependencies from `requirements.txt`, and create a `.bat` wrapper to execute `src/main.py`. This wrapper will be called by the existing external `.ps1` script.

**Tech Stack:** Python 3.13, `venv`, `aw-client`, `pyyaml`, `python-dotenv`.

---

### Task 1: Environment Setup

**Files:**
- Create: `G:\Projetos\activitywatch_obsidian\.venv`

- [ ] **Step 1: Create the virtual environment**

Run: `python -m venv G:\Projetos\activitywatch_obsidian\.venv`
Expected: Folder `.venv` created in the project root.

- [ ] **Step 2: Install dependencies in the venv**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\pip install -r G:\Projetos\activitywatch_obsidian\requirements.txt`
Expected: `aw-client`, `pyyaml` and `python-dotenv` installed.

- [ ] **Step 3: Verify installation**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\pip list`
Expected: List includes `aw-client`.

---

### Task 2: Create local launch_sync.bat

**Files:**
- Create: `G:\Projetos\activitywatch_obsidian\launch_sync.bat`

- [ ] **Step 1: Write the batch file**

```batch
@echo off
"G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe" "G:\Projetos\activitywatch_obsidian\src\main.py" %*
```

- [ ] **Step 2: Test the batch file manually**

Run: `G:\Projetos\activitywatch_obsidian\launch_sync.bat --help`
Expected: Print the help message for `main.py` using the venv interpreter.

---

### Task 3: Configuration Check

**Files:**
- Modify: `G:\Projetos\activitywatch_obsidian\.env`

- [ ] **Step 1: Verify VAULT_PATH**

- Ensure `VAULT_PATH` is absolute (e.g., `G:/Franklin`).

- [ ] **Step 2: Final test**

Run: `G:\Projetos\activitywatch_obsidian\launch_sync.bat`
Expected: "Sync concluído com sucesso!" in logs or console.
