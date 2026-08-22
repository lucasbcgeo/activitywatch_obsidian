import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from handlers.periodic import (
    MEDIA_FIELDS,
    _compute_medias,
    candidate_paths,
    format_iso_duration,
    nested_get,
    nested_set,
    numeric_value,
    NUMERIC_FIELDS,
    parse_iso_duration,
    parse_note,
    period_bounds,
    update_periodic_notes,
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


class ComputeMediasTests(unittest.TestCase):
    FM_A = {
        "pc": {"tempo_ativo": "PT1H", "tempo_total": "PT4H"},
        "exercicio": True,
        "leitura": False,
        "procrastinacao": 5,
    }
    FM_B = {
        "pc": {"tempo_ativo": "PT2H"},
        "cel": {"tempo_total": "PT30M"},
        "tempo_tela": "PT1H30M",
        "redesSociais": "PT15M",
        "exercicio": True,
        "lazer": True,
        "procrastinacao": 8,
    }
    FM_C = {
        "pc": {"tempo_ativo": "PT45M"},
        "tempo_tela": "PT2H",
        "exercicio": False,
        "leitura": True,
        "procrastinacao": 9,
        "redesSociais": ["PT5M", "PT10M"],
    }
    FM_VAZIA = {"description": "sem dados"}

    def test_medias_iso(self):
        medias = _compute_medias([self.FM_A, self.FM_B, self.FM_C])
        # tempo_ativo: 60+120+45 = 225min / 3 = 75min
        self.assertEqual(medias["pc"]["tempo_ativo_media"], "PT1H15M")
        # tempo_total: só A tem -> 240min
        self.assertEqual(medias["pc"]["tempo_total_media"], "PT4H")
        # tempo_tela: B 90min + C 120min = 105min
        self.assertEqual(medias["tempo_tela_media"], "PT1H45M")
        # redesSociais: lista soma elementos -> B 15 + C 5+10 = 30min / 3 valores
        self.assertEqual(medias["redesSociais_media"], "PT10M")
        # cel: só B
        self.assertEqual(medias["cel"]["tempo_total_media"], "PT30M")

    def test_medias_numericas(self):
        medias = _compute_medias([self.FM_A, self.FM_B, self.FM_C])
        # exercicio: (1+1+0)/3 = 0.666... -> 0.67
        self.assertEqual(medias["exercicio.media"], 0.67)
        # lazer: só B tem -> 1.0
        self.assertEqual(medias["lazer.media"], 1.0)
        # leitura: (0+1)/2 = 0.5
        self.assertEqual(medias["leitura.media"], 0.5)
        # procrastinacao: (5+8+9)/3 = 7.33
        self.assertEqual(medias["procrastinacao.media"], 7.33)

    def test_campos_mapem_para_chaves_planas_ou_aninhadas(self):
        medias = _compute_medias([self.FM_A, self.FM_B, self.FM_C])
        self.assertIn(("exercicio.media",), [dest for dest, _ in NUMERIC_FIELDS])
        self.assertIn(("pc", "tempo_ativo_media"), [dest for dest, _ in MEDIA_FIELDS])

    def test_diaria_sem_campo_nao_conta_no_denominador(self):
        medias = _compute_medias([self.FM_VAZIA, self.FM_A])
        # só A tem tempo_total
        self.assertEqual(medias["pc"]["tempo_total_media"], "PT4H")
        self.assertNotIn("redesSociais_media", medias)
        self.assertNotIn("cel", medias)

    def test_nenhum_dia_valido_nao_gera_chave(self):
        medias = _compute_medias([{"exercicio": "talvez"}, {}])
        self.assertEqual(medias, {})

    def test_duracao_invalida_sai_do_denominador(self):
        medias = _compute_medias([{"tempo_tela": "lixo"}, {"tempo_tela": "PT1H"}])
        self.assertEqual(medias["tempo_tela_media"], "PT1H")

    def test_arredondamento_iso_segundos(self):
        # 59.5s médios -> round -> 60s -> PT1M
        medias = _compute_medias([{"redesSociais": "PT59S"}, {"redesSociais": "PT60S"}])
        self.assertEqual(medias["redesSociais_media"], "PT1M")


JORNADA = Path("01_Arquivos") / "Jornada"


def write_note(root: Path, relative: Path, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class UpdatePeriodicNotesTests(unittest.TestCase):
    TARGET = date(2026, 8, 19)  # quarta-feira, semana ISO 34

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.vault = Path(self._tmp.name)

        self.semanal = write_note(
            self.vault,
            JORNADA / "2026" / "Semanas" / "2026-W34.md",
            "---\n"
            "nota.Tipo: Regs-Semanal\n"
            "year: 2026\n"
            "pc:\n"
            "  tempo_total_media: PT9H\n"
            "cel:\n"
            "  tempo_total_media:\n"
            "procrastinacao.media: 8.17\n"
            "description: velho\n"
            "---\n"
            "\n"
            "# Log\n\nMARCADOR-CORPO\n",
        )
        write_note(
            self.vault,
            JORNADA / "2026" / "08" / "2026-08-18.md",
            "---\npc:\n  tempo_ativo: PT1H\n  tempo_total: PT4H\n"
            "exercicio: true\nleitura: false\nprocrastinacao: 5\n---\ncorpo\n",
        )
        write_note(
            self.vault,
            JORNADA / "2026" / "08" / "2026-08-19.md",
            "---\npc:\n  tempo_ativo: PT2H\ncel:\n  tempo_total: PT30M\n"
            "tempo_tela: PT1H30M\nredesSociais: PT15M\n"
            "exercicio: true\nlazer: true\nprocrastinacao: 8\n---\ncorpo\n",
        )
        write_note(
            self.vault,
            JORNADA / "2026" / "08" / "2026-08-20.md",
            "---\npc:\n  tempo_ativo: PT45M\ntempo_tela: PT2H\n"
            "exercicio: false\nleitura: true\nprocrastinacao: 9\n---\ncorpo\n",
        )

    def _weekly_content(self) -> str:
        return self.semanal.read_text(encoding="utf-8")

    def test_medias_iso_e_numericas_calculadas(self):
        updated = update_periodic_notes(self.TARGET, str(self.vault))

        self.assertIn(str(self.semanal), updated)
        fm, body = parse_note(self._weekly_content())
        self.assertEqual(fm["pc"]["tempo_ativo_media"], "PT1H15M")
        self.assertEqual(fm["pc"]["tempo_total_media"], "PT4H")
        self.assertEqual(fm["cel"]["tempo_total_media"], "PT30M")
        self.assertEqual(fm["tempo_tela_media"], "PT1H45M")
        self.assertEqual(fm["redesSociais_media"], "PT15M")
        self.assertEqual(fm["exercicio.media"], 0.67)
        self.assertEqual(fm["lazer.media"], 1.0)
        self.assertEqual(fm["leitura.media"], 0.5)
        self.assertEqual(fm["procrastinacao.media"], 7.33)

    def test_dias_sem_campo_nao_contam_no_denominador(self):
        update_periodic_notes(self.TARGET, str(self.vault))
        fm, _body = parse_note(self._weekly_content())
        # tempo_tela: só qua (90min) e qui (120min) têm -> 105min
        self.assertEqual(fm["tempo_tela_media"], "PT1H45M")
        # lazer: só qua tem -> 1.0 (terça sem lazer NÃO conta como false)
        self.assertEqual(fm["lazer.media"], 1.0)

    def test_preserva_corpo_e_campos_extras(self):
        update_periodic_notes(self.TARGET, str(self.vault))
        fm, body = parse_note(self._weekly_content())
        self.assertEqual(body.strip(), "# Log\n\nMARCADOR-CORPO")
        self.assertEqual(fm["nota.Tipo"], "Regs-Semanal")
        self.assertEqual(fm["year"], 2026)
        self.assertEqual(fm["description"], "velho")

    def test_periodica_inexistente_pula_sem_erro(self):
        with tempfile.TemporaryDirectory() as vazio:
            updated = update_periodic_notes(self.TARGET, vazio)
            self.assertEqual(updated, [])
            self.assertFalse((Path(vazio) / "01_Arquivos").exists())

    def test_idempotencia(self):
        update_periodic_notes(self.TARGET, str(self.vault))
        primeira = self._weekly_content()

        segunda = update_periodic_notes(self.TARGET, str(self.vault))

        self.assertEqual(segunda, [])
        self.assertEqual(self._weekly_content(), primeira)

    def test_trimestre_e_mes_quando_existem(self):
        trimestral = write_note(
            self.vault, JORNADA / "2026" / "2026-Q3.md", "---\nnota.Tipo: Regs-Tri\n---\ntri\n"
        )
        mensal = write_note(
            self.vault, JORNADA / "2026" / "2026-08.md", "---\nnota.Tipo: Regs-Mes\n---\nmes\n"
        )

        updated = update_periodic_notes(self.TARGET, str(self.vault))

        self.assertIn(str(trimestral), updated)
        self.assertIn(str(mensal), updated)
        fm_tri, _ = parse_note(trimestral.read_text(encoding="utf-8"))
        fm_mes, _ = parse_note(mensal.read_text(encoding="utf-8"))
        self.assertEqual(fm_tri["pc"]["tempo_ativo_media"], "PT1H15M")
        self.assertEqual(fm_mes["procrastinacao.media"], 7.33)

    def test_mensal_na_raiz_da_jornada_tambem_atualiza(self):
        mensal_raiz = write_note(
            self.vault, JORNADA / "2026-08.md", "---\nnota.Tipo: Regs-Mes-Raiz\n---\nx\n"
        )
        updated = update_periodic_notes(self.TARGET, str(self.vault))
        self.assertIn(str(mensal_raiz), updated)

    def test_sync_do_domingo_pega_a_mesma_semana(self):
        updated = update_periodic_notes(date(2026, 8, 23), str(self.vault))
        self.assertIn(str(self.semanal), updated)

    def test_diaria_ilegivel_nao_aborta_sync(self):
        write_note(self.vault, JORNADA / "2026" / "08" / "2026-08-21.md", "---\npc:\n\ttempo_ativo\n---\ncorpo\n")
        updated = update_periodic_notes(self.TARGET, str(self.vault))
        self.assertIn(str(self.semanal), updated)


if __name__ == "__main__":
    unittest.main()
