# Betting Rules

## Goal

Generate a logical betting recommendation per race.

Each race should answer:
1. Which horse is the most likely?
2. Which bet type is most suitable?
3. How much should be staked?
4. Why is this the recommendation?
5. Is the price attractive, fair, or poor?

---

## Horse Selection

- Always select the horse with the highest model probability
- This is the "Top Pick"

---

## Race Structure (Edge)

edge = prob_1 / prob_2

- edge > 1.3 → strong favorite
- 1.1–1.3 → moderate edge
- < 1.1 → open race

---

## Bet Type Logic

- Sieg:
  Use when top horse has strong edge (>1.3)

- Platz:
  Use when top horse is best but not dominant

- Zweierwette:
  Use when top 2 horses are clearly above rest

- Dreierwette:
  Use when top 3 horses dominate in larger fields

- Only suggest complex bets if confidence is high

---

## Play / Skip Logic

- PLAY:
  value >= 1.1

- OPTIONAL:
  value 0.95–1.1 AND edge > 1.2

- SKIP:
  value < 0.95 AND no strong edge

---

## Value Calculation

value = model_probability / implied_probability

---

## Value Tiers

- >= 1.25 → strong value
- 1.0–1.25 → positive value
- 0.9–1.0 → fair
- < 0.9 → poor

Important:
Value must NOT override the main recommendation.

---

## Bankroll Logic

- Track:
  - total bankroll
  - already placed bets

remaining_bankroll = bankroll - already_staked

remaining_races = total_races - finished_races

budget_per_race = remaining_bankroll / remaining_races

---

## Stake Allocation

Based on race strength:

- strong → 70–100% of race budget
- medium → 40–70%
- neutral → 20–40%
- weak → 0–10% (or skip)

---

## Combination Bets

Only include PLAY or OPTIONAL races.

### Types:

- Safe Combo:
  place bets only

- Value Combo:
  value >= 1.0

- Mixed Combo:
  best 2–3 picks

---

## Output Requirements

Each race must show:

- horse name
- bet type
- stake (€)
- explanation (why)
- price evaluation

---

## Explanation Logic

Use strongest signals:
- highest probability
- strong jockey
- good form
- distance fit
- clear edge over field

---

## Important

- Always produce a recommendation per race
- Do not skip output completely
- Keep logic consistent across races
- Avoid overfitting or overly complex heuristics