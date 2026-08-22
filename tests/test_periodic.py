import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from handlers.periodic import (
    format_iso_duration,
    nested_get,
    nested_set,
    numeric_value,
    parse_iso_duration,
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


if __name__ == "__main__":
    unittest.main()
