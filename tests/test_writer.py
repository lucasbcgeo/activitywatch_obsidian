import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from handlers.writer import AW_END, AW_END_INTERVALO, AW_START, AW_START_INTERVALO, update_note


class UpdateNoteTests(unittest.TestCase):
    def test_creates_missing_daily_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "Lucas" / "01_Arquivos" / "Jornada" / "2026" / "07" / "2026-07-02.md"

            update_note(str(note), {"pc": {"total": "PT1H"}}, f"{AW_START}\nbody\n{AW_END}")

            content = note.read_text(encoding="utf-8")
            self.assertIn("pc:", content)
            self.assertIn(f"{AW_START}\nbody\n{AW_END}", content)

    def test_creates_missing_daily_note_from_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template.md"
            template.write_text("<%* templater code %>\n\n# Planejamento\n", encoding="utf-8")
            note = Path(tmp) / "2026" / "07" / "2026-07-02.md"

            update_note(
                str(note),
                {"pc": {"total": "PT1H"}},
                f"{AW_START}\nbody\n{AW_END}",
                str(template),
            )

            content = note.read_text(encoding="utf-8")
            self.assertIn("journal-date: 2026-07-02", content)
            self.assertIn("uri: obsidian://open?vault=Lucas&file=2026-07-02", content)
            self.assertIn("# Planejamento", content)
            self.assertNotIn("templater code", content)


class UpdateIntervaloMarkersTests(unittest.TestCase):
    def _note(self):
        return (
            "---\nnota: x\n---\n\n"
            "## ⏰ Horários\n\n"
            ">> [!alimentacao-fato] Café\n"
            ">> `$= dv.current().alimentacao?.[0] ? \"t\" : \"—\" ` <!-- café-start --><!-- café-end -->\n"
            "\n"
            "<div style=\"margin-bottom: 40px;\"></div>\n"
            "\n"
            f"{AW_START_INTERVALO}\n"
            "\n"
            "> [!multi-column]\n"
            ">> [!sumário]+  Pausa Longa \n"
            ">> <!-- pausa-longa-start --><!-- pausa-longa-end -->\n"
            ">>\n"
            ">\n"
            ">> [!sumário]+  Pausa Curta\n"
            ">> <!-- pausa-curta-start --><!-- pausa-curta-end -->\n"
            ">>\n"
            "\n"
            f"{AW_END_INTERVALO}\n"
            "\n"
            '<div style="margin-bottom: 20px;"></div>\n'
            "\n"
            "## 🗓️ Eventos\n\nconteudo manual\n"
        )

    def _update(self, note, contents):
        update_note(str(note), {"pc": {"total": "PT1H"}}, f"{AW_START}\npc\n{AW_END}", None, contents)

    def test_interior_substituido_preserva_marcadores_e_resto(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-21.md"
            note.write_text(self._note(), encoding="utf-8")
            self._update(note, {"café": "· 31m"})
            content = note.read_text(encoding="utf-8")
            self.assertIn("<!-- café-start -->· 31m<!-- café-end -->", content)
            self.assertIn("dv.current().alimentacao?.[0]", content)
            self.assertIn("conteudo manual", content)
            self.assertIn(">> [!sumário]+  Pausa Longa ", content)

    def test_slug_ausente_skip_sem_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-21.md"
            note.write_text(self._note(), encoding="utf-8")
            self._update(note, {"café": "· 31m", "pausa-longa": "· 12m"})
            content = note.read_text(encoding="utf-8")
            self.assertIn("<!-- pausa-longa-start -->· 12m<!-- pausa-longa-end -->", content)

    def test_todos_slugs_ausentes_nao_altera_horarios(self):
        # update_note sempre mexe em frontmatter/bloco PC; o que não pode
        # acontecer é criação de marcadores ou interior em nota sem eles.
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-21.md"
            note.write_text(
                "---\nnota: x\npc:\n  total: PT1H\n---\n\n## ⏰ Horários\n\nsem marcadores\n",
                encoding="utf-8",
            )
            self._update(note, {"café": "· 31m", "jantar": "· 5m"})
            content = note.read_text(encoding="utf-8")
            self.assertNotIn("café-start", content)
            self.assertNotIn("· 31m", content)
            self.assertIn("sem marcadores", content)

    def test_idempotencia(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-21.md"
            note.write_text(self._note(), encoding="utf-8")
            self._update(note, {"café": "· 31m"})
            primeira = note.read_text(encoding="utf-8")
            self._update(note, {"café": "· 31m"})
            self.assertEqual(note.read_text(encoding="utf-8"), primeira)

    def test_bloco_intervalos_nao_mais_substituido_wholesale(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-21.md"
            note.write_text(self._note(), encoding="utf-8")
            self._update(note, {})
            content = note.read_text(encoding="utf-8")
            # skeleton estático sobrevive intacto quando não há dados
            self.assertIn(">> [!sumário]+  Pausa Curta", content)
            self.assertIn("<!-- pausa-curta-start --><!-- pausa-curta-end -->", content)

    def test_conteudo_vazio_mantem_marcadores_adjacentes(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-21.md"
            note.write_text(self._note(), encoding="utf-8")
            self._update(note, {"café": ""})
            content = note.read_text(encoding="utf-8")
            self.assertIn("<!-- café-start --><!-- café-end -->", content)


if __name__ == "__main__":
    unittest.main()
