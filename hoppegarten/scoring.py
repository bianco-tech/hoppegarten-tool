from hoppegarten.constants import AGE_SCORES, RECENCY_W


def parse_form_runs(form_str: str) -> list:
    if form_str.strip() in ("-", "", "0"):
        return []
    runs = []
    for token in form_str.split(","):
        token = token.strip()
        if not token:
            continue
        ground = token[0]
        try:
            pos = int(token[1:])
        except ValueError:
            continue
        runs.append((ground, pos))
    return runs


def pos_points(pos: int) -> float:
    if pos <= 0:
        return 0
    return {1: 100, 2: 80, 3: 60, 4: 40}.get(pos, 20)


def score_form(form_str: str, today_codes: set) -> float:
    runs = parse_form_runs(form_str)
    grass_runs = [(g, p) for g, p in runs if g.upper() != "S"]
    if not grass_runs:
        return 0.50
    total, max_possible = 0.0, 0.0
    for i, (ground, pos) in enumerate(grass_runs[:10]):
        w = RECENCY_W[i] if i < len(RECENCY_W) else 0.05
        base = pos_points(pos)
        mult = 1.20 if ground.lower() in today_codes else 0.85
        total += base * w * mult
        max_possible += 100 * w * 1.20
    return total / max_possible if max_possible else 0.50


def ground_compat(form_str: str, today_codes: set) -> str:
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
    effective = rate if rate > 0 else 8
    return min(effective, 30) / 30


def score_distance(affinity: str) -> float:
    return {"good": 1.0, "neutral": 0.60, "bad": 0.20}.get(affinity.lower(), 0.60)


def score_career(starts: int, wins: int) -> float:
    if starts == 0:
        return 0.50
    return min(wins / starts, 0.50) / 0.50


def score_season(starts: int, wins: int, placed: int) -> float:
    if starts == 0:
        return 0.50
    win_component = wins / starts
    place_component = placed / starts
    return min(0.7 * win_component + 0.3 * place_component, 0.60) / 0.60


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
    s = score_season(horse.get("season_starts", 0), horse.get("season_wins", 0), horse.get("season_placed", 0))
    w = score_weight(horse["weight"], field_kg)
    e = 1.0 if horse["expert_tip"] else 0.0
    a = score_age(horse["age"])
    raw = 0.32 * f + 0.18 * j + 0.14 * d + 0.08 * c + 0.10 * s + 0.05 * w + 0.08 * e + 0.05 * a
    return raw * 1.08 if horse["expert_tip"] else raw


def race_probs(horses: list, today_codes: set) -> list:
    field_kg = [h["weight"] for h in horses]
    scores = [composite(h, field_kg, today_codes) for h in horses]
    total = sum(scores) or 1.0
    return [s / total for s in scores]
