import logging
import os
import re
from datetime import datetime
from urllib.parse import quote

from util.yaml_helpers import deep_merge, parse_note, rebuild_note

logger = logging.getLogger("aw-sync.writer")

AW_START = "<!-- aw:start -->"
AW_END = "<!-- aw:end -->"


def update_note(
    note_path: str, fm_data: dict, body_block: str, template_path: str | None = None
) -> None:
    """Atualiza nota diária com dados do ActivityWatch.

    - Frontmatter: deep merge da chave 'pc'
    - Corpo: insere/substitui bloco entre aw:start e aw:end em ## Dados
    """
    if os.path.isfile(note_path):
        with open(note_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        parent = os.path.dirname(note_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        content = _render_daily_template(note_path, template_path)
        logger.info("Nota diária criada: %s", note_path)

    frontmatter, body = parse_note(content)

    # Merge frontmatter
    frontmatter = deep_merge(frontmatter, fm_data)
    logger.info("Frontmatter atualizado com chave 'pc'")

    # Merge corpo
    body = _merge_body_block(body, body_block)

    result = rebuild_note(frontmatter, body)

    with open(note_path, "w", encoding="utf-8") as f:
        f.write(result)

    logger.info("Nota salva: %s", note_path)


def _render_daily_template(note_path: str, template_path: str | None) -> str:
    if not template_path:
        return ""
    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"Template de nota diária não encontrado: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    body = re.sub(r"\A<%\*.*?%>\s*", "", template, flags=re.DOTALL)
    return _daily_frontmatter(note_path) + body


def _daily_frontmatter(note_path: str) -> str:
    title = os.path.splitext(os.path.basename(note_path))[0]
    day = datetime.strptime(title, "%Y-%m-%d").date()
    iso_year, iso_week, iso_weekday = day.isocalendar()
    months = [
        "janeiro",
        "fevereiro",
        "março",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    ]
    weekdays = [
        "segunda-feira",
        "terça-feira",
        "quarta-feira",
        "quinta-feira",
        "sexta-feira",
        "sábado",
        "domingo",
    ]
    day_long = f"{weekdays[day.weekday()]}, {day:%d} {months[day.month - 1]} {day:%Y}"
    vault_name = _vault_name_from_note_path(note_path)
    uri = f"obsidian://open?vault={quote(vault_name)}&file={quote(title)}"

    return (
        "---\n"
        "aliases:\n"
        f'  - "{day_long}"\n'
        f'  - "{day:%d-%m-%Y}"\n'
        f'  - "{day:%Y}-{day:%j}"\n'
        f'  - "{iso_year}-W{iso_week:02d}-{iso_weekday}"\n'
        f"uid: {int(datetime.combine(day, datetime.min.time()).timestamp())}\n"
        f'uri: "{uri}"\n'
        f"week: {iso_week:02d}\n"
        f"month: {day:%m}\n"
        f"quarter: {(day.month - 1) // 3 + 1}\n"
        f"year: {day:%Y}\n"
        'nota.Tipo: "Regs-Diário"\n'
        "journal: Jornada_Diária\n"
        f"journal-date: {day:%Y-%m-%d}\n"
        'description: ""\n'
        "banner: https://wallpapers.com/images/hd/calendar-pencil-and-clock-as-tiempo-background-jlwr8f81osug906i.jpg\n"
        "cssclasses:\n"
        "  - wide-page\n"
        "  - esconder-propriedades\n"
        "  - hide-title\n"
        "---\n"
    )


def _vault_name_from_note_path(note_path: str) -> str:
    parts = os.path.normpath(note_path).split(os.sep)
    for marker in ("01_Arquivos", "02_Notas"):
        if marker in parts:
            index = parts.index(marker)
            if index > 0:
                return parts[index - 1]
    return "Lucas"


def _merge_body_block(body: str, block: str) -> str:
    """Insere ou substitui bloco aw:start/end na seção ## Dados."""
    pattern = re.compile(
        rf"{re.escape(AW_START)}.*?{re.escape(AW_END)}",
        re.DOTALL,
    )

    if pattern.search(body):
        # Substituir bloco existente
        body = pattern.sub(block, body)
        logger.info("Bloco AW atualizado (merge)")
    else:
        # Inserir no final de ## Dados
        dados_match = re.search(r"(## Dados\b.*?)(\n## |\n# |\Z)", body, re.DOTALL)
        if dados_match:
            insert_pos = dados_match.end(1)
            body = body[:insert_pos] + "\n" + block + "\n" + body[insert_pos:]
            logger.info("Bloco AW inserido em ## Dados")
        else:
            # Fallback: append no final
            body = body.rstrip() + "\n\n" + block + "\n"
            logger.warning("Seção ## Dados não encontrada, bloco inserido no final")

    return body
