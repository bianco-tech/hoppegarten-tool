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
            career_starts, career_wins = 0, 0
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
                elif line.startswith("Form:"):
                    form_str = line[5:].strip()
                elif line.startswith("DistancePref:"):
                    dist_affinity = line[13:].strip().lower()
                elif line.startswith("ExpertTip:"):
                    expert_tip = line[10:].strip().lower() == "yes"

            horses.append(dict(
                name=name, jockey=jockey, jockey_rate=jockey_rate, trainer=trainer,
                weight=weight, age=age, career_starts=career_starts,
                career_wins=career_wins, form=form_str,
                distance=dist_affinity, expert_tip=expert_tip,
            ))

        if horses:
            races.append(dict(
                num=race_num, distance=distance, prize=prize,
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


def composite(horse: dict, field_kg: list, today_codes: set) -> float:
    f = score_form(horse["form"], today_codes)
    j = score_jockey(horse["jockey_rate"])
    d = score_distance(horse["distance"])
    c = score_career(horse["career_starts"], horse["career_wins"])
    w = score_weight(horse["weight"], field_kg)
    e = 1.0 if horse["expert_tip"] else 0.0
    a = score_age(horse["age"])

    raw = (0.40 * f + 0.20 * j + 0.15 * d +
           0.10 * c + 0.05 * w + 0.05 * e + 0.05 * a)

    return raw * 1.10 if horse["expert_tip"] else raw


def race_probs(horses: list, today_codes: set) -> list:
    field_kg = [h["weight"] for h in horses]
    scores = [composite(h, field_kg, today_codes) for h in horses]
    total = sum(scores) or 1.0
    return [s / total for s in scores]


# ─── Kelly ────────────────────────────────────────────────────────────────────
def kelly(est_prob: float, decimal_odds: float, bankroll: float) -> tuple:
    """Half-Kelly, capped at 25%. Returns (pct, eur)."""
    if decimal_odds <= 1.0 or est_prob <= 0:
        return 0.0, 0.0
    b = decimal_odds - 1.0
    k = (b * est_prob - (1.0 - est_prob)) / b
    if k <= 0:
        return 0.0, 0.0
    k = min(k * 0.5, 0.25)
    return round(k * 100, 1), round(k * bankroll, 2)


# ─── Bet type recommender ─────────────────────────────────────────────────────
def recommend_bet(
    ranked: list,  # list of (horse, prob, value_or_None)
    n_runners: int,
) -> tuple:  # (bet_type, horse_names) or None
    """Pick best bet type given available value scores. Returns (type, names) or None."""
    with_v = [(h, p, v) for h, p, v in ranked if v is not None]
    if not with_v:
        return None

    h1, p1, v1 = with_v[0]
    h2, p2, v2 = (with_v[1][0], with_v[1][1], with_v[1][2]) if len(with_v) >= 2 else (None, 0.0, 0.0)
    h3, p3, v3 = (with_v[2][0], with_v[2][1], with_v[2][2]) if len(with_v) >= 3 else (None, 0.0, 0.0)

    gap12 = p1 - p2

    if v1 > 1.30 and gap12 > 0.05:
        return ("Sieg", [h1["name"]])
    if h2 and v1 > 1.10 and v2 > 1.10:
        return ("Zweier", [h1["name"], h2["name"]])
    if n_runners >= 8 and h3 and v1 > 1.0 and v2 > 1.0 and v3 > 1.0 and gap12 > 0.02 and (p2 - p3) > 0.02:
        return ("Dreier", [h1["name"], h2["name"], h3["name"]])
    if v1 >= 1.0:
        return ("Platz", [h1["name"]])
    if h2 and v1 >= 0.90 and v2 >= 0.90:
        return ("Platz-Zwilling", [h1["name"], h2["name"]])
    return None


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
        "Sieg":          "#16a34a",
        "Platz":         "#2563eb",
        "Zweier":        "#7c3aed",
        "Dreier":        "#ea580c",
        "Platz-Zwilling":"#0891b2",
    }
    bg = colors.get(bet_type, "#6b7280")
    return (
        f'<span style="display:inline-block;background:{bg};color:#fff;'
        f'padding:2px 10px;border-radius:12px;font-size:0.80rem;font-weight:700">'
        f'{bet_type}</span>'
    )


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⚙️ Einstellungen")
        bankroll = st.number_input(
            "Bankroll (€)", min_value=10.0, max_value=1_000_000.0, value=500.0, step=10.0,
        )
        min_bet = st.number_input(
            "Min. Einsatz pro Wette (€)",
            min_value=0.50, max_value=100.0, value=2.0, step=0.50,
            help="Toto-Minimum: €2.00. Kelly-Empfehlungen unter diesem Betrag werden auf 0 gesetzt.",
        )
        st.markdown("**Globaler Bodenzustand**")
        global_ground = st.selectbox("Boden", GROUND_OPTIONS, index=0)
        st.divider()
        st.markdown(
            "**Score-Gewichte**\n\n"
            "| | |\n|---|---|\n"
            "| Form (Boden) | 40% |\n"
            "| Jockey | 20% |\n"
            "| Distanzpräferenz | 15% |\n"
            "| Karriere WR | 10% |\n"
            "| Gewicht | 5% |\n"
            "| Experten-Tipp | 5% |\n"
            "| Alter | 5% |\n\n"
            "_Experten-Tipp = zusätzlich ×1.10_\n\n"
            "**Value** = Est. Prob ÷ (1/Quote)\n\n"
            "**Einsatz** = Half-Kelly × Bankroll, max 25%"
        )

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("# 🐎 Hoppegarten")
    st.markdown(
        '<p style="color:#6b7280;margin-top:-8px;margin-bottom:6px">'
        "Große Saisoneröffnung · 5. April 2026 · Berlin-Hoppegarten</p>",
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    c1.metric("Bankroll", f"€{bankroll:,.0f}")
    c2.metric("Boden", global_ground)
    st.divider()

    # ── Load ──────────────────────────────────────────────────────────────────
    races_path = Path("races.md")
    if not races_path.exists():
        st.error("`races.md` nicht gefunden.")
        st.stop()

    with st.spinner("Rennen laden…"):
        races = load_races(str(races_path))

    if not races:
        st.error("Keine Rennen in `races.md` gefunden.")
        st.stop()

    # ── Per-race rendering ────────────────────────────────────────────────────
    wettschein = []

    for race_idx, race in enumerate(races):
        horses = race["horses"]
        expander_label = (
            f"Rennen {race['num']}  ·  {race['distance']}  ·  "
            f"{race['prize']}  ·  {race['runners']}"
        )
        if race["time_conditions"]:
            tc = race["time_conditions"]
            expander_label += f"  ·  {tc}"

        with st.expander(expander_label, expanded=(race_idx == 0)):
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

            # Compute probabilities
            probs = race_probs(horses, today_codes)
            ranked = sorted(zip(horses, probs), key=lambda x: x[1], reverse=True)

            st.markdown(
                f"**Boden:** `{eff_ground}` &nbsp;·&nbsp; {len(horses)} Starter",
                unsafe_allow_html=True,
            )
            st.markdown("")

            # ── Per-horse cards ───────────────────────────────────────────
            race_values = {}

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

                    with right:
                        st.metric("Est. Prob", f"{prob*100:.1f}%")
                        dist_icon = {"good": "✅", "neutral": "〰️", "bad": "❌"}.get(
                            horse["distance"], "〰️"
                        )
                        st.caption(f"Distanz {dist_icon}")

                    # Score breakdown
                    with st.expander("Score-Details", expanded=False):
                        fkg = [h["weight"] for h in horses]
                        b1, b2, b3, b4 = st.columns(4)
                        b1.metric("Form", f"{score_form(horse['form'], today_codes)*100:.0f}")
                        b2.metric("Jockey", f"{score_jockey(horse['jockey_rate'])*100:.0f}")
                        b3.metric("Distanz", f"{score_distance(horse['distance'])*100:.0f}")
                        b4.metric("Karriere", f"{score_career(horse['career_starts'], horse['career_wins'])*100:.0f}")
                        b5, b6, b7, _ = st.columns(4)
                        b5.metric("Gewicht", f"{score_weight(horse['weight'], fkg)*100:.0f}")
                        b6.metric("Alter", f"{score_age(horse['age'])*100:.0f}")
                        b7.metric("Experte", "✅" if horse["expert_tip"] else "—")

                    # Odds input
                    odds_val = st.number_input(
                        "Live-Quote (dezimal)",
                        min_value=1.01, max_value=500.0,
                        value=None, step=0.05,
                        placeholder="z.B. 4.50 — Quote eingeben…",
                        key=key_odds, format="%.2f",
                    )

                    # Output
                    if odds_val and odds_val > 1.01:
                        implied = 1.0 / odds_val
                        val     = prob / implied
                        race_values[horse["name"]] = val
                        k_pct, k_eur = kelly(prob, odds_val, bankroll)
                        if k_eur < min_bet:
                            k_pct, k_eur = 0.0, 0.0

                        r1, r2, r3 = st.columns([3, 2, 2])
                        with r1:
                            st.markdown(value_html(val), unsafe_allow_html=True)
                            st.caption(f"Est {prob*100:.1f}% vs Implied {implied*100:.1f}%")
                        with r2:
                            st.markdown(f"**Kelly:** {k_pct:.1f}%")
                        with r3:
                            st.markdown(stake_html(k_eur), unsafe_allow_html=True)
                    else:
                        st.caption("_Quote eingeben für Value & Einsatz_")

                st.markdown("")

            # ── Bet recommendation for this race ─────────────────────────
            ranked_with_v = [(h, p, race_values.get(h["name"])) for h, p in ranked]
            bet = recommend_bet(ranked_with_v, len(horses))

            if bet:
                bet_type, bet_horses = bet
                st.markdown(
                    f"**Empfehlung:** {bet_badge_html(bet_type)} &nbsp; "
                    + " + ".join(f"**{n}**" for n in bet_horses),
                    unsafe_allow_html=True,
                )
                # Collect for Wettschein
                primary_horse_name = bet_horses[0]
                ph = next((h for h in horses if h["name"] == primary_horse_name), None)
                if ph:
                    ph_orig_idx = horses.index(ph)
                    ph_odds = st.session_state.get(f"odds_r{race_idx}_h{ph_orig_idx}")
                    ph_prob = next(p for h, p in ranked if h["name"] == primary_horse_name)
                    if ph_odds and float(ph_odds) > 1.01:
                        ph_val = ph_prob / (1.0 / float(ph_odds))
                        _, k_eur = kelly(ph_prob, float(ph_odds), bankroll)
                        if k_eur < min_bet:
                            k_eur = 0.0
                        wettschein.append(dict(
                            race_label=f"R{race['num']}",
                            time=race["time_conditions"].split("—")[-1].strip() if "—" in race.get("time_conditions", "") else "",
                            bet_type=bet_type,
                            horses=bet_horses,
                            odds=float(ph_odds),
                            value=ph_val,
                            stake=k_eur,
                        ))

    # ─── Mein Wettschein ──────────────────────────────────────────────────────
    st.divider()
    st.markdown("## 🎫 Mein Wettschein")

    if not wettschein:
        st.info(
            "Noch keine auswertbaren Quoten eingegeben.  \n"
            "Sobald du Quoten einträgst und Value ≥ 1.0 erreicht wird, erscheinen die Bets hier."
        )
    else:
        total_stake = sum(r["stake"] for r in wettschein)
        total_races = len(wettschein)

        for row in wettschein:
            time_str = f" · {row['time']}" if row["time"] else ""
            horses_str = " + ".join(row["horses"])
            val_color = "#16a34a" if row["value"] >= 1.25 else ("#ca8a04" if row["value"] >= 1.0 else "#dc2626")

            st.markdown(
                f'<div class="schein-row schein-row-value">'
                f'<span style="font-weight:700;min-width:60px">{row["race_label"]}{time_str}</span>'
                f'&nbsp;{bet_badge_html(row["bet_type"])}&nbsp;'
                f'<span style="flex:1">{horses_str}</span>'
                f'<span style="color:#6b7280">@{row["odds"]:.2f}</span>'
                f'<span style="color:{val_color};font-weight:700">{row["value"]:.2f}×</span>'
                f'<span style="font-weight:800;color:#16a34a;min-width:50px;text-align:right">€{row["stake"]:.0f}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Totals
        st.markdown("")
        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("Wetten", total_races)
        tc2.metric("Gesamteinsatz", f"€{total_stake:.0f}")
        tc3.metric("Bankroll-Anteil", f"{total_stake/bankroll*100:.1f}%")

    st.divider()
    st.caption(
        "Modellschätzungen — keine Finanzberatung. Bitte verantwortungsvoll wetten.  \n"
        "Hoppegarten Racing Tool · April 2026"
    )


if __name__ == "__main__":
    main()
