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
from handlers.formatter import format_intervalos_block


class FormatIntervalosTests(unittest.TestCase):
    def _activity(self, intervalos):
        return DailyActivity(
            date=date(2026, 8, 20).isoformat(),
            total_seconds=0,
            active_seconds=0,
            intervalos=intervalos,
        )

    def test_so_itens_positivos_aparecem(self):
        activity = self._activity([
            IntervaloEntry("Jantar", "Intervalo", 2160),    # 36m
            IntervaloEntry("Exercícios", "Exercícios", 0),  # omitido
        ])
        block = format_intervalos_block(activity)
        self.assertIn("Jantar (36m)", block)
        self.assertNotIn("Exercícios", block)
        self.assertIn("<!-- aw:start-intervalos -->", block)
        self.assertIn("<!-- aw:end-intervalos -->", block)

    def test_grupo_so_aparece_se_tem_item_positivo(self):
        activity = self._activity([])
        block = format_intervalos_block(activity)
        self.assertNotIn("Intervalo", block)
        self.assertNotIn("Exercícios", block)
        self.assertIn("<!-- aw:start-intervalos -->", block)
        self.assertIn("<!-- aw:end-intervalos -->", block)

    def test_preserva_ordem_pre_ordenada_do_grupo(self):
        # fetch pre-sorts by (group, INTERVALO_ORDER.index(rotulo)):
        # Pausa Rápida comes before Jantar. Formatter must preserve that order.
        activity = self._activity([
            IntervaloEntry("Pausa Rápida", "Intervalo", 50),
            IntervaloEntry("Jantar", "Intervalo", 100),
        ])
        block = format_intervalos_block(activity)
        self.assertLess(block.index("Pausa Rápida"), block.index("Jantar"))

    def test_duas_secoes_intervalo_e_exercicios(self):
        activity = self._activity([
            IntervaloEntry("Jantar", "Intervalo", 2160),
            IntervaloEntry("Exercícios", "Exercícios", 2700),
        ])
        block = format_intervalos_block(activity)
        self.assertIn("Intervalo", block)
        self.assertIn("Exercícios", block)
        self.assertIn("Jantar (36m)", block)
        self.assertIn("Exercícios (45m)", block)

    def test_sem_porcentagem_no_bloco(self):
        activity = self._activity([
            IntervaloEntry("Jantar", "Intervalo", 2160),
        ])
        block = format_intervalos_block(activity)
        self.assertNotIn("%", block)

    def test_primeira_coluna_direto_apos_header_sem_separador(self):
        activity = self._activity([
            IntervaloEntry("Jantar", "Intervalo", 2160),
        ])
        block = format_intervalos_block(activity)
        # Matches format_body pattern: first column directly after [!multi-column]
        self.assertIn("> [!multi-column]\n>> [!pause]+  Intervalo", block)
        self.assertNotIn("> [!multi-column]\n>\n>> [!pause]+  Intervalo", block)


if __name__ == "__main__":
    unittest.main()
