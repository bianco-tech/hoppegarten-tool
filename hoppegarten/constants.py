GROUND_OPTIONS = ["gut", "gut-weich", "weich", "schwer", "fest"]
GROUND_CODES = {
    "gut": {"g"},
    "gut-weich": {"g", "w"},
    "weich": {"w"},
    "schwer": {"s"},
    "fest": {"f"},
}
RECENCY_W = [1.0, 0.90, 0.80, 0.70, 0.60, 0.50, 0.40, 0.30, 0.20, 0.10]
AGE_SCORES = {3: 0.60, 4: 0.90, 5: 1.00, 6: 0.90, 7: 0.70, 8: 0.50}

TIER_RANGES = {
    "strong": (0.70, 1.00),
    "medium": (0.40, 0.70),
    "neutral": (0.20, 0.40),
    "weak": (0.05, 0.10),
}

TIER_COLORS = {
    "strong": "#16a34a",
    "medium": "#ca8a04",
    "neutral": "#6b7280",
    "weak": "#dc2626",
}

TIER_ICONS = {
    "strong": "🟢",
    "medium": "🟡",
    "neutral": "⚪",
    "weak": "🔴",
}

PLAY_COLORS = {
    "play": "#16a34a",
    "optional": "#ca8a04",
    "skip": "#dc2626",
    "pending": "#9ca3af",
}
