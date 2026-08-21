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


from data.models import IntervaloEntry
from handlers.formatter import INTERVALO_MARKERS, format_intervalo_contents


class FormatIntervaloContentsTests(unittest.TestCase):
    def _activity(self, intervalos):
        return DailyActivity(
            date=date(2026, 8, 21).isoformat(),
            total_seconds=0,
            active_seconds=0,
            intervalos=intervalos,
        )

    def test_seis_slugs_sempre_presentes(self):
        contents = format_intervalo_contents(self._activity([]))
        self.assertEqual(
            set(contents),
            {"pausa-longa", "pausa-curta", "café", "almoço", "jantar", "exercícios"},
        )

    def test_zero_ou_ausente_vazio(self):
        activity = self._activity([
            IntervaloEntry("Jantar", "Intervalo", 0),
            IntervaloEntry("Pausa Longa", "Intervalo", 30),  # < 60s -> "0m"
        ])
        contents = format_intervalo_contents(activity)
        self.assertEqual(contents["jantar"], "")
        self.assertEqual(contents["pausa-longa"], "")

    def test_positivo_minutos_formato_separador(self):
        activity = self._activity([
            IntervaloEntry("Café da manhã", "Intervalo", 1860),  # 31m
        ])
        self.assertEqual(format_intervalo_contents(activity)["café"], "· 31m")

    def test_positivo_horas_formato_separador(self):
        activity = self._activity([
            IntervaloEntry("Exercícios", "Exercícios", 8100),  # 2h15
        ])
        self.assertEqual(format_intervalo_contents(activity)["exercícios"], "· 2h15")

    def test_mapeamento_pausa_rapida_vira_pausa_curta(self):
        activity = self._activity([
            IntervaloEntry("Pausa Rápida", "Intervalo", 300),
        ])
        contents = format_intervalo_contents(activity)
        self.assertEqual(contents["pausa-curta"], "· 5m")
        self.assertNotIn("pausa-rápida", contents)


if __name__ == "__main__":
    unittest.main()
