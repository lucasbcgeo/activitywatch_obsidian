import logging
import os
import re
from datetime import datetime
from urllib.parse import quote

from util.yaml_helpers import deep_merge, parse_note, rebuild_note

logger = logging.getLogger("aw-sync.writer")

AW_START = "<!-- aw:start -->"
AW_END = "<!-- aw:end -->"
AW_START_INTERVALO = "<!-- aw:start-intervalos -->"
AW_END_INTERVALO = "<!-- aw:end-intervalos -->"


def update_note(
    note_path: str,
    fm_data: dict,
    body_block: str,
    template_path: str | None = None,
    intervalo_block: str | None = None,
) -> None:
    """Atualiza nota diária com dados do ActivityWatch.

    - Frontmatter: deep merge da chave 'pc'
    - Corpo (PC): insere/substitui bloco entre aw:start e aw:end em ## Dados
    - Corpo (Intervalos): insere/substitui bloco entre aw:start-intervalos e
      aw:end-intervalos em ## Horários (se intervalo_block fornecido)
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

    # Merge corpo (PC)
    body = _merge_body_block(body, body_block)

    # Merge corpo (Intervalos) — opcional
    if intervalo_block is not None:
        body = _merge_body_block(
            body,
            intervalo_block,
            AW_START_INTERVALO,
            AW_END_INTERVALO,
            "## ⏰ Horários",
        )

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


def _merge_body_block(
    body: str,
    block: str,
    start: str = AW_START,
    end: str = AW_END,
    section_fallback: str = "## Dados",
) -> str:
    """Insere ou substitui bloco delimitado por start/end.

    Se marcadores existem, substitui conteudo entre eles.
    Se nao, insere apos section_fallback (secao header). Fallback final: append.
    """
    pattern = re.compile(rf"{re.escape(start)}.*?{re.escape(end)}", re.DOTALL)

    if pattern.search(body):
        body = pattern.sub(block, body)
        logger.info("Bloco %s atualizado (merge)", start)
    else:
        section_match = re.search(
            rf"({re.escape(section_fallback)}\b.*?)(\n## |\n# |\Z)",
            body,
            re.DOTALL,
        )
        if section_match:
            insert_pos = section_match.end(1)
            body = body[:insert_pos] + "\n" + block + "\n" + body[insert_pos:]
            logger.info("Bloco %s inserido em %s", start, section_fallback)
        else:
            body = body.rstrip() + "\n\n" + block + "\n"
            logger.warning(
                "%s nao encontrada, bloco %s inserido no final",
                section_fallback,
                start,
            )

    return body
