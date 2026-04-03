from hoppegarten.constants import TIER_RANGES
from hoppegarten.scoring import ground_compat, parse_form_runs


def kelly(est_prob: float, decimal_odds: float, bankroll: float) -> tuple:
    if decimal_odds <= 1.0 or est_prob <= 0:
        return 0.0, 0.0
    b = decimal_odds - 1.0
    k = (b * est_prob - (1.0 - est_prob)) / b
    if k <= 0:
        return 0.0, 0.0
    k = min(k * 0.5, 0.25)
    return round(k * 100, 1), round(k * bankroll, 2)


def full_kelly_frac(est_prob: float, decimal_odds: float) -> float:
    if decimal_odds <= 1.0 or est_prob <= 0:
        return 0.0
    b = decimal_odds - 1.0
    k = (b * est_prob - (1.0 - est_prob)) / b
    return max(0.0, k)


def value_tier(value: float) -> str:
    if value >= 1.25:
        return "strong"
    if value >= 1.00:
        return "medium"
    if value >= 0.90:
        return "neutral"
    return "weak"


def budget_stake(kelly_frac: float, race_budget: float, tier: str, min_bet: float) -> float:
    lo, hi = TIER_RANGES.get(tier, (0.20, 0.40))
    kelly_norm = min(kelly_frac / 0.30, 1.0)
    pct = lo + kelly_norm * (hi - lo)
    stake = round(pct * race_budget, 2)
    if tier == "weak":
        return 0.0 if stake < min_bet else stake
    return max(stake, min_bet)


def decide_bet_type(ranked: list, n_runners: int, top_value=None) -> str:
    if not ranked:
        return "Platz"
    if len(ranked) < 2:
        return "Sieg"
    p1 = ranked[0][1]
    p2 = ranked[1][1]
    edge = p1 / max(p2, 0.0001)
    gap = p1 - p2
    if top_value is not None and top_value < 0.95 and edge < 1.20:
        return "Platz"
    if n_runners <= 6 and gap >= 0.07:
        return "Sieg"
    if edge >= 1.30 or gap >= 0.10:
        return "Sieg"
    if edge >= 1.15:
        return "Sieg/Platz"
    return "Platz"


def recommend_bet(ranked: list, n_runners: int):
    if not ranked:
        return None
    horse, prob, value = ranked[0]
    bet_type = decide_bet_type([(h, p) for h, p, _ in ranked], n_runners, value)
    return bet_type, [horse["name"]]


def play_status(value, edge: float) -> tuple:
    if value is None:
        return "pending", "⏳ Quote fehlt"
    if value >= 1.10:
        return "play", "✅ Play"
    if value >= 0.95 and edge > 1.20:
        return "optional", "⚠️ Optional"
    return "skip", "❌ Skip"


def make_explanation(horse: dict, prob_gap: float, value, bet_type: str, today_codes: set) -> str:
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
    if horse.get("season_wins", 0) >= 2:
        reasons.append("starke Saisonform")
    if not reasons:
        reasons.append("Algorithmus-Favorit")

    if bet_type == "Sieg":
        bet_reason = f"klarer Vorteil (Δ {prob_gap*100:.0f}%p)"
    elif bet_type == "Sieg/Platz":
        bet_reason = f"stark, aber nicht dominant (Δ {prob_gap*100:.0f}%p)"
    else:
        bet_reason = f"knappes Feld (Δ {prob_gap*100:.0f}%p)"

    if value is not None:
        if value >= 1.10:
            price_note = "attraktiver Preis"
        elif value >= 0.95:
            price_note = "Preis okay"
        else:
            price_note = "Preis eher schwach"
        return ", ".join(reasons) + " — " + bet_reason + f", {price_note}"

    return ", ".join(reasons) + " — " + bet_reason


def price_eval_str(value) -> str:
    if value is None:
        return "— Quote fehlt"
    if value >= 1.25:
        return "🟢 Gute Quote"
    if value >= 1.00:
        return "🟡 Faire Quote"
    if value >= 0.90:
        return "⚪ Fast fair"
    return "🔴 Tiefe Quote"


def suggest_exotics(ranked: list, n_runners: int, odds_map: dict) -> list:
    suggestions = []
    if len(ranked) < 2:
        return suggestions

    p1 = ranked[0][1]
    p2 = ranked[1][1]
    p3 = ranked[2][1] if len(ranked) >= 3 else 0.0
    edge12 = p1 / max(p2, 0.0001)
    gap23 = p2 - p3 if len(ranked) >= 3 else 0.0

    top2 = [ranked[0][0]["name"], ranked[1][0]["name"]]
    top3 = [ranked[0][0]["name"], ranked[1][0]["name"], ranked[2][0]["name"]] if len(ranked) >= 3 else []
    top4 = [r[0]["name"] for r in ranked[:4]] if len(ranked) >= 4 else []

    if edge12 >= 1.15:
        suggestions.append({
            "bet_type": "Zweier",
            "horses": top2,
            "reason": "Top 2 heben sich vom Feld ab",
        })
    else:
        suggestions.append({
            "bet_type": "Platz-Zwilling",
            "horses": top2,
            "reason": "offeneres Rennen, Top 2 ohne feste Reihenfolge",
        })

    if n_runners >= 8 and len(top3) == 3 and gap23 > 0.01:
        suggestions.append({
            "bet_type": "Dreier",
            "horses": top3,
            "reason": "Top 3 strukturieren das Rennen klar",
        })

    if n_runners >= 10 and len(top4) == 4:
        suggestions.append({
            "bet_type": "Vierer",
            "horses": top4,
            "reason": "großes Feld, Viererwette als Longshot-Option",
        })

    for item in suggestions:
        dec_odds = []
        for horse_name in item["horses"]:
            if horse_name in odds_map:
                dec_odds.append(odds_map[horse_name][0])
        item["indicative_odds"] = round(_combine_odds(dec_odds), 2) if dec_odds else None
    return suggestions


def _combine_odds(decimal_odds: list) -> float:
    if not decimal_odds:
        return 0.0
    product = 1.0
    for odd in decimal_odds:
        product *= max(odd, 1.01)
    return product


def build_combo_suggestions(rows: list, budget_for_combos: float, min_bet: float) -> list:
    eligible = [r for r in rows if r.get("has_odds") and r.get("play_code") in ("play", "optional") and r.get("odds")]
    if len(eligible) < 2:
        return []

    safe_candidates = [r for r in eligible if r["bet_type"] in ("Platz", "Sieg/Platz")][:3]
    value_candidates = [r for r in eligible if (r.get("value") or 0) >= 1.0][:3]
    mixed_candidates = sorted(eligible, key=lambda r: ((r.get("value") or 0) * (r.get("edge") or 1.0)), reverse=True)[:3]

    combos = []
    for label, selected, share in [
        ("Safe Combo", safe_candidates, 0.40),
        ("Value Combo", value_candidates, 0.35),
        ("Mixed Combo", mixed_candidates, 0.25),
    ]:
        if len(selected) < 2:
            continue
        combo_odds = _combine_odds([r["odds"] for r in selected if r.get("odds")])
        stake = max(round(budget_for_combos * share, 2), min_bet)
        combos.append({
            "label": label,
            "legs": selected,
            "combined_odds": round(combo_odds, 2),
            "stake": stake,
        })
    return combos
