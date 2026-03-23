import logging
import os
import re

from util.yaml_helpers import deep_merge, parse_note, rebuild_note

logger = logging.getLogger("aw-sync.writer")

AW_START = "<!-- aw:start -->"
AW_END = "<!-- aw:end -->"


def update_note(note_path: str, fm_data: dict, body_block: str) -> None:
    """Atualiza nota diária com dados do ActivityWatch.

    - Frontmatter: deep merge da chave 'pc'
    - Corpo: insere/substitui bloco entre aw:start e aw:end em ## Dados
    """
    if not os.path.isfile(note_path):
        raise FileNotFoundError(f"Nota não encontrada: {note_path}")

    with open(note_path, "r", encoding="utf-8") as f:
        content = f.read()

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
