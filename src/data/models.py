from dataclasses import dataclass, field


@dataclass
class AppUsage:
    name: str
    duration_seconds: float


@dataclass
class WebVisit:
    domain: str
    duration_seconds: float


@dataclass
class StudyItem:
    name: str
    duration_seconds: float


@dataclass
class Category:
    name: str
    total_seconds: float
    apps: list[AppUsage] = field(default_factory=list)


@dataclass
class DailyActivity:
    date: str
    total_seconds: float
    active_seconds: float
    categories: list[Category] = field(default_factory=list)
    uncategorized: list[AppUsage] = field(default_factory=list)
    web: list[WebVisit] = field(default_factory=list)
    study: list[StudyItem] = field(default_factory=list)
