import re
import yaml


def parse_note(content: str) -> tuple[dict, str]:
    """Separa frontmatter YAML do corpo da nota.

    Returns:
        (frontmatter_dict, body_string)
    """
    match = re.match(r"^---\n(.*?\n)---\n?(.*)", content, re.DOTALL)
    if not match:
        return {}, content
    fm = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)
    return fm, body


def rebuild_note(frontmatter: dict, body: str) -> str:
    """Reconstroi a nota com frontmatter YAML + corpo."""
    fm_str = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=1000,
    )
    return f"---\n{fm_str}---\n{body}"


def deep_merge(base: dict, override: dict) -> dict:
    """Merge profundo: override atualiza base sem apagar chaves existentes."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
