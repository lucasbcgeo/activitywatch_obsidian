"""Migra notas diárias e o template para marcadores de intervalo por métrica.

Insere <!-- {slug}-start -->/<!-- {slug}-end --> nos callouts Café/Almoço/Jantar/
Exercícios de ## ⏰ Horários e o skeleton estático de Pausa Longa/Pausa Curta.
Idempotente. Reversível via git do vault.
"""
import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TEMPLATE_REL = os.path.join(
    "99_Sistema", "_templates", "Nota Inteira", "Jornada", "Nota Diária 2_ISO.md"
)
NOTES_REL = os.path.join("01_Arquivos", "Jornada")

AW_START_INTERVALOS = "<!-- aw:start-intervalos -->"
AW_END_INTERVALOS = "<!-- aw:end-intervalos -->"

INLINE_TARGETS = [
    ("café", re.compile(r"^>> \[!alimentacao-fato\]\s*Café\b.*$", re.MULTILINE)),
    ("almoço", re.compile(r"^>> \[!alimentacao-fato\]\s*Almoço\b.*$", re.MULTILINE)),
    ("jantar", re.compile(r"^>> \[!alimentacao-fato\]\s*Jantar\b.*$", re.MULTILINE)),
    ("exercícios", re.compile(r"^>> \[!exercicios-fato\]\s*Exerc[ií]cios\b.*$", re.MULTILINE)),
]

SKELETON_INNER = (
    "> [!multi-column]\n"
    ">> [!sumário]+  Pausa Longa \n"
    ">> <!-- pausa-longa-start --><!-- pausa-longa-end -->\n"
    ">>\n"
    ">\n"
    ">> [!sumário]+  Pausa Curta\n"
    ">> <!-- pausa-curta-start --><!-- pausa-curta-end -->\n"
    ">>"
)

DIV20 = '<div style="margin-bottom: 20px;"></div>'
DIV40 = '<div style="margin-bottom: 40px;"></div>'
EVENTOS_RE = re.compile(r"^#{2,3} [^\n]*Eventos[^\n]*$", re.MULTILINE)
CALLOUT_LINE_RE = re.compile(r"^>>[^\n]*$", re.MULTILINE)


def _append_marker_after_query(text: str, title_match: re.Match, slug: str) -> str | None:
    """Acha a linha de query seguinte ao título do callout e anexa os marcadores."""
    for cand in CALLOUT_LINE_RE.finditer(text, title_match.end()):
        line = cand.group(0)
        if "[!" in line:
            return None  # chegou em outro callout sem achar query
        if "`" in line:
            abs_start, abs_end = cand.span()
            prefix = text[:abs_end].rstrip()
            suffix = text[abs_end:]
            return prefix + f" <!-- {slug}-start --><!-- {slug}-end -->" + suffix
    return None


def migrate_content(text: str) -> tuple[str, list[str]]:
    """Aplica a migração em um conteúdo. Retorna (novo_texto, avisos)."""
    warnings: list[str] = []

    # 1) Marcadores inline nos callouts existentes
    for slug, title_re in INLINE_TARGETS:
        if f"<!-- {slug}-start -->" in text:
            continue
        m = title_re.search(text)
        if not m:
            continue
        new_text = _append_marker_after_query(text, m, slug)
        if new_text is None:
            warnings.append(f"linha de query do '{slug}' não encontrada")
            continue
        text = new_text

    # 2) Skeleton de Pausas
    block = f"{AW_START_INTERVALOS}\n\n{SKELETON_INNER}\n\n{AW_END_INTERVALOS}"
    if AW_START_INTERVALOS in text:
        if "pausa-longa-start" not in text:
            block_re = re.compile(
                rf"{re.escape(AW_START_INTERVALOS)}.*?{re.escape(AW_END_INTERVALOS)}",
                re.DOTALL,
            )
            # lambda => reposição literal (sem processar escapes de re.sub)
            text = block_re.sub(lambda _m: block, text)
    else:
        ev = EVENTOS_RE.search(text)
        if not ev:
            warnings.append("seção Eventos não encontrada")
        else:
            head = text[: ev.start()].rstrip()
            tail = text[ev.start():]
            pieces = []
            if not (head.endswith(DIV40) or head.endswith(DIV20)):
                pieces.append(DIV40)
            pieces.append(block)
            if not head.endswith(DIV20):
                pieces.append(DIV20)
            text = head + "\n\n" + "\n\n".join(pieces) + "\n\n" + tail

    return text, warnings


def collect_files(vault: Path) -> list[Path]:
    files = [vault / TEMPLATE_REL]
    files.extend(sorted((vault / NOTES_REL).rglob("*.md")))
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-root", default=None, help="Raiz do vault (default: VAULT_PATH)")
    parser.add_argument("--dry-run", action="store_true", help="Não escreve, só lista")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    vault = Path(args.vault_root or os.environ.get("VAULT_PATH", "")).resolve()
    if not vault.is_dir():
        sys.exit(f"Vault não encontrado: {vault}")

    migrated = skipped = 0
    for path in collect_files(vault):
        rel = path.relative_to(vault).as_posix()
        try:
            original = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            print(f"[erro ] {rel}: {e}")
            skipped += 1
            continue
        new_text, warnings = migrate_content(original)
        for w in warnings:
            print(f"[aviso] {rel}: {w}")
        if new_text == original:
            continue
        migrated += 1
        if args.dry_run:
            print(f"[seco ] {rel}")
        else:
            try:
                path.write_text(new_text, encoding="utf-8", newline="\n")
            except OSError as e:
                print(f"[erro ] {rel}: {e}")
                migrated -= 1
                skipped += 1
                continue
            print(f"[ok   ] {rel}")

    acao = "seriam migradas" if args.dry_run else "migradas"
    print(f"\n{migrated} arquivo(s) {acao}, {skipped} pulado(s)")


if __name__ == "__main__":
    main()
