from pathlib import Path
import re
import streamlit as st


def _parse_season_triplet(raw: str):
    parts = raw.strip().split("/")
    if len(parts) != 3:
        return 0, 0, 0
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return 0, 0, 0


@st.cache_data(ttl=30)
def load_races(path: str) -> list:
    content = Path(path).read_text(encoding="utf-8")
    race_blocks = re.split(r"(?m)^# Race\s+", content)
    races = []

    for block in race_blocks[1:]:
        lines = block.split("\n")
        header_parts = [p.strip() for p in lines[0].split("|")]
        race_num = header_parts[0].strip()
        distance = header_parts[1] if len(header_parts) > 1 else ""
        prize = header_parts[2] if len(header_parts) > 2 else ""
        runners_str = header_parts[3] if len(header_parts) > 3 else ""
        time_conditions = header_parts[4] if len(header_parts) > 4 else ""

        notes = []
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith("## ") or (
                not stripped.startswith("## ")
                and any(stripped.startswith(f"## {c}") for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            ):
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
                elif line.startswith("Season") and ":" in line:
                    season_starts, season_wins, season_placed = _parse_season_triplet(line.split(":", 1)[1])
                elif line.startswith("Form:"):
                    form_str = line[5:].strip()
                elif line.startswith("DistancePref:"):
                    dist_affinity = line[13:].strip().lower()
                elif line.startswith("ExpertTip:"):
                    expert_tip = line[10:].strip().lower() == "yes"

            horses.append(
                dict(
                    name=name,
                    jockey=jockey,
                    jockey_rate=jockey_rate,
                    trainer=trainer,
                    weight=weight,
                    age=age,
                    career_starts=career_starts,
                    career_wins=career_wins,
                    season_starts=season_starts,
                    season_wins=season_wins,
                    season_placed=season_placed,
                    form=form_str,
                    distance=dist_affinity,
                    expert_tip=expert_tip,
                )
            )

        if horses:
            races.append(
                dict(
                    num=race_num,
                    distance=distance,
                    prize=prize,
                    runners=runners_str,
                    time_conditions=time_conditions,
                    notes=notes,
                    horses=horses,
                )
            )

    return races
