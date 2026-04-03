from __future__ import annotations

import streamlit as st
import re
import math
from pathlib import Path

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hoppegarten · 5. April",
    page_icon="🐎",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 1rem 1rem 3rem 1rem !important;
    max-width: 720px !important;
}
/* Wettschein row */
.schein-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 8px;
    background: #f8f9fa;
    margin-bottom: 6px;
    font-size: 0.92rem;
}
.schein-row-value {
    background: #f0fff4;
    border-left: 4px solid #198754;
}
.schein-badge {
    display: inline-block;
    background: #0d6efd;
    color: #fff;
    padding: 1px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 700;
    white-space: nowrap;
}
.schein-badge-sieg   { background: #198754; }
.schein-badge-platz  { background: #0d6efd; }
.schein-badge-zweier { background: #6f42c1; }
.schein-badge-dreier { background: #fd7e14; }
.schein-badge-zwilling { background: #20c997; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────
GROUND_OPTIONS = ["gut", "gut-weich", "weich", "schwer", "fest"]
GROUND_CODES = {
    "gut":       {"g"},
    "gut-weich": {"g", "w"},
    "weich":     {"w"},
    "schwer":    {"s"},
    "fest":      {"f"},
}
RECENCY_W = [1.0, 0.90, 0.80, 0.70, 0.60, 0.50, 0.40, 0.30, 0.20, 0.10]
AGE_SCORES = {3: 0.60, 4: 0.90, 5: 1.00, 6: 0.90, 7: 0.70, 8: 0.50}


# ─── Internal helpers ─────────────────────────────────────────────────────────
def _parse_prize_int(prize_str: str) -> int:
    """Parse '€30,000' or '€7,200' → int."""
    cleaned = re.sub(r"[€,\s]", "", prize_str)
    try:
        return int(cleaned)
    except ValueError:
        return 10000


def _parse_distance_m(distance_str: str) -> int:
    """Parse '1800m' → 1800."""
    m = re.search(r"(\d+)", distance_str)
    return int(m.group(1)) if m else 2000


# ─── Parsing ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_races(path: str) -> list:
    content = Path(path).read_text(encoding="utf-8")
    race_blocks = re.split(r"(?m)^# Race\s+", content)
    races = []

    for block in race_blocks[1:]:
        lines = block.split("\n")

        # ── Header ──
        header_parts = [p.strip() for p in lines[0].split("|")]
        race_num        = header_parts[0].strip()
        distance        = header_parts[1] if len(header_parts) > 1 else ""
        prize           = header_parts[2] if len(header_parts) > 2 else ""
        runners_str     = header_parts[3] if len(header_parts) > 3 else ""
        time_conditions = header_parts[4] if len(header_parts) > 4 else ""

        prize_int = _parse_prize_int(prize)

        # ── Notes (comment lines before first ##) ──
        notes = []  # list of (category, text)
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith("## ") or (stripped.startswith("## ") is False and
               any(stripped.startswith(f"## {c}") for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")):
                break
            if not stripped.startswith("#") or "═══" in stripped:
                continue
            text = stripped.lstrip("# ").strip()
            if not text:
                continue
            if text.upper().startswith("HINWEIS:"):
                notes.append(("hinweis", text[8:].strip()))
            elif text.upper().startswith("PROGRAMMTIPP:"):
                notes.append(("tipp", text[13:].strip()))
            elif text.upper().startswith("EXPERTEN-KONSENS:"):
                notes.append(("experte", text[17:].strip()))
            elif text.upper().startswith("VIERERWETTE:"):
                notes.append(("viererwette", text[12:].strip()))
            else:
                notes.append(("info", text))

        # ── Horses (split on ## ) ──
        rest = "\n".join(lines[1:])
        horse_blocks = re.split(r"(?m)^## ", rest)

        horses = []
        for hblock in horse_blocks:
            hblock = hblock.strip()
            if not hblock:
                continue
            hlines = hblock.split("\n")
            name = hlines[0].strip()
            if not name or name.startswith("#") or "═══" in name:
                continue

            jockey, jockey_rate, trainer = "", 0, ""
            weight, age = 58.0, 5
            box, gag, rennpause = 0, 0.0, 150
            career_starts, career_wins = 0, 0
            season_starts, season_wins, season_placed = 0, 0, 0
            form_str, dist_affinity, expert_tip = "-", "neutral", False

            for line in hlines[1:]:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("Jockey:"):
                    raw = line[7:].strip()
                    m = re.search(r"\((\d+)%\)", raw)
                    if m:
                        jockey_rate = int(m.group(1))
                        jockey = raw[: m.start()].strip()
                    else:
                        jockey = raw
                elif line.startswith("Trainer:"):
                    trainer = line[8:].strip()
                elif line.startswith("Weight:"):
                    try:
                        weight = float(line[7:].strip())
                    except ValueError:
                        pass
                elif line.startswith("Age:"):
                    try:
                        age = int(line[4:].strip())
                    except ValueError:
                        pass
                elif line.startswith("Career:"):
                    parts = line[7:].strip().split("/")
                    if len(parts) == 2:
                        try:
                            career_starts, career_wins = int(parts[0]), int(parts[1])
                        except ValueError:
                            pass
                elif line.startswith("Box:"):
                    try:
                        box = int(line[4:].strip())
                    except ValueError:
                        pass
                elif line.startswith("GAG:"):
                    try:
                        gag = float(line[4:].strip())
                    except ValueError:
                        pass
                elif line.startswith("Rennpause:"):
                    try:
                        rennpause = int(line[10:].strip())
                    except ValueError:
                        pass
                elif line.startswith("Season2025:") or line.startswith("Season2026:"):
                    raw_val = line.split(":", 1)[1].strip()
                    parts = raw_val.split("/")
                    if len(parts) == 3:
                        try:
                            season_starts = int(parts[0])
                            season_wins   = int(parts[1])
                            season_placed = int(parts[2])
                        except ValueError:
                            pass
                elif line.startswith("Form:"):
                    form_str = line[5:].strip()
                elif line.startswith("DistancePref:"):
                    dist_affinity = line[13:].strip().lower()
                elif line.startswith("ExpertTip:"):
                    expert_tip = line[10:].strip().lower() == "yes"

            horses.append(dict(
                name=name, jockey=jockey, jockey_rate=jockey_rate, trainer=trainer,
                weight=weight, age=age,
                box=box, gag=gag, rennpause=rennpause,
                career_starts=career_starts, career_wins=career_wins,
                season_starts=season_starts, season_wins=season_wins,
                season_placed=season_placed,
                form=form_str, distance=dist_affinity, expert_tip=expert_tip,
            ))

        if horses:
            races.append(dict(
                num=race_num, distance=distance, prize=prize, prize_int=prize_int,
                runners=runners_str, time_conditions=time_conditions,
                notes=notes, horses=horses,
            ))

    return races


# ─── Form parsing ─────────────────────────────────────────────────────────────
def parse_form_runs(form_str: str) -> list:
    """Return (ground_code, position) tuples. Most recent first (as listed)."""
    if form_str.strip() in ("-", "", "0"):
        return []
    runs = []
    for token in form_str.split(","):
        token = token.strip()
        if not token:
            continue
        ground = token[0]           # g/w/f/s/S
        pos_str = token[1:]
        try:
            pos = int(pos_str)
        except ValueError:
            continue
        runs.append((ground, pos))
    return runs


# ─── Scoring ──────────────────────────────────────────────────────────────────
def pos_points(pos: int) -> float:
    """Finishing position → score [0,100]."""
    if pos <= 0:
        return 0
    return {1: 100, 2: 80, 3: 60, 4: 40}.get(pos, 20)


def score_form(form_str: str, today_codes: set) -> float:
    """Form score [0,1] with ground-matching bonus, ignoring Sand runs."""
    runs = parse_form_runs(form_str)
    grass_runs = [(g, p) for g, p in runs if g.upper() != "S"]

    if not grass_runs:
        return 0.50  # debutant or all-sand → neutral

    total, max_possible = 0.0, 0.0
    for i, (ground, pos) in enumerate(grass_runs[:10]):
        w = RECENCY_W[i] if i < len(RECENCY_W) else 0.05
        base = pos_points(pos)
        mult = 1.20 if ground.lower() in today_codes else 0.85
        total += base * w * mult
        max_possible += 100 * w * 1.20  # max: win on matching ground

    return total / max_possible if max_possible else 0.50


def ground_compat(form_str: str, today_codes: set) -> str:
    """Return '✅', '⚠️', '❌', or '?' for ground compatibility."""
    runs = parse_form_runs(form_str)
    grass = [(g, p) for g, p in runs if g.upper() != "S"]
    if not grass:
        return "?"
    matching = sum(1 for g, _ in grass if g.lower() in today_codes)
    ratio = matching / len(grass)
    if ratio >= 0.50:
        return "✅"
    if ratio >= 0.20:
        return "⚠️"
    return "❌"


def score_jockey(rate: int) -> float:
    effective = rate if rate > 0 else 8   # 0% = no data, assume journeyman ~8%
    return min(effective, 30) / 30


def score_distance(affinity: str) -> float:
    return {"good": 1.0, "neutral": 0.60, "bad": 0.20}.get(affinity.lower(), 0.60)


def score_career(starts: int, wins: int) -> float:
    if starts == 0:
        return 0.50
    return min(wins / starts, 0.50) / 0.50


def score_weight(horse_kg: float, field_kg: list) -> float:
    avg = sum(field_kg) / len(field_kg) if field_kg else horse_kg
    penalty = max(0.0, horse_kg - avg)
    return max(0.0, 1.0 - penalty / 10.0)


def score_age(age: int) -> float:
    return AGE_SCORES.get(age, 0.40)


def score_season(season_starts: int, season_wins: int, season_placed: int) -> float:
    """Season-form score [0, 1]: captures win rate, consistency, and activity."""
    if season_starts == 0:
        return 0.50
    season_win_rate   = season_wins / season_starts
    season_place_rate = (season_wins + season_placed) / season_starts
    if season_starts >= 8:
        activity_bonus = 0.05
    elif season_starts >= 5:
        activity_bonus = 0.02
    else:
        activity_bonus = 0.0
    raw = (0.50 * season_win_rate
           + 0.35 * season_place_rate
           + 0.15 * min(season_starts, 15) / 15)
    raw += activity_bonus
    return min(raw, 1.0)


def score_box(box: int, n_runners: int, distance_m: int) -> float:
    """Draw bias score [0, 1]. Only applied for short distances with large fields."""
    if box == 0:
        return 0.50  # not set → neutral
    if distance_m <= 1800 and n_runners >= 7:
        if box <= n_runners // 3:
            return 0.65   # inner draw advantage
        if box > 2 * n_runners // 3:
            return 0.35   # outer draw penalty
        return 0.50
    return 0.50  # no significant bias for longer races or small fields


def score_gag(gag: float, field_gag_values: list) -> float:
    """Relative GAG handicap score [0, 1] within the race field."""
    if gag == 0:
        return 0.50  # debütant / no rating → neutral
    non_zero = [v for v in field_gag_values if v > 0]
    if not non_zero:
        return 0.50
    lo, hi = min(non_zero), max(non_zero)
    return (gag - lo) / (hi - lo + 0.01)


def score_rennpause(rennpause: int) -> float:
    """Fitness signal from days since last race."""
    if rennpause == 0:
        return 0.50    # debütant / no data → neutral
    if rennpause <= 100:
        return 0.75    # recently active, fit
    if rennpause <= 200:
        return 0.60    # typical winter break, acceptable
    if rennpause <= 365:
        return 0.35    # long break, fitness concern
    return 0.10        # very long break, strong negative signal


def score_prize(prize_str: str) -> float:
    """Field class factor based on prize money. NOT used in composite score."""
    prize = _parse_prize_int(prize_str)
    if prize >= 25000:
        return 0.0   # strong field → be conservative
    if prize >= 15000:
        return 0.5
    return 1.0       # weak field → Sieg more viable


def blend_prob(model_prob: float, market_odds: float, blend_weight: float = 0.35) -> float:
    """Blend model estimate with market implied probability."""
    implied = 1.0 / market_odds
    return (1 - blend_weight) * model_prob + blend_weight * implied


def composite(horse: dict, field_kg: list, field_gag: list, today_codes: set,
              n_runners: int, distance_m: int) -> float:
    f = score_form(horse["form"], today_codes)
    g = score_gag(horse["gag"], field_gag)
    j = score_jockey(horse["jockey_rate"])
    s = score_season(horse["season_starts"], horse["season_wins"], horse["season_placed"])
    d = score_distance(horse["distance"])
    r = score_rennpause(horse["rennpause"])
    c = score_career(horse["career_starts"], horse["career_wins"])
    e = 1.0 if horse["expert_tip"] else 0.0
    b = score_box(horse.get("box", 0), n_runners, distance_m)

    raw = (0.25 * f + 0.20 * g + 0.12 * j + 0.10 * s + 0.10 * d +
           0.08 * r + 0.05 * c + 0.05 * e + 0.05 * b)

    return raw * 1.10 if horse["expert_tip"] else raw


def race_probs(horses: list, today_codes: set,
               n_runners: int, distance_m: int) -> list:
    field_kg  = [h["weight"] for h in horses]
    field_gag = [h["gag"] for h in horses if h["gag"] > 0]
    scores = [
        composite(h, field_kg, field_gag, today_codes, n_runners, distance_m)
        for h in horses
    ]
    total = sum(scores) or 1.0
    return [s / total for s in scores]


# ─── Kelly ────────────────────────────────────────────────────────────────────
def kelly(est_prob: float, decimal_odds: float, bankroll: float) -> tuple:
    """Half-Kelly, capped at 25%. Returns (pct, eur). Used for display in horse cards."""
    if decimal_odds <= 1.0 or est_prob <= 0:
        return 0.0, 0.0
    b = decimal_odds - 1.0
    k = (b * est_prob - (1.0 - est_prob)) / b
    if k <= 0:
        return 0.0, 0.0
    k = min(k * 0.5, 0.25)
    return round(k * 100, 1), round(k * bankroll, 2)


def full_kelly_frac(est_prob: float, decimal_odds: float) -> float:
    """Full (uncapped) Kelly fraction [0, 1]."""
    if decimal_odds <= 1.0 or est_prob <= 0:
        return 0.0
    b = decimal_odds - 1.0
    k = (b * est_prob - (1.0 - est_prob)) / b
    return max(0.0, k)


# ─── Budget-aware stake system ────────────────────────────────────────────────
_TIER_RANGES = {
    "strong":  (0.70, 1.00),
    "medium":  (0.40, 0.70),
    "neutral": (0.20, 0.40),
    "weak":    (0.05, 0.10),
}


def value_tier(value: float) -> str:
    if value >= 1.25:
        return "strong"
    if value >= 1.00:
        return "medium"
    if value >= 0.90:
        return "neutral"
    return "weak"


def budget_stake(kelly_frac: float, race_budget: float, tier: str, min_bet: float) -> float:
    """
    Combine Kelly confidence with tier-based budget allocation.
    Kelly normalised against 0.30 (30% full-Kelly ≈ realistic upper bound).
    """
    lo, hi = _TIER_RANGES.get(tier, (0.20, 0.40))
    kelly_norm = min(kelly_frac / 0.30, 1.0)
    pct = lo + kelly_norm * (hi - lo)
    stake = round(pct * race_budget, 2)

    if tier == "weak":
        return 0.0 if stake < min_bet else stake

    return max(stake, min_bet)


def edge_ratio(ranked: list) -> float:
    if len(ranked) < 2 or ranked[1][1] <= 0:
        return 999.0
    return ranked[0][1] / ranked[1][1]


def prob_gap(ranked: list) -> float:
    if len(ranked) < 2:
        return ranked[0][1] if ranked else 0.0
    return ranked[0][1] - ranked[1][1]


def decide_bet_type(ranked: list, n_runners: int, prize_int: int = 10000) -> str:
    """
    Main recommended bet type for the top pick.
    Sieg thresholds adjusted by field class (prize_int).
    """
    if not ranked:
        return "Platz"

    gap = prob_gap(ranked)
    edge = edge_ratio(ranked)
    top_prob = ranked[0][1]

    # Sieg threshold by field class
    if prize_int >= 25000:
        sieg_ok = gap >= 0.12 and edge >= 1.45   # Listenrennen: very strict
    elif prize_int < 10000:
        sieg_ok = gap >= 0.06 and edge >= 1.20   # weak field: more lenient
    else:
        sieg_ok = gap >= 0.08 or edge >= 1.30    # mid-level: current default

    if n_runners <= 5:
        return "Sieg" if sieg_ok else "Platz"

    if top_prob >= 0.24 and sieg_ok:
        return "Sieg"

    if top_prob >= 0.18 and edge >= 1.18:
        return "Sieg/Platz"

    return "Platz"


def decide_play_status(value: float | None, ranked: list) -> str:
    edge = edge_ratio(ranked)
    if value is None:
        return "OPTIONAL" if edge >= 1.20 else "SKIP"
    if value >= 1.10:
        return "PLAY"
    if value >= 0.95 and edge >= 1.20:
        return "OPTIONAL"
    return "SKIP"


def recommend_bet(ranked_with_v: list, n_runners: int, prize_int: int = 10000):
    """
    Returns (bet_type, horse_names)
    ranked_with_v = [(horse, prob, value_or_none)]
    Always centered on the model top pick.
    """
    if not ranked_with_v:
        return None

    top_horse = ranked_with_v[0][0]
    ranked = [(h, p) for h, p, _ in ranked_with_v]
    bet_type = decide_bet_type(ranked, n_runners, prize_int)

    return bet_type, [top_horse["name"]]


def suggest_exotics(ranked: list, n_runners: int) -> list:
    """
    Returns a list of dictionaries:
    [{type, horses, reason}]
    """
    suggestions = []
    if len(ranked) < 2:
        return suggestions

    top_names = [h["name"] for h, _ in ranked]
    p1 = ranked[0][1]
    p2 = ranked[1][1]
    p3 = ranked[2][1] if len(ranked) >= 3 else 0.0
    p4 = ranked[3][1] if len(ranked) >= 4 else 0.0

    gap12 = p1 - p2
    gap23 = p2 - p3 if len(ranked) >= 3 else 0.0
    gap34 = p3 - p4 if len(ranked) >= 4 else 0.0

    # Platz-Zwilling
    if len(ranked) >= 2 and p1 + p2 >= 0.38:
        suggestions.append({
            "type": "Platz-Zwilling",
            "horses": top_names[:2],
            "reason": "Top 2 wirken gemeinsam am stabilsten"
        })

    # Zweier
    if len(ranked) >= 2 and p1 + p2 >= 0.42 and gap23 >= 0.03:
        suggestions.append({
            "type": "Zweier",
            "horses": top_names[:2],
            "reason": "Top 2 klar vor dem Rest"
        })

    # Dreier
    if len(ranked) >= 3 and n_runners >= 7 and (p1 + p2 + p3) >= 0.58:
        suggestions.append({
            "type": "Dreier",
            "horses": top_names[:3],
            "reason": "Top 3 dominieren das Rennen"
        })

    # Vierer
    if len(ranked) >= 4 and n_runners >= 9 and (p1 + p2 + p3 + p4) >= 0.72:
        suggestions.append({
            "type": "Vierer",
            "horses": top_names[:4],
            "reason": "Top 4 heben sich im großen Feld ab"
        })

    return suggestions


def make_explanation(horse: dict, prob_gap: float, value: float | None,
                     bet_type: str, today_codes: set,
                     field_gag: list = None) -> str:
    """
    One-line rationale: key strengths + bet-type reason.
    field_gag: list of non-zero GAG values for the race (used to detect top-rated).
    """
    reasons = []

    runs = [(g, p) for g, p in parse_form_runs(horse["form"]) if g.upper() != "S"]
    if runs:
        wins3 = sum(1 for _, p in runs[:3] if p == 1)
        if wins3 >= 2:
            reasons.append(f"{wins3} Siege in letzten 3")
        elif runs[0][1] == 1:
            reasons.append("zuletzt gewonnen")
        elif runs[0][1] <= 3:
            reasons.append("gute Vorform")

    if horse["expert_tip"]:
        reasons.append("Experten-Tipp ⭐")
    if horse["distance"] == "good":
        reasons.append("Distanz ✓")
    if ground_compat(horse["form"], today_codes) == "✅":
        reasons.append("Boden ✓")
    if horse["jockey_rate"] >= 20:
        reasons.append(f"Top-Jockey ({horse['jockey_rate']}%)")

    # GAG signal — top-rated horse in the field
    if field_gag and horse["gag"] > 0 and horse["gag"] >= max(field_gag):
        reasons.append("Stärkstes GAG-Rating ⭐")

    # Rennpause signals
    rp = horse.get("rennpause", 150)
    if rp > 300:
        reasons.append(f"Lange Pause ({rp}d) ⚠️")
    elif 0 < rp <= 100:
        reasons.append("Frisch in Form ✅")

    if not reasons:
        reasons.append("Algorithmus-Favorit")

    if bet_type == "Sieg":
        bet_reason = f"klarer Vorteil (Δ {prob_gap*100:.0f}%p)"
    elif bet_type == "Sieg/Platz":
        bet_reason = f"starker Pick, aber etwas offener (Δ {prob_gap*100:.0f}%p)"
    else:
        bet_reason = f"engeres Feld (Δ {prob_gap*100:.0f}%p)"

    if value is not None:
        if value >= 1.25:
            price_reason = "Preis attraktiv"
        elif value >= 1.00:
            price_reason = "Preis fair"
        elif value >= 0.90:
            price_reason = "Preis fast fair"
        else:
            price_reason = "Preis eher tief"
        return ", ".join(reasons) + " — " + bet_reason + " — " + price_reason

    return ", ".join(reasons) + " — " + bet_reason


def price_eval_str(value: float | None) -> str:
    if value is None:
        return "—"
    if value >= 1.25:
        return "🟢 Gute Quote"
    if value >= 1.00:
        return "🟡 Faire Quote"
    if value >= 0.90:
        return "⚪ Fast fair"
    return "🔴 Tiefe Quote"


# ─── HTML helpers ─────────────────────────────────────────────────────────────
def form_html(form_str: str) -> str:
    runs = parse_form_runs(form_str)
    if not runs:
        return '<span style="color:#9ca3af;font-size:0.78rem">Debütant – keine Vorform</span>'

    badges = []
    for ground, pos in runs[:10]:
        is_sand = ground.upper() == "S"
        if is_sand:
            bg, text = "#94a3b8", f"S{pos}"
        elif pos == 0:
            bg, text = "#111827", f"{ground}✗"
        elif pos == 1:
            bg, text = "#16a34a", f"{ground}1"
        elif pos <= 3:
            bg, text = "#ca8a04", f"{ground}{pos}"
        elif pos <= 5:
            bg, text = "#dc2626", f"{ground}{pos}"
        else:
            bg, text = "#6b7280", f"{ground}{pos}"

        badges.append(
            f'<span style="display:inline-block;background:{bg};color:#fff;'
            f'padding:1px 5px;border-radius:3px;font-size:0.68rem;font-weight:700;'
            f'margin:1px;font-family:monospace">{text}</span>'
        )
    return "".join(badges)


def value_html(v: float) -> str:
    if v >= 1.25:
        return f'<span style="color:#16a34a;font-weight:800;font-size:1.05rem">🟢 {v:.2f}×</span>'
    if v >= 1.0:
        return f'<span style="color:#ca8a04;font-weight:800;font-size:1.05rem">🟡 {v:.2f}×</span>'
    return f'<span style="color:#dc2626;font-weight:800;font-size:1.05rem">🔴 {v:.2f}×</span>'


def stake_html(eur: float) -> str:
    if eur > 0:
        return (
            f'<div style="background:#f0fdf4;border:2px solid #16a34a;border-radius:6px;'
            f'padding:5px 8px;text-align:center;font-weight:800;color:#16a34a;font-size:1.1rem">'
            f'€{eur:.0f}</div>'
        )
    return (
        '<div style="background:#f9fafb;border:1.5px solid #d1d5db;border-radius:6px;'
        'padding:5px 8px;text-align:center;color:#9ca3af;font-size:0.85rem">Kein Tipp</div>'
    )


def bet_badge_html(bet_type: str) -> str:
    colors = {
        "Sieg":           "#16a34a",
        "Platz":          "#2563eb",
        "Sieg/Platz":     "#0f766e",
        "Zweier":         "#7c3aed",
        "Dreier":         "#ea580c",
        "Vierer":         "#be123c",
        "Platz-Zwilling": "#0891b2",
    }
    bg = colors.get(bet_type, "#6b7280")
    return (
        f'<span style="display:inline-block;background:{bg};color:#fff;'
        f'padding:2px 10px;border-radius:12px;font-size:0.80rem;font-weight:700">'
        f'{bet_type}</span>'
    )


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    # ── Session state init ────────────────────────────────────────────────────
    if "placed_bets" not in st.session_state:
        st.session_state.placed_bets = {}     # race_label → actual stake (€)
    if "finished_races" not in st.session_state:
        st.session_state.finished_races = set()  # set of race nums (str)

    # ── Load races early (needed for budget calc) ─────────────────────────────
    races_path = Path("races.md")
    if not races_path.exists():
        st.error("`races.md` nicht gefunden.")
        st.stop()
    races = load_races(str(races_path))
    if not races:
        st.error("Keine Rennen in `races.md` gefunden.")
        st.stop()

    n_races = len(races)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⚙️ Einstellungen")
        bankroll = st.number_input(
            "Bankroll (€)", min_value=10.0, max_value=1_000_000.0, value=500.0, step=10.0,
        )
        min_bet = st.number_input(
            "Min. Einsatz pro Wette (€)",
            min_value=0.50, max_value=100.0, value=2.0, step=0.50,
            help="Toto-Minimum: €2.00.",
        )
        st.markdown("**Globaler Bodenzustand**")
        global_ground = st.selectbox("Boden", GROUND_OPTIONS, index=0)
        st.divider()

        # ── Budget overview ───────────────────────────────────────────────────
        placed_total   = sum(st.session_state.placed_bets.values())
        placed_count   = len(st.session_state.placed_bets)
        finished_count = len(st.session_state.finished_races)
        remaining_bankroll = bankroll - placed_total
        remaining_races    = max(n_races - finished_count - placed_count, 1)
        budget_per_race    = remaining_bankroll / remaining_races

        st.markdown("**Bankroll-Übersicht**")
        st.metric("Verbleibend", f"€{remaining_bankroll:.0f}",
                  delta=f"-€{placed_total:.0f}" if placed_total > 0 else None,
                  delta_color="inverse")
        col_bp, col_rr = st.columns(2)
        col_bp.metric("Budget/Rennen", f"€{budget_per_race:.0f}")
        col_rr.metric("Offene Rennen", remaining_races)
        st.divider()

        # Section 6 — Updated weights table
        st.markdown(
            "**Score-Gewichte**\n\n"
            "| Faktor | Gewicht |\n|---|---|\n"
            "| Form (Boden, Recency) | 25% |\n"
            "| GAG-Rating (Handicap) | 20% |\n"
            "| Jockey Winrate | 12% |\n"
            "| Season Stats 2025/26 | 10% |\n"
            "| Distanzpräferenz | 10% |\n"
            "| Rennpause (Fitness) | 8% |\n"
            "| Karriere Winrate | 5% |\n"
            "| Experten-Tipp | 5% |\n"
            "| Boxnummer (Draw) | 5% |\n\n"
            "_Experten-Tipp = zusätzlich ×1.10 Multiplikator_\n\n"
            "_GAG 0 = Debütant (neutral 50%)_\n\n"
            "_Rennpause >365 Tage = starkes Warnsignal_\n\n"
            "_Bayesian Blend: 65% Modell + 35% Markt wenn Quote vorhanden_\n\n"
            "**Einsatz** = Kelly × Rennenbudget (tiered)"
        )

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("# 🐎 Hoppegarten")
    st.markdown(
        '<p style="color:#6b7280;margin-top:-8px;margin-bottom:6px">'
        "Große Saisoneröffnung · 5. April 2026 · Berlin-Hoppegarten</p>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Bankroll", f"€{bankroll:,.0f}")
    c2.metric("Verbleibend", f"€{remaining_bankroll:.0f}")
    c3.metric("Budget/Rennen", f"€{budget_per_race:.0f}")
    st.divider()

    # ── Per-race rendering ────────────────────────────────────────────────────
    wettschein = []

    for race_idx, race in enumerate(races):
        horses = race["horses"]
        prize_int  = race["prize_int"]
        distance_m = _parse_distance_m(race["distance"])

        race_is_finished = race["num"] in st.session_state.finished_races

        expander_label = (
            f"Rennen {race['num']}  ·  {race['distance']}  ·  "
            f"{race['prize']}  ·  {race['runners']}"
        )
        if race["time_conditions"]:
            tc = race["time_conditions"]
            expander_label += f"  ·  {tc}"
        if race_is_finished:
            expander_label = "🏁 " + expander_label

        with st.expander(expander_label, expanded=(race_idx == 0 and not race_is_finished)):
            # Feature 1 — "Rennen vorbei" checkbox
            is_finished = st.checkbox(
                "🏁 Rennen beendet",
                value=race_is_finished,
                key=f"finished_{race['num']}",
            )
            if is_finished:
                st.session_state.finished_races.add(race["num"])
            else:
                st.session_state.finished_races.discard(race["num"])

            if race_is_finished:
                st.markdown(
                    '<div style="background:#f3f4f6;border-radius:6px;padding:5px 12px;'
                    'margin:4px 0 10px;color:#9ca3af;font-size:0.85rem;text-align:center">'
                    '🏁 Rennen abgeschlossen</div>',
                    unsafe_allow_html=True,
                )

            # Notes
            for cat, text in race.get("notes", []):
                if cat == "hinweis":
                    st.warning(f"**Hinweis:** {text}")
                elif cat == "tipp":
                    st.info(f"**Programmtipp:** {text}")
                elif cat == "experte":
                    st.success(f"**Experten-Konsens:** {text}")
                elif cat == "viererwette":
                    st.success(f"**Viererwette:** {text}")
                else:
                    st.caption(text)

            # Per-race ground override
            race_ground_raw = st.selectbox(
                "Boden für dieses Rennen",
                ["(global)"] + GROUND_OPTIONS,
                key=f"ground_r{race_idx}",
            )
            eff_ground = global_ground if race_ground_raw == "(global)" else race_ground_raw
            today_codes = GROUND_CODES[eff_ground]

            # field_gag used in composite scoring and make_explanation
            field_gag = [h["gag"] for h in horses if h["gag"] > 0]

            # Debütant race detection (Section 8)
            if all(h["career_starts"] == 0 for h in horses):
                st.info("⚡ Debütantenrennen — Jockey & Box entscheidend")

            # Compute probabilities
            probs = race_probs(horses, today_codes,
                               n_runners=len(horses), distance_m=distance_m)
            ranked = sorted(zip(horses, probs), key=lambda x: x[1], reverse=True)

            st.markdown(
                f"**Boden:** `{eff_ground}` &nbsp;·&nbsp; {len(horses)} Starter",
                unsafe_allow_html=True,
            )
            st.markdown("")

            # ── Per-horse cards ───────────────────────────────────────────────
            race_values    = {}     # name → value_score (blended/implied)
            race_horse_odds = {}    # name → (odds_f, k_eur, model_prob)

            for rank, (horse, prob) in enumerate(ranked, 1):
                orig_idx = horses.index(horse)
                key_odds = f"odds_r{race_idx}_h{orig_idx}"
                compat   = ground_compat(horse["form"], today_codes)
                tip_icon = " 💡" if horse["expert_tip"] else ""

                with st.container(border=True):
                    left, right = st.columns([5, 2])

                    with left:
                        st.markdown(
                            f'<span style="font-weight:800;color:#2563eb;font-size:1.05rem">#{rank}</span> '
                            f'<span style="font-weight:700;font-size:1.05rem">{horse["name"]}</span>'
                            f'<span style="font-size:0.90rem"> {compat}{tip_icon}</span>',
                            unsafe_allow_html=True,
                        )
                        st.caption(
                            f"🏇 {horse['jockey']} ({horse['jockey_rate']}%)  ·  "
                            f"🎓 {horse['trainer']}  ·  "
                            f"{horse['age']}J  ·  {horse['weight']}kg  ·  "
                            f"{'⭐' if horse['expert_tip'] else ''}"
                            f"Karriere {horse['career_starts']}/{horse['career_wins']}"
                        )
                        st.markdown(form_html(horse["form"]), unsafe_allow_html=True)

                        # Section 7 — GAG / Rennpause info line
                        gag_str = f"GAG: {horse['gag']:.1f}" if horse["gag"] > 0 else "GAG: –"
                        rp = horse["rennpause"]
                        if rp == 0:
                            rp_str = "Pause: Debütant"
                        elif rp > 365:
                            rp_str = f"Pause: {rp} Tage 🔴"
                        elif rp > 200:
                            rp_str = f"Pause: {rp} Tage ⚠️"
                        else:
                            rp_str = f"Pause: {rp} Tage ✅"
                        st.caption(f"{gag_str}  |  {rp_str}")

                    with right:
                        st.metric("Est. Prob", f"{prob*100:.1f}%")
                        dist_icon = {"good": "✅", "neutral": "〰️", "bad": "❌"}.get(
                            horse["distance"], "〰️"
                        )
                        st.caption(f"Distanz {dist_icon}")

                    # Score breakdown — 9-factor 3×3 grid
                    with st.expander("Score-Details", expanded=False):
                        b1, b2, b3 = st.columns(3)
                        b1.metric("Form", f"{score_form(horse['form'], today_codes)*100:.0f}")
                        b2.metric("GAG", f"{score_gag(horse['gag'], field_gag)*100:.0f}")
                        b3.metric("Jockey", f"{score_jockey(horse['jockey_rate'])*100:.0f}")
                        b4, b5, b6 = st.columns(3)
                        b4.metric("Season", f"{score_season(horse['season_starts'], horse['season_wins'], horse['season_placed'])*100:.0f}")
                        b5.metric("Distanz", f"{score_distance(horse['distance'])*100:.0f}")
                        b6.metric("Rennpause", f"{score_rennpause(horse['rennpause'])*100:.0f}")
                        b7, b8, b9 = st.columns(3)
                        b7.metric("Karriere", f"{score_career(horse['career_starts'], horse['career_wins'])*100:.0f}")
                        b8.metric("Experte", "✅" if horse["expert_tip"] else "—")
                        b9.metric("Box", f"{score_box(horse['box'], len(horses), distance_m)*100:.0f}")

                    # Odds input
                    odds_val = st.number_input(
                        "Live-Quote (dezimal)",
                        min_value=1.01, max_value=500.0,
                        value=None, step=0.05,
                        placeholder="z.B. 4.50 — Quote eingeben…",
                        key=key_odds, format="%.2f",
                    )

                    # Section 6 — Bayesian blend output
                    if odds_val and odds_val > 1.01:
                        implied    = 1.0 / odds_val
                        blended    = blend_prob(prob, odds_val)
                        val        = blended / implied
                        race_values[horse["name"]] = val
                        k_pct, k_eur = kelly(blended, odds_val, bankroll)
                        race_horse_odds[horse["name"]] = (odds_val, k_eur, prob)
                        if k_eur < min_bet:
                            k_pct, k_eur = 0.0, 0.0

                        r1, r2, r3 = st.columns([3, 2, 2])
                        with r1:
                            st.markdown(value_html(val), unsafe_allow_html=True)
                            st.caption(
                                f"Est {prob*100:.1f}% (Modell) → {blended*100:.1f}% (Blend)"
                                f" vs Implied {implied*100:.1f}%"
                            )
                        with r2:
                            st.markdown(f"**Kelly:** {k_pct:.1f}%")
                        with r3:
                            st.markdown(stake_html(k_eur), unsafe_allow_html=True)
                    else:
                        st.caption("_Quote eingeben für Value & Einsatz_")

                st.markdown("")

            # ── Bet recommendation display ────────────────────────────────────
            ranked_with_v = [(h, p, race_values.get(h["name"])) for h, p in ranked]
            bet = recommend_bet(ranked_with_v, len(horses), prize_int)

            top_horse = ranked[0][0]
            top_prob  = ranked[0][1]
            pgap      = prob_gap(ranked)

            if bet:
                bet_type_rec, bet_horses_rec = bet
            else:
                bet_type_rec, bet_horses_rec = "Platz", [top_horse["name"]]

            top_odds  = race_horse_odds.get(top_horse["name"])
            top_value = race_values.get(top_horse["name"])
            play_status = decide_play_status(top_value, ranked)

            play_color = {
                "PLAY": "#16a34a",
                "OPTIONAL": "#ca8a04",
                "SKIP": "#dc2626",
            }.get(play_status, "#6b7280")

            st.markdown(
                f"**Empfehlung:** {bet_badge_html(bet_type_rec)} &nbsp; "
                + " + ".join(f"**{n}**" for n in bet_horses_rec)
                + f' &nbsp; <span style="color:{play_color};font-weight:700">{play_status}</span>',
                unsafe_allow_html=True,
            )

            extra_bets = suggest_exotics(ranked, len(horses))
            if extra_bets:
                st.markdown("**Weitere Wettarten:**")
                for eb in extra_bets:
                    horses_txt = " + ".join(f"**{n}**" for n in eb["horses"])
                    st.markdown(
    f"{bet_badge_html(eb['type'])} &nbsp; {horses_txt}  \n"
    f"<span style='color:#6b7280;font-size:0.84rem'>{eb['reason']}</span>",
    unsafe_allow_html=True,
)

            # ── Collect for Wettschein (fully recomputed every run) ───────────
            race_time = (
                race["time_conditions"].split("—")[-1].strip()
                if "—" in race.get("time_conditions", "") else ""
            )
            race_label    = f"R{race['num']}"
            bet_type_final = decide_bet_type(ranked, len(horses), prize_int)

            if top_odds:
                ph_odds_f, raw_k_eur, _ = top_odds
                ph_val = top_value

                blended_p = blend_prob(top_prob, ph_odds_f)
                kf    = full_kelly_frac(blended_p, ph_odds_f)
                tier  = value_tier(ph_val)
                stake = budget_stake(kf, budget_per_race, tier, min_bet)

                explanation = make_explanation(top_horse, pgap, ph_val, bet_type_final, today_codes, field_gag)
                price       = price_eval_str(ph_val)

                st.session_state[f"stake_{race_label}"] = stake

                wettschein.append(dict(
                    race_label=race_label, time=race_time,
                    horse=top_horse["name"], bet_type=bet_type_final,
                    odds=ph_odds_f, value=ph_val, tier=tier,
                    stake=stake, explanation=explanation, price=price,
                    play_status=play_status,
                    extra_bets=extra_bets,
                    has_odds=True,
                    model_prob=top_prob,
                    blended_prob=blended_p,
                    implied_prob=1.0 / ph_odds_f,
                    prob_map={h["name"]: p for h, p in ranked},
                ))
            else:
                explanation = make_explanation(top_horse, pgap, None, bet_type_final, today_codes, field_gag)

                # Estimated stake (no odds) — NOT counted toward bankroll
                er = edge_ratio(ranked)
                if er >= 1.35:
                    est_stake = round(0.60 * budget_per_race, 2)
                elif er >= 1.20:
                    est_stake = round(0.40 * budget_per_race, 2)
                else:
                    est_stake = round(0.20 * budget_per_race, 2)
                est_stake = max(est_stake, min_bet)

                wettschein.append(dict(
                    race_label=race_label, time=race_time,
                    horse=top_horse["name"], bet_type=bet_type_final,
                    odds=None, value=None, tier=None,
                    stake=None, explanation=explanation, price="—",
                    play_status=play_status,
                    extra_bets=extra_bets,
                    has_odds=False,
                    model_prob=top_prob,
                    blended_prob=None,
                    implied_prob=None,
                    estimated_stake=est_stake,
                    prob_map={h["name"]: p for h, p in ranked},
                ))

    # ─── Mein Wettschein ──────────────────────────────────────────────────────
    st.divider()
    st.markdown("## 🎫 Mein Wettschein")

    rows_with_odds = [r for r in wettschein if r["has_odds"]]
    # estimated stakes are intentionally excluded from total_planned
    total_planned  = sum(r["stake"] for r in rows_with_odds if r["stake"])

    _tier_colors = {"strong": "#16a34a", "medium": "#ca8a04",
                    "neutral": "#6b7280", "weak": "#dc2626"}
    _tier_icons  = {"strong": "🟢", "medium": "🟡", "neutral": "⚪", "weak": "🔴"}
    _play_colors = {"PLAY": "#16a34a", "OPTIONAL": "#ca8a04", "SKIP": "#dc2626"}

    for row in wettschein:
        time_str   = f" · {row['time']}" if row["time"] else ""
        label      = f"**{row['race_label']}**{time_str}"
        play_status = row.get("play_status", "—")
        play_col   = _play_colors.get(play_status, "#6b7280")

        with st.container(border=True):

            # ── PART 1: Hauptwette ─────────────────────────────────────────
            c_l, c_r = st.columns([5, 2])

            with c_l:
                # Race header line
                st.markdown(
                    f"{label} &nbsp;"
                    f'<span style="font-size:0.78rem;font-weight:700;color:{play_col}">'
                    f"{play_status}</span>",
                    unsafe_allow_html=True,
                )

                if row["has_odds"]:
                    col  = _tier_colors.get(row["tier"], "#6b7280")
                    icon = _tier_icons.get(row["tier"], "⚪")
                    st.markdown(
                        f"🐴 **{row['horse']}** &nbsp; {bet_badge_html(row['bet_type'])} &nbsp;"
                        f'<span style="font-size:0.80rem;color:#6b7280">@{row["odds"]:.2f}</span>',
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        f"🎯 {row['model_prob']*100:.1f}% Modell-Chance"
                        f" → {row['blended_prob']*100:.1f}% Blend"
                        f" vs {row['implied_prob']*100:.1f}% Implied"
                    )
                    st.markdown(
                        f'<span style="font-size:0.82rem;color:{col}">{icon} {row["price"]}</span>'
                        f' &nbsp; <span style="font-size:0.82rem;color:#6b7280">'
                        f'· {row["explanation"]}</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    est_stake = row.get("estimated_stake", 0)
                    st.markdown(
                        f"🐴 {row['horse']} &nbsp; {bet_badge_html(row['bet_type'])}",
                        unsafe_allow_html=True,
                    )
                    st.caption(f"🎯 {row['model_prob']*100:.1f}% Modell-Chance")
                    st.markdown(
                        f'<span style="font-size:0.82rem;color:#9ca3af">'
                        f"~€{est_stake:.0f} (Schätzung, keine Quote) · {row['explanation']}"
                        f"</span>",
                        unsafe_allow_html=True,
                    )

            with c_r:
                if row["has_odds"]:
                    col       = _tier_colors.get(row["tier"], "#6b7280")
                    stake_str = f"€{row['stake']:.0f}" if row["stake"] else f"€{min_bet:.0f} min"
                    st.markdown(
                        f'<div style="text-align:right;font-size:1.5rem;font-weight:800;'
                        f'color:{col};padding-top:4px">{stake_str}</div>',
                        unsafe_allow_html=True,
                    )
                    # Feature 2 — Gewettet checkbox + actual stake input
                    placed_key = f"bet_placed_{row['race_label']}"
                    was_placed = st.session_state.placed_bets.get(row["race_label"]) is not None
                    is_placed  = st.checkbox("Gewettet", key=placed_key, value=was_placed)
                    if is_placed:
                        amount_key = f"bet_amount_{row['race_label']}"
                        if amount_key not in st.session_state:
                            # Initialise with algo-recommended stake on first check
                            st.session_state[amount_key] = float(row["stake"] or min_bet)
                        actual_amount = st.number_input(
                            "Einsatz (€)",
                            min_value=0.50,
                            step=0.50,
                            key=amount_key,
                            label_visibility="collapsed",
                        )
                        st.session_state.placed_bets[row["race_label"]] = actual_amount
                    elif row["race_label"] in st.session_state.placed_bets:
                        del st.session_state.placed_bets[row["race_label"]]
                else:
                    est_stake = row.get("estimated_stake", 0)
                    st.markdown(
                        f'<div style="text-align:right;font-size:1.4rem;font-weight:700;'
                        f'color:#9ca3af;padding-top:4px">~€{est_stake:.0f}</div>'
                        f'<div style="text-align:right;font-size:0.72rem;color:#9ca3af">'
                        f'Schätzung</div>',
                        unsafe_allow_html=True,
                    )

            # ── PART 2: Kombi-Potenzial ────────────────────────────────────
            extra_bets = row.get("extra_bets", [])
            if extra_bets:
                top_kombi    = extra_bets[0]
                prob_map     = row.get("prob_map", {})
                combined_p   = sum(prob_map.get(h, 0) for h in top_kombi["horses"])
                horses_str   = " + ".join(top_kombi["horses"])
                st.markdown(
                    f'<div style="border-top:1px solid #e5e7eb;margin-top:8px;'
                    f'padding-top:6px;font-size:0.84rem;color:#6b7280">'
                    f'💡 <strong>Kombi-Idee:</strong> &nbsp;'
                    f'{bet_badge_html(top_kombi["type"])} &nbsp;'
                    f'{horses_str} &nbsp;'
                    f'<span style="color:#9ca3af">~{combined_p*100:.0f}% kombiniert</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Totals ────────────────────────────────────────────────────────────────
    st.markdown("")
    differenz = total_planned - placed_total
    tc1, tc2, tc3, tc4, tc5 = st.columns(5)
    tc1.metric("Rennen", n_races)
    tc2.metric("Mit Quote", len(rows_with_odds))
    tc3.metric("Geplant", f"€{total_planned:.0f}" if total_planned else "—")
    tc4.metric("Gesetzt", f"€{placed_total:.0f}" if placed_total else "—")
    tc5.metric(
        "Differenz",
        f"€{differenz:+.0f}" if (total_planned or placed_total) else "—",
    )

    st.divider()
    st.caption(
        "Modellschätzungen — keine Finanzberatung. Bitte verantwortungsvoll wetten.  \n"
        "Hoppegarten Racing Tool · April 2026"
    )


if __name__ == "__main__":
    main()
