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

        self.assertIn("games", result)
        self.assertEqual(result["games"], "PT1H30M")
        self.assertIn("pc", result)

    def test_omits_games_when_exact_positive_category_is_absent(self):
        for categories in ([], [Category("Games", 0)], [Category("Games > Steam", 5400)]):
            with self.subTest(categories=categories):
                self.assertNotIn("games", format_frontmatter(self.activity(categories)))


if __name__ == "__main__":
    unittest.main()
