# Games Category Frontmatter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the root `games` property when the exact ActivityWatch category `Games` has positive duration.

**Architecture:** Reuse `DailyActivity.categories` inside `format_frontmatter`; no fetching or model changes are needed. Use the existing ISO 8601 formatter and omit the property when no exact positive category exists.

**Tech Stack:** Python standard-library `unittest`, existing dataclasses and formatter utilities.

---

### Task 1: Format the Games category

**Files:**
- Create: `tests/test_formatter.py`
- Modify: `src/handlers/formatter.py`

- [ ] **Step 1: Write the failing tests**

```python
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from data.models import Category, DailyActivity
from handlers.formatter import format_frontmatter


class FormatFrontmatterTests(unittest.TestCase):
    def activity(self, categories):
        return DailyActivity(
            date=date(2026, 6, 20).isoformat(),
            total_seconds=5400,
            active_seconds=5000,
            categories=categories,
        )

    def test_adds_games_from_exact_category_case_insensitively(self):
        result = format_frontmatter(self.activity([Category("games", 5400)]))

        self.assertEqual(result["games"], "PT1H30M")
        self.assertIn("pc", result)

    def test_omits_games_when_exact_positive_category_is_absent(self):
        for categories in ([], [Category("Games", 0)], [Category("Games > Steam", 5400)]):
            with self.subTest(categories=categories):
                self.assertNotIn("games", format_frontmatter(self.activity(categories)))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify the feature test fails**

Run: `.venv\Scripts\python.exe -m unittest tests.test_formatter -v`

Expected: `test_adds_games_from_exact_category_case_insensitively` fails because `games` is absent; omission cases pass.

- [ ] **Step 3: Add the minimal formatter logic**

Insert before the return from `format_frontmatter`:

```python
    result = {"pc": pc}
    games = next(
        (c for c in activity.categories if c.name.casefold() == "games" and c.total_seconds > 0),
        None,
    )
    if games:
        result["games"] = seconds_to_iso(games.total_seconds)

    return result
```

- [ ] **Step 4: Run the focused and complete tests**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`

Expected: both tests pass with exit code 0.

- [ ] **Step 5: Review and commit only feature files**

Run: `git diff --check -- src/handlers/formatter.py tests/test_formatter.py`

Expected: exit code 0 and no output.

Commit only `src/handlers/formatter.py` and `tests/test_formatter.py`, preserving unrelated local changes.
