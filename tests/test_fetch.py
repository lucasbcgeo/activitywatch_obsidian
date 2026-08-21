import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from data.models import IntervaloEntry
from handlers.fetch import INTERVALO_APPS, INTERVALO_GROUP, INTERVALO_ORDER, _extract_intervalos


class ExtractIntervalosTests(unittest.TestCase):
    def test_separa_intervalos_de_apps_normais(self):
        app_totals = {"Jantar": 973.0, "VS Code": 3600.0, "Exercícios": 45.0}
        intervalos, remaining = _extract_intervalos(app_totals)

        rotulos = {(i.rotulo, i.group) for i in intervalos}
        self.assertIn(("Jantar", "Intervalo"), rotulos)
        self.assertIn(("Exercícios", "Exercícios"), rotulos)
        self.assertEqual(remaining, {"VS Code": 3600.0})

    def test_ordem_fixa_por_rotulo_dentro_do_grupo(self):
        app_totals = {"Jantar": 100.0, "Pausa Rápida": 50.0, "Almoço": 30.0}
        intervalos, _ = _extract_intervalos(app_totals)
        rotulos = [i.rotulo for i in intervalos]
        self.assertEqual(rotulos, ["Pausa Rápida", "Almoço", "Jantar"])

    def test_sem_intervalos_retorna_lista_vazia_e_preserva_apps(self):
        app_totals = {"VS Code": 3600.0, "Chrome": 600.0}
        intervalos, remaining = _extract_intervalos(app_totals)
        self.assertEqual(intervalos, [])
        self.assertEqual(remaining, app_totals)

    def test_mapeamento_intervalo_exe_vira_pausa_longa(self):
        app_totals = {"Intervalo": 120.0}
        intervalos, remaining = _extract_intervalos(app_totals)
        self.assertEqual(intervalos[0].rotulo, "Pausa Longa")
        self.assertEqual(intervalos[0].group, "Intervalo")
        self.assertEqual(remaining, {})

    def test_constantes_cobrem_os_6_rotulos(self):
        self.assertEqual(
            set(INTERVALO_APPS.values()),
            {"Pausa Longa", "Pausa Rápida", "Café da manhã", "Almoço", "Jantar", "Exercícios"},
        )
        self.assertEqual(set(INTERVALO_GROUP.values()), {"Intervalo", "Exercícios"})
        self.assertEqual(len(INTERVALO_ORDER), 6)

    def test_clean_app_name_dos_intervalos_batem_com_CONSTANTES(self):
        from util.clean import clean_app_name
        raw_apps = [
            "Intervalo.exe",
            "Pausa Rápida.exe",
            "Café da manhã.exe",
            "Almoço.exe",
            "Jantar.exe",
            "Exercícios.exe",
        ]
        for raw in raw_apps:
            with self.subTest(raw=raw):
                self.assertIn(clean_app_name(raw), INTERVALO_APPS)


if __name__ == "__main__":
    unittest.main()
