import re

# Apps: remove .exe e capitaliza
_APP_FRIENDLY_NAMES = {
    "chrome": "Chrome",
    "firefox": "Firefox",
    "obsidian": "Obsidian",
    "windowsterminal": "Terminal",
    "code": "VS Code",
    "chatgpt": "ChatGPT",
    "explorer": "Explorer",
    "lghub": "Logitech Hub",
    "discord": "Discord",
    "spotify": "Spotify",
    "steam": "Steam",
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
    "slack": "Slack",
    "notion": "Notion",
    "anki": "Anki",
    "toggltrack": "Toggl Track",
    "msedge": "Edge",
    "teams": "Teams",
    "excel": "Excel",
    "winword": "Word",
    "powerpnt": "PowerPoint",
    "acrobat": "Acrobat",
    "acrord32": "Acrobat Reader",
    "sumatrapdf": "Sumatra PDF",
}


def clean_app_name(raw: str) -> str:
    """Remove .exe e retorna nome amigável."""
    name = re.sub(r"\.(exe|root\.exe)$", "", raw, flags=re.IGNORECASE).strip()
    lookup = name.lower().replace(".root", "")
    if lookup in _APP_FRIENDLY_NAMES:
        return _APP_FRIENDLY_NAMES[lookup]
    # Capitaliza primeiro caractere como fallback
    return name[:1].upper() + name[1:] if name else raw


# Domínios locais / internos a ignorar
_IGNORED_DOMAIN_PATTERNS = [
    r"^localhost(:\d+)?$",
    r"^127\.0\.0\.1(:\d+)?$",
    r"^0\.0\.0\.0(:\d+)?$",
    r"^192\.168\.\d+\.\d+(:\d+)?$",
    r"^10\.\d+\.\d+\.\d+(:\d+)?$",
    r"^\[::1\](:\d+)?$",
    r"^$",
    r"^newtab$",
    r"^about:",
    r"^chrome:",
    r"^edge:",
]

# Domínios com porta → nome amigável
_PORT_DOMAIN_NAMES = {
    "localhost:5600": "ActivityWatch",
    "127.0.0.1:5600": "ActivityWatch",
    "localhost:3000": "Dev Server",
    "127.0.0.1:3000": "Dev Server",
    "localhost:8080": "Dev Server",
    "127.0.0.1:8080": "Dev Server",
    "localhost:8000": "Dev Server",
    "127.0.0.1:8000": "Dev Server",
    "localhost:5173": "Vite Dev",
    "127.0.0.1:5173": "Vite Dev",
    "localhost:4200": "Angular Dev",
    "127.0.0.1:4200": "Angular Dev",
}


def is_ignored_domain(domain: str) -> bool:
    """Retorna True se o domínio deve ser ignorado (local/interno)."""
    for pattern in _IGNORED_DOMAIN_PATTERNS:
        if re.match(pattern, domain):
            return True
    return False


def clean_domain(domain: str) -> str | None:
    """Limpa domínio. Retorna None se deve ser ignorado.

    Domínios com porta conhecida viram nome amigável.
    Remove www. e trailing dots.
    """
    domain = domain.strip().lower().rstrip(".")

    if is_ignored_domain(domain):
        return None

    # Porta conhecida → nome amigável
    if domain in _PORT_DOMAIN_NAMES:
        return _PORT_DOMAIN_NAMES[domain]

    # Remove www.
    if domain.startswith("www."):
        domain = domain[4:]

    # Remove TLD (.com, .io, .net, .org, .dev, .app, etc.)
    # Mantém subdomínios compostos (ex: blacksmithgu.github → blacksmithgu.github)
    domain = re.sub(r"\.(com|io|net|org|dev|app|co|me|info|xyz|gg|tv|br|pt)$", "", domain)

    return domain


def clean_obsidian_path(path: str, vault_name: str = "") -> str:
    """Retorna só o nome da nota se for do mesmo cofre, caminho completo se de outro."""
    name = path.lstrip("/")
    if name.endswith(".md"):
        name = name[:-3]
    # Se não tem prefixo de outro vault, retorna só o nome do arquivo
    # (arquivos do mesmo vault sempre começam sem vault: prefix)
    parts = name.rsplit("/", 1)
    return parts[-1] if len(parts) > 1 else name
