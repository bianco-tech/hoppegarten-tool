def form_html(form_str: str) -> str:
    from hoppegarten.scoring import parse_form_runs

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
    if v >= 0.9:
        return f'<span style="color:#6b7280;font-weight:800;font-size:1.05rem">⚪ {v:.2f}×</span>'
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
        "Sieg": "#16a34a",
        "Platz": "#2563eb",
        "Sieg/Platz": "#0f766e",
        "Each Way": "#0f766e",
        "Zweier": "#7c3aed",
        "Dreier": "#ea580c",
        "Vierer": "#9333ea",
        "Platz-Zwilling": "#0891b2",
    }
    bg = colors.get(bet_type, "#6b7280")
    return (
        f'<span style="display:inline-block;background:{bg};color:#fff;'
        f'padding:2px 10px;border-radius:12px;font-size:0.80rem;font-weight:700">'
        f'{bet_type}</span>'
    )
