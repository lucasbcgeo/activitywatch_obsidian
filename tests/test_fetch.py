import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from datetime import datetime, timedelta, timezone

from data.models import IntervaloEntry
from handlers.fetch import (
    COUNT_AFK_CATEGORIES,
    INTERVALO_APPS,
    INTERVALO_GROUP,
    INTERVALO_ORDER,
    _compute_active_seconds,
    _extract_intervalos,
)


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


class ComputeActiveSecondsTests(unittest.TestCase):
    BASE = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)

    CLASSES = [
        {
            "name": ["Intervalo", "Café da manhã"],
            "rule": {"type": "regex", "regex": "caf"},
        },
        {
            "name": ["Estudando", "TogglTrack"],
            "rule": {"type": "regex", "regex": "toggl"},
        },
    ]

    def afk(self, status, minutes, offset=0):
        return {
            "timestamp": self.BASE + timedelta(minutes=offset),
            "duration": timedelta(minutes=minutes),
            "data": {"status": status},
        }

    def win(self, app, title, minutes, offset=0):
        return {
            "timestamp": self.BASE + timedelta(minutes=offset),
            "duration": timedelta(minutes=minutes),
            "data": {"app": app, "title": title},
        }

    def test_constante_tem_as_oito_categorias(self):
        self.assertEqual(
            COUNT_AFK_CATEGORIES,
            {
                "Intervalo > Pausa Rápida",
                "Intervalo > Café da manhã",
                "Intervalo > Almoço",
                "Intervalo > Jantar",
                "Intervalo > Pausa Longa",
                "Estudando > TogglTrack",
                "Exercício",
                "X",
            },
        )

    def test_afk_em_categoria_da_lista_conta_ativo(self):
        active = _compute_active_seconds(
            [self.afk("afk", 30)],
            [self.win("Café da manhã.exe", "", 30)],
            self.CLASSES,
        )
        self.assertEqual(active, 1800.0)

    def test_afk_fora_da_lista_nao_conta(self):
        active = _compute_active_seconds(
            [self.afk("afk", 30)],
            [self.win("chrome.exe", "Qualquer site", 30)],
            self.CLASSES,
        )
        self.assertEqual(active, 0.0)

    def test_intersecao_parcial(self):
        # janela de 60min cobre afk de 10min -> só 10min entram
        active = _compute_active_seconds(
            [self.afk("afk", 10)],
            [self.win("Café da manhã.exe", "", 60)],
            self.CLASSES,
        )
        self.assertEqual(active, 600.0)

    def test_multiplas_janelas_num_mesmo_afk(self):
        active = _compute_active_seconds(
            [self.afk("afk", 30)],
            [
                self.win("Café da manhã.exe", "", 20, offset=0),
                self.win("chrome.exe", "site", 10, offset=20),
            ],
            self.CLASSES,
        )
        self.assertEqual(active, 1200.0)

    def test_not_afk_soma_integral(self):
        active = _compute_active_seconds(
            [self.afk("not-afk", 45), self.afk("not-afk", 15, offset=45)],
            [],
            self.CLASSES,
        )
        self.assertEqual(active, 3600.0)

    def test_misto_not_afk_e_afk_categorizado(self):
        active = _compute_active_seconds(
            [self.afk("not-afk", 30), self.afk("afk", 30, offset=30)],
            [self.win("TogglTrack.exe", "toggl", 60)],
            self.CLASSES,
        )
        self.assertEqual(active, 3600.0)

    def test_sem_classes_fallback_not_afk(self):
        active = _compute_active_seconds(
            [self.afk("not-afk", 10), self.afk("afk", 20, offset=10)],
            [self.win("Café da manhã.exe", "", 30)],
            [],
        )
        self.assertEqual(active, 600.0)


if __name__ == "__main__":
    unittest.main()
