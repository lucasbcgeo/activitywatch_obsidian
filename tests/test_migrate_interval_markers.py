import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from migrate_interval_markers import migrate_content


NOTE_FIXTURE = (
    "---\nnota: x\n---\n\n"
    "## ⏰ Horários\n\n"
    ">> [!alimentacao-fato] Café\n"
    ">> `$= dv.current().alimentacao?.[0] ? \"t\" : \"—\" `\n"
    ">\n"
    ">> [!alimentacao-fato] Almoço\n"
    ">> `$= dv.current().alimentacao?.[1] ? \"t\" : \"—\" `\n"
    "\n"
    '<div style="margin-bottom: 40px;"></div>\n'
    "\n"
    "## 🗓️ Eventos\n\nconteudo\n"
)

OLD_BLOCK_FIXTURE = (
    "## ⏰ Horários\n\n"
    ">> [!alimentacao-fato] Café\n"
    ">> `$= q `\n"
    "\n"
    '<div style="margin-bottom: 40px;"></div>\n'
    "\n"
    "<!-- aw:start-intervalos -->\n"
    "> [!multi-column]\n"
    ">> [!pause]+  Intervalo\n"
    ">> - Café da manhã (31m)\n"
    ">\n"
    "<!-- aw:end-intervalos -->\n"
    "\n"
    '<div style="margin-bottom: 20px;"></div>\n'
    "\n"
    "## 🗓️ Eventos\n\nconteudo\n"
)


class MigrateContentTests(unittest.TestCase):
    def test_insere_inline_nos_callouts_e_skeleton_antes_de_eventos(self):
        new, warnings = migrate_content(NOTE_FIXTURE)
        self.assertEqual(warnings, [])
        self.assertIn('` <!-- café-start --><!-- café-end -->', new)
        self.assertIn('` <!-- almoço-start --><!-- almoço-end -->', new)
        idx_div40 = new.index('<div style="margin-bottom: 40px;"></div>')
        idx_start = new.index("<!-- aw:start-intervalos -->")
        idx_end = new.index("<!-- aw:end-intervalos -->")
        idx_div20 = new.index('<div style="margin-bottom: 20px;"></div>')
        idx_eventos = new.index("## 🗓️ Eventos")
        self.assertLess(idx_div40, idx_start)
        self.assertLess(idx_start, idx_end)
        self.assertLess(idx_end, idx_div20)
        self.assertLess(idx_div20, idx_eventos)
        self.assertEqual(new.count("pausa-longa-start"), 1)
        self.assertIn("[!sumário]+  Pausa Longa", new)
        self.assertIn("[!sumário]+  Pausa Curta", new)
        # div40 não duplicado
        self.assertEqual(new.count('<div style="margin-bottom: 40px;"></div>'), 1)

    def test_idempotente(self):
        once, _ = migrate_content(NOTE_FIXTURE)
        twice, warnings = migrate_content(once)
        self.assertEqual(twice, once)
        self.assertEqual(warnings, [])

    def test_substitui_bloco_antigo_pelo_skeleton(self):
        new, warnings = migrate_content(OLD_BLOCK_FIXTURE)
        self.assertEqual(warnings, [])
        self.assertNotIn("- Café da manhã (31m)", new)
        self.assertNotIn("[!pause]", new)
        self.assertIn("pausa-longa-start", new)
        self.assertEqual(new.count('<div style="margin-bottom: 40px;"></div>'), 1)
        self.assertEqual(new.count('<div style="margin-bottom: 20px;"></div>'), 1)

    def test_nota_sem_ancoras_avisa_e_nao_altera(self):
        texto = "# Dia\n\nconteudo solto\n"
        new, warnings = migrate_content(texto)
        self.assertEqual(new, texto)
        self.assertTrue(any("Eventos" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
