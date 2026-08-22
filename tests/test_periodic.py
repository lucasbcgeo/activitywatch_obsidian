import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from handlers.periodic import (
    candidate_paths,
    format_iso_duration,
    nested_get,
    nested_set,
    numeric_value,
    parse_iso_duration,
    period_bounds,
)


class ParseIsoDurationTests(unittest.TestCase):
    def test_horas_minutos_segundos(self):
        self.assertEqual(parse_iso_duration("PT15H55M"), 57300)
        self.assertEqual(parse_iso_duration("PT1H30M"), 5400)
        self.assertEqual(parse_iso_duration("PT45M"), 2700)
        self.assertEqual(parse_iso_duration("PT30S"), 30)

    def test_zero_e_vazio(self):
        self.assertEqual(parse_iso_duration("PT0S"), 0)
        self.assertIsNone(parse_iso_duration(""))
        self.assertIsNone(parse_iso_duration(None))
        self.assertIsNone(parse_iso_duration("lixo"))

    def test_string_com_espacos(self):
        self.assertEqual(parse_iso_duration("  PT10M  "), 600)


class FormatIsoDurationTests(unittest.TestCase):
    def test_omite_partes_zero(self):
        self.assertEqual(format_iso_duration(5400), "PT1H30M")
        self.assertEqual(format_iso_duration(3600), "PT1H")
        self.assertEqual(format_iso_duration(60), "PT1M")
        self.assertEqual(format_iso_duration(3661), "PT1H1M1S")

    def test_zero_vira_pt0s(self):
        self.assertEqual(format_iso_duration(0), "PT0S")


class NumericValueTests(unittest.TestCase):
    def test_booleanos(self):
        self.assertEqual(numeric_value(True), 1.0)
        self.assertEqual(numeric_value(False), 0.0)

    def test_numeros(self):
        self.assertEqual(numeric_value(7), 7.0)
        self.assertEqual(numeric_value(2.5), 2.5)

    def test_strings_estilo_js(self):
        self.assertEqual(numeric_value("true"), 1.0)
        self.assertEqual(numeric_value("sim"), 1.0)
        self.assertEqual(numeric_value("nao"), 0.0)
        self.assertEqual(numeric_value("8"), 8.0)
        self.assertEqual(numeric_value("7,5"), 7.5)
        self.assertIsNone(numeric_value("abc"))
        self.assertIsNone(numeric_value(None))


class NestedGetSetTests(unittest.TestCase):
    def test_get_aninhado_e_plano(self):
        fm = {"pc": {"total": "PT1H"}, "exercicio.media": 0.5}
        self.assertEqual(nested_get(fm, ("pc", "total")), "PT1H")
        self.assertEqual(nested_get(fm, ("exercicio.media",)), 0.5)
        self.assertIsNone(nested_get(fm, ("cel", "tempo_total")))
        self.assertIsNone(nested_get(fm, ("pc", "total", "fundo")))

    def test_set_aninhado_cria_dicionarios(self):
        fm: dict = {}
        nested_set(fm, ("pc", "tempo_ativo_media"), "PT1H")
        nested_set(fm, ("exercicio.media",), 0.5)
        self.assertEqual(fm, {"pc": {"tempo_ativo_media": "PT1H"}, "exercicio.media": 0.5})


class PeriodBoundsTests(unittest.TestCase):
    def test_semana_iso_mesmo_ano(self):
        # 2026-08-19 é quarta-feira da semana ISO 34 (seg 17/08 – dom 23/08)
        bounds = {slug: (start, end) for slug, start, end in period_bounds(date(2026, 8, 19))}
        self.assertEqual(bounds["2026-W34"], (date(2026, 8, 17), date(2026, 8, 23)))

    def test_semana_iso_vira_de_ano(self):
        # 2027-01-01 é sexta da semana ISO 53 de 2026 (seg 28/12/2026 – dom 03/01/2027)
        bounds = {slug: (start, end) for slug, start, end in period_bounds(date(2027, 1, 1))}
        self.assertIn("2026-W53", bounds)
        self.assertEqual(bounds["2026-W53"], (date(2026, 12, 28), date(2027, 1, 3)))

    def test_mes(self):
        bounds = {slug: (start, end) for slug, start, end in period_bounds(date(2026, 8, 19))}
        self.assertEqual(bounds["2026-08"], (date(2026, 8, 1), date(2026, 8, 31)))

    def test_trimestre(self):
        bounds = {slug: (start, end) for slug, start, end in period_bounds(date(2026, 8, 19))}
        self.assertEqual(bounds["2026-Q3"], (date(2026, 7, 1), date(2026, 9, 30)))

    def test_ano(self):
        bounds = {slug: (start, end) for slug, start, end in period_bounds(date(2026, 8, 19))}
        self.assertEqual(bounds["2026"], (date(2026, 1, 1), date(2026, 12, 31)))


class CandidatePathsTests(unittest.TestCase):
    def test_semana(self):
        self.assertEqual(
            candidate_paths("V", "2026-W34"),
            [str(Path("V") / "01_Arquivos" / "Jornada" / "2026" / "Semanas" / "2026-W34.md")],
        )

    def test_trimestre(self):
        self.assertEqual(
            candidate_paths("V", "2026-Q3"),
            [str(Path("V") / "01_Arquivos" / "Jornada" / "2026" / "2026-Q3.md")],
        )

    def test_mes_dois_candidatos(self):
        self.assertEqual(
            candidate_paths("V", "2026-08"),
            [
                str(Path("V") / "01_Arquivos" / "Jornada" / "2026" / "2026-08.md"),
                str(Path("V") / "01_Arquivos" / "Jornada" / "2026-08.md"),
            ],
        )

    def test_ano_dois_candidatos(self):
        self.assertEqual(
            candidate_paths("V", "2026"),
            [
                str(Path("V") / "01_Arquivos" / "Jornada" / "2026.md"),
                str(Path("V") / "01_Arquivos" / "Jornada" / "2026" / "2026.md"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
