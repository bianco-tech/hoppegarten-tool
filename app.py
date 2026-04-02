import streamlit as st
import re
import math
from pathlib import Path

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hoppegarten · Apr 5",
    page_icon="🐎",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Hide Streamlit chrome */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Mobile-first container */
.block-container {
    padding: 1rem 1rem 3rem 1rem !important;
    max-width: 720px !important;
}

/* Form result badges */
.form-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 700;
    margin: 2px 1px;
    letter-spacing: 0.04em;
}
.form-W { background: #198754; color: #fff; }
.form-P { background: #ffc107; color: #212529; }
.form-L { background: #dc3545; color: #fff; }

/* Score pill */
.score-pill {
    display: inline-block;
    background: #0d6efd;
    color: #fff;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
}

/* Value badges */
.val-green  { color: #198754; font-weight: 700; font-size: 1.05rem; }
.val-yellow { color: #e09800; font-weight: 700; font-size: 1.05rem; }
.val-red    { color: #dc3545; font-weight: 700; font-size: 1.05rem; }

/* Stake highlight */
.stake-box {
    background: #f8f9fa;
    border: 1.5px solid #198754;
    border-radius: 6px;
    padding: 6px 10px;
    text-align: center;
    font-size: 1.1rem;
    font-weight: 700;
    color: #198754;
}
.stake-none {
    background: #f8f9fa;
    border: 1.5px solid #adb5bd;
    border-radius: 6px;
    padding: 6px 10px;
    text-align: center;
    font-size: 0.9rem;
    color: #6c757d;
}

/* Race header divider */
.race-meta {
    font-size: 0.85rem;
    color: #6c757d;
    margin-bottom: 4px;
}

/* Horse rank number */
.rank-num {
    font-size: 1.1rem;
    font-weight: 800;
    color: #0d6efd;
    min-width: 22px;
    display: inline-block;
}

/* Sidebar */
[data-testid="stSidebar"] {
    min-width: 240px;
}
</style>
""", unsafe_allow_html=True)

# ─── Parsing ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_races(path: str) -> list[dict]:
    """Parse races.md into a list of race dicts."""
    content = Path(path).read_text(encoding="utf-8")

    races: list[dict] = []
    # Split on level-1 headings that start a race
    race_blocks = re.split(r"(?m)^# Race\s+", content)

    for block in race_blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        header_parts = [p.strip() for p in lines[0].split("|")]

        race_num      = header_parts[0].strip()
        distance      = header_parts[1] if len(header_parts) > 1 else ""
        prize         = header_parts[2] if len(header_parts) > 2 else ""
        runners_str   = header_parts[3] if len(header_parts) > 3 else ""
        conditions    = header_parts[4] if len(header_parts) > 4 else ""

        rest = "\n".join(lines[1:])
        horse_blocks = re.split(r"(?m)^## ", rest)

        horses: list[dict] = []
        for hblock in horse_blocks:
            hblock = hblock.strip()
            if not hblock:
                continue
            hlines = hblock.split("\n")
            name = hlines[0].strip()
            if not name:
                continue

            jockey = ""
            jockey_rate = 12      # default win rate %
            trainer = ""
            form_str = "L,L,L,L,L"
            dist_affinity = "neutral"

            for line in hlines[1:]:
                line = line.strip()
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
                elif line.startswith("Form:"):
                    form_str = line[5:].strip()
                elif line.startswith("Distance:"):
                    dist_affinity = line[9:].strip().lower()

            horses.append(
                dict(
                    name=name,
                    jockey=jockey,
                    jockey_rate=jockey_rate,
                    trainer=trainer,
                    form=form_str,
                    distance=dist_affinity,
                )
            )

        if horses:
            races.append(
                dict(
                    num=race_num,
                    distance=distance,
                    prize=prize,
                    runners=runners_str,
                    conditions=conditions,
                    horses=horses,
                )
            )

    return races


# ─── Scoring ──────────────────────────────────────────────────────────────────
_FORM_POINTS = {"W": 3, "P": 2, "L": 0}
_RECENCY_WEIGHTS = [1.0, 0.85, 0.70, 0.55, 0.40]
_MAX_FORM = sum(3 * w for w in _RECENCY_WEIGHTS)   # 12.0

_DIST_SCORE = {"good": 1.0, "neutral": 0.5, "bad": 0.0}
_MAX_JOCKEY_RATE = 30   # cap for normalisation


def score_form(form_str: str) -> float:
    """Return a normalised [0,1] form score, most recent result first."""
    results = [r.strip().upper() for r in form_str.split(",")]
    total = 0.0
    max_possible = 0.0
    for i, result in enumerate(results[:5]):
        w = _RECENCY_WEIGHTS[i]
        total += _FORM_POINTS.get(result, 0) * w
        max_possible += 3 * w
    return total / max_possible if max_possible > 0 else 0.0


def score_distance(affinity: str) -> float:
    return _DIST_SCORE.get(affinity.lower(), 0.5)


def score_jockey(rate: int) -> float:
    return min(rate, _MAX_JOCKEY_RATE) / _MAX_JOCKEY_RATE


def composite_score(horse: dict) -> float:
    """Weighted composite of form (50%), distance (30%), jockey (20%)."""
    f = score_form(horse["form"])
    d = score_distance(horse["distance"])
    j = score_jockey(horse["jockey_rate"])
    return 0.50 * f + 0.30 * d + 0.20 * j


def race_probabilities(horses: list[dict]) -> list[float]:
    """Proportional probability estimates from composite scores."""
    scores = [composite_score(h) for h in horses]
    total = sum(scores) or 1.0
    return [s / total for s in scores]


def kelly_stake(
    est_prob: float,
    decimal_odds: float,
    bankroll: float,
    half_kelly: bool = True,
    max_fraction: float = 0.25,
) -> tuple[float, float]:
    """
    Return (kelly_pct, stake_eur).
    Uses half-Kelly by default; caps at max_fraction of bankroll.
    """
    if decimal_odds <= 1.0 or est_prob <= 0:
        return 0.0, 0.0
    b = decimal_odds - 1.0
    q = 1.0 - est_prob
    k = (b * est_prob - q) / b
    if k <= 0:
        return 0.0, 0.0
    if half_kelly:
        k *= 0.5
    k = min(k, max_fraction)
    return round(k * 100, 1), round(k * bankroll, 2)


# ─── HTML helpers ─────────────────────────────────────────────────────────────
def form_badges_html(form_str: str) -> str:
    badges = []
    for result in form_str.split(","):
        r = result.strip().upper()
        css_class = f"form-{r}" if r in ("W", "P", "L") else "form-L"
        badges.append(f'<span class="form-badge {css_class}">{r}</span>')
    return " ".join(badges)


def value_html(value: float) -> str:
    if value >= 1.20:
        label = f"🟢 VALUE  {value:.2f}×"
        css = "val-green"
    elif value >= 1.0:
        label = f"🟡 FAIR  {value:.2f}×"
        css = "val-yellow"
    else:
        label = f"🔴 POOR  {value:.2f}×"
        css = "val-red"
    return f'<span class="{css}">{label}</span>'


def stake_html(k_eur: float) -> str:
    if k_eur > 0:
        return f'<div class="stake-box">Stake: €{k_eur:.0f}</div>'
    return '<div class="stake-none">No bet</div>'


# ─── Main UI ──────────────────────────────────────────────────────────────────
def main() -> None:
    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⚙️ Settings")
        bankroll = st.number_input(
            "Total Bankroll (€)",
            min_value=10.0,
            max_value=1_000_000.0,
            value=500.0,
            step=50.0,
            help="Your total betting bankroll. Kelly stakes are calculated from this.",
        )
        st.markdown("---")
        st.markdown(
            "**How scores work**\n\n"
            "- **Form 50%** — last 5 results, recency-weighted\n"
            "- **Distance 30%** — good / neutral / bad\n"
            "- **Jockey 20%** — win rate\n\n"
            "**Value** = estimated prob ÷ implied prob\n\n"
            "**Stake** = half-Kelly × bankroll (max 25 %)\n\n"
            "---\n"
            "_Edit `races.md` to update race data._"
        )

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("# 🐎 Hoppegarten")
    st.markdown(
        '<p class="race-meta">Race Day · April 5, 2026 · Berlin-Hoppegarten</p>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**Bankroll:** €{bankroll:,.0f}  |  *Half-Kelly, max 25 % per bet*")
    st.divider()

    # ── Load races ────────────────────────────────────────────────────────────
    races_path = Path("races.md")
    if not races_path.exists():
        st.error(
            "`races.md` not found in the project root.  \n"
            "Create it using the template format shown in the README."
        )
        st.stop()

    with st.spinner("Loading races…"):
        races = load_races(str(races_path))

    if not races:
        st.error("No races parsed from `races.md`. Check the file format.")
        st.stop()

    # ── Per-race sections ─────────────────────────────────────────────────────
    for race_idx, race in enumerate(races):
        horses = race["horses"]
        probs  = race_probabilities(horses)

        # Sort horses by estimated probability (highest first)
        ranked = sorted(zip(horses, probs), key=lambda x: x[1], reverse=True)

        label = (
            f"Race {race['num']}  ·  {race['distance']}  ·  "
            f"{race['prize']}  ·  {race['runners']}"
        )
        with st.expander(label, expanded=(race_idx == 0)):
            if race["conditions"]:
                st.markdown(
                    f'<p class="race-meta">{race["conditions"]}</p>',
                    unsafe_allow_html=True,
                )

            for rank, (horse, prob) in enumerate(ranked, start=1):
                # Stable index for session_state keys (use original horse idx)
                orig_idx = horses.index(horse)
                key_odds = f"odds_r{race_idx}_h{orig_idx}"

                with st.container(border=True):
                    # ── Horse header row ──
                    left, right = st.columns([5, 2])

                    with left:
                        dist_icon = {
                            "good":    "✅",
                            "neutral": "〰️",
                            "bad":     "❌",
                        }.get(horse["distance"], "〰️")
                        st.markdown(
                            f'<span class="rank-num">#{rank}</span> '
                            f"**{horse['name']}** {dist_icon}",
                            unsafe_allow_html=True,
                        )
                        st.caption(
                            f"🏇 {horse['jockey']} ({horse['jockey_rate']}%)  ·  "
                            f"🎓 {horse['trainer']}"
                        )
                        st.markdown(
                            form_badges_html(horse["form"]),
                            unsafe_allow_html=True,
                        )

                    with right:
                        st.metric(
                            label="Est. prob",
                            value=f"{prob*100:.1f}%",
                            help="Estimated win probability from composite score",
                        )

                    # ── Score breakdown (collapsible) ──
                    with st.expander("Score breakdown", expanded=False):
                        f_s = score_form(horse["form"])
                        d_s = score_distance(horse["distance"])
                        j_s = score_jockey(horse["jockey_rate"])
                        comp = composite_score(horse)

                        b1, b2, b3, b4 = st.columns(4)
                        b1.metric("Form", f"{f_s*100:.0f}")
                        b2.metric("Distance", f"{d_s*100:.0f}")
                        b3.metric("Jockey", f"{j_s*100:.0f}")
                        b4.metric("Composite", f"{comp*100:.0f}")

                    # ── Live odds input ──
                    odds = st.number_input(
                        "Live decimal odds",
                        min_value=1.01,
                        max_value=500.0,
                        value=None,
                        step=0.05,
                        placeholder="e.g. 4.50  — enter to calculate",
                        key=key_odds,
                        format="%.2f",
                    )

                    # ── Value & Kelly output ──
                    if odds and odds > 1.01:
                        implied_prob = 1.0 / odds
                        value        = prob / implied_prob
                        k_pct, k_eur = kelly_stake(prob, odds, bankroll)

                        r1, r2, r3 = st.columns([3, 2, 2])

                        with r1:
                            st.markdown(
                                value_html(value), unsafe_allow_html=True
                            )
                            st.caption(
                                f"Est {prob*100:.1f}% vs implied {implied_prob*100:.1f}%"
                            )

                        with r2:
                            if k_pct > 0:
                                st.markdown(f"**Kelly:** {k_pct:.1f}%")
                            else:
                                st.markdown("**Kelly:** —")

                        with r3:
                            st.markdown(
                                stake_html(k_eur), unsafe_allow_html=True
                            )
                    else:
                        st.caption("_Enter live odds above to see value & stake_")

                    st.markdown("")  # breathing room

    # ── Footer ────────────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        "Scores are model estimates only — not financial advice. "
        "Bet responsibly. | Hoppegarten Racing Tool v1.0"
    )


if __name__ == "__main__":
    main()
