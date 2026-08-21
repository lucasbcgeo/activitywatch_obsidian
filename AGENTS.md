# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python CLI that syncs ActivityWatch activity into Obsidian daily notes. Source code lives in `src/`, with the CLI entry point at `src/main.py`.

- `src/handlers/`: core pipeline modules for `fetch -> format -> write`.
- `src/data/`: dataclasses and shared activity models.
- `src/util/`: path, YAML, time formatting, and cleanup helpers.
- `src/log/`: logging setup.
- `tests/`: unit tests, currently focused on formatter behavior.
- `docs/superpowers/`: design specs and implementation plans; do not treat these as runtime code.

Keep generated or local runtime output out of commits. `logs/`, `.venv/`, `.env`, and `data/` are local/environment state unless a task explicitly says otherwise.

## Build, Test, and Development Commands

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Creates the local Python environment and installs `aw-client`, `pyyaml`, and `python-dotenv`.

```powershell
python src/main.py
python src/main.py --date 2026-03-22
```

Runs the sync for today or a specific date. Requires ActivityWatch running and a configured `.env`.

```powershell
python -m unittest discover -s tests
```

Runs the test suite.

## Coding Style & Naming Conventions

Use Python 3.10+ and standard-library features where they fit. Follow the existing style: 4-space indentation, small functions, dataclasses for structured data, and clear module names such as `formatter.py` or `yaml_helpers.py`. Keep comments for non-obvious behavior, not line-by-line narration.

Environment variables are uppercase, for example `VAULT_PATH`, `AW_HOST`, and `MIN_MINUTES_APPS`.

## Testing Guidelines

Use `unittest` unless the project adopts another framework. Put tests in `tests/` and name files `test_*.py`. Prefer focused tests around formatter, path, YAML merge, and writer behavior because those are the safest checks for Obsidian output regressions.

## Commit & Pull Request Guidelines

Recent history uses short Conventional Commit-style subjects, for example `feat: add Games duration to frontmatter` and `docs: plan Games frontmatter implementation`. Keep commits scoped and imperative.

Pull requests should include the behavior change, test command output, and any required `.env` or ActivityWatch setup notes. Include before/after Obsidian output examples when changing formatting or frontmatter.

## Security & Configuration Tips

Do not commit `.env` or vault-specific private paths. Use `.env.example` for documented configuration and keep real vault paths local.

## 1. Worktree & Environment Setup
* New ideas and features must be developed and tested in a separate worktree. See [Ideas](../../Lucas/01_Arquivos/Projetos/activitywatch#-ideias) for the backlog. Use `git` or `gh` commands to create the worktree inside `"G:\Projetos\Worktrees-Proj"`.
* **Environment Initialization:** When entering a new worktree directory, you **must** run `npm install` (or `yarn`) immediately before writing or testing any code. Dependencies are not copied automatically by Git.

## 2. Git Workflow & Dependency Rules
* **No Manual File Copying:** When your feature is complete, **DO NOT** manually copy files back to the main repository folder. Run `git add`, `git commit`, and `git push` from inside your worktree directory to update the remote feature branch. Leave the feature branch open for subsequent reviews.
* **Dependency Files:** When adding new packages to `package.json`, `package-lock.json`, or `requirements.txt`, modify them **only** within your active worktree/branch. Resolve dependency conflicts through normal git merge/rebase — do not manually sync these files across directories.

## 3. Commit & Pull Request Guidelines
Recent history uses short imperative subjects, sometimes Conventional Commit prefixes such as `fix:` and `feat:`. Keep commits scoped, for example `fix: recover messages missed by live listener`. PRs should describe the changed runtime path, list the exact checks run, mention config or `.env` changes, and include log excerpts only when they prove simulated behavior.

## 4. Communication & Logging
* Document your progress, logic changes, and implementation details clearly. Use [Session Notes](../../Lucas/01_Arquivos/Projetos/activitywatch#-anotações) to write comprehensive logs and keep Lucas fully informed of your structural and functional changes.

## gh-cli commands
To use GitHub Actions, use skill gh-cli — any new learning about gh-cli will be added to this file.

### List



