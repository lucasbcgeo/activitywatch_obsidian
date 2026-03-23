import logging
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import requests
from aw_client import ActivityWatchClient

from data.models import AppUsage, Category, DailyActivity, StudyItem, WebVisit
from util.clean import clean_app_name, clean_domain

logger = logging.getLogger("aw-sync.fetch")


def _day_range(target_date: date) -> tuple[datetime, datetime]:
    # Define o início e fim do dia no horário local
    from datetime import time as dt_time
    local_start = datetime.combine(target_date, dt_time.min).astimezone()
    local_end = local_start + timedelta(days=1)
    return local_start, local_end


def _find_bucket(buckets: dict, prefix: str) -> str | None:
    for bid in buckets:
        if bid.startswith(prefix):
            return bid
    return None


def _get_duration(event) -> float:
    """Extrai duração em segundos de um evento (pode ser timedelta ou float)."""
    d = event.get("duration", event.duration if hasattr(event, "duration") else 0)
    if hasattr(d, "total_seconds"):
        return d.total_seconds()
    return float(d)


def _aggregate_events(events: list, key_fn) -> dict[str, float]:
    totals = defaultdict(float)
    for e in events:
        k = key_fn(e)
        if k:
            totals[k] += _get_duration(e)
    return dict(totals)


def fetch_daily(client: ActivityWatchClient, target_date: date) -> DailyActivity:
    """Busca dados de todos os watchers para um dia específico."""
    start, end = _day_range(target_date)
    buckets = client.get_buckets()

    # --- Window watcher (apps) ---
    window_bid = _find_bucket(buckets, "aw-watcher-window")
    app_totals: dict[str, float] = {}
    total_seconds = 0.0
    if window_bid:
        events = client.get_events(window_bid, limit=-1, start=start, end=end)
        raw_totals = _aggregate_events(events, lambda e: e.get("data", {}).get("app", ""))
        for raw_name, secs in raw_totals.items():
            clean = clean_app_name(raw_name)
            app_totals[clean] = app_totals.get(clean, 0.0) + secs
        total_seconds = sum(app_totals.values())
        logger.info("Window: %d eventos, %.0fs total", len(events), total_seconds)

    # --- AFK watcher (tempo ativo) ---
    afk_bid = _find_bucket(buckets, "aw-watcher-afk")
    active_seconds = 0.0
    if afk_bid:
        events = client.get_events(afk_bid, limit=-1, start=start, end=end)
        for e in events:
            if e.get("data", {}).get("status") == "not-afk":
                active_seconds += _get_duration(e)
        logger.info("AFK: tempo ativo %.0fs", active_seconds)

    # --- Web watcher (sites) ---
    web_bid = _find_bucket(buckets, "aw-watcher-web")
    web_list: list[WebVisit] = []
    clean_totals: dict[str, float] = {}
    if web_bid:
        events = client.get_events(web_bid, limit=-1, start=start, end=end)
        raw_domain_totals = _aggregate_events(
            events, lambda e: e.get("data", {}).get("url", "").split("/")[2] if "://" in e.get("data", {}).get("url", "") else ""
        )
        for raw_domain, secs in raw_domain_totals.items():
            cleaned = clean_domain(raw_domain)
            if cleaned:
                clean_totals[cleaned] = clean_totals.get(cleaned, 0.0) + secs
        web_list = [
            WebVisit(domain=d, duration_seconds=s)
            for d, s in sorted(clean_totals.items(), key=lambda x: -x[1])
        ]
        logger.info("Web: %d domínios", len(web_list))

    # --- Estudo aggregation (Filtra apps e domínios específicos) ---
    study_items: list[StudyItem] = []
    study_apps = ["Anki", "Toggl Track"]
    study_domains = ["qconcursos", "estrategiaconcursos"]

    for app_name, secs in app_totals.items():
        if app_name in study_apps:
            study_items.append(StudyItem(name=app_name, duration_seconds=secs))

    for domain, secs in clean_totals.items():
        if any(sd in domain for sd in study_domains):
            study_items.append(StudyItem(name=domain, duration_seconds=secs))

    study_items.sort(key=lambda x: -x.duration_seconds)
    logger.info("Estudo: %d itens identificados", len(study_items))

    # --- Categorias (via settings do AW) ---
    categories = _build_categories(client, window_bid, start, end)

    apps_sorted = [
        AppUsage(name=name, duration_seconds=dur)
        for name, dur in sorted(app_totals.items(), key=lambda x: -x[1])
        if name
    ]

    return DailyActivity(
        date=target_date.isoformat(),
        total_seconds=total_seconds,
        active_seconds=active_seconds,
        categories=categories,
        uncategorized=apps_sorted,
        web=web_list,
        study=study_items,
    )


def _fetch_categories(host: str, port: int) -> list[dict]:
    """Busca regras de categorias do ActivityWatch via settings API."""
    try:
        r = requests.get(f"http://{host}:{port}/api/0/settings", timeout=5)
        r.raise_for_status()
        return r.json().get("classes", [])
    except Exception as e:
        logger.warning("Não foi possível buscar categorias do AW: %s", e)
        return []


def _classify_event(event, classes: list[dict]) -> str:
    """Classifica um evento pela primeira categoria cujo regex bate."""
    app = event.get("data", {}).get("app", "")
    title = event.get("data", {}).get("title", "")
    search_text = f"{app} {title}"

    for cls in classes:
        rule = cls.get("rule", {})
        regex = rule.get("regex", "")
        rtype = rule.get("type", "")
        if rtype != "regex" or not regex:
            continue
        try:
            if re.search(regex, search_text, re.IGNORECASE):
                return " > ".join(cls["name"])
        except re.error:
            continue

    return "Uncategorized"


def _build_categories(
    client: ActivityWatchClient,
    window_bid: str | None,
    start: datetime,
    end: datetime,
) -> list[Category]:
    """Classifica eventos do dia nas categorias configuradas no AW."""
    if not window_bid:
        return []

    import os
    host = os.environ.get("AW_HOST", "localhost")
    port = int(os.environ.get("AW_PORT", "5600"))
    classes = _fetch_categories(host, port)
    if not classes:
        return []

    events = client.get_events(window_bid, limit=-1, start=start, end=end)

    cat_seconds: dict[str, float] = defaultdict(float)
    for e in events:
        cat_name = _classify_event(e, classes)
        cat_seconds[cat_name] += _get_duration(e)

    categories = [
        Category(name=name, total_seconds=secs)
        for name, secs in sorted(cat_seconds.items(), key=lambda x: -x[1])
        if secs > 0
    ]

    logger.info("Categorias: %d categorias encontradas", len(categories))
    return categories
