# Project Context

This project is a horse racing decision tool, not just a bet slip generator.

## Main Purpose
The app helps users:
- analyze races
- compare horses
- enter live odds
- receive clear betting recommendations

The goal is to provide a logical decision per race, not just pure value betting.

---

## Main UI Structure

### 1. Race Overview
- Display all races of the day
- Each race contains:
  - race number
  - time
  - conditions
  - list of horses

### 2. Horse Cards
Each horse card should show:
- horse name
- jockey, trainer, age, weight
- career / form indicators
- estimated probability (model output)
- score details
- live odds input

### 3. Odds Input
- Users can manually enter decimal odds per horse
- These odds are used to calculate:
  - implied probability
  - value (model vs market)
  - stake recommendations

### 4. Bet Slip ("Mein Wettschein")
- Always generate ONE recommendation per race
- Show:
  - selected horse (Top Pick)
  - bet type (Sieg / Platz etc.)
  - recommended stake (€)
  - short explanation (why)
  - price evaluation (good / fair / too low)

Important:
The bet slip must always show a complete overview of all races.

---

## Product Philosophy

- The best horse ≠ the best bet
- Model probability is the primary signal
- Odds are secondary (price evaluation)
- The system should always produce a recommendation
- The UI must clearly separate:
  - model strength (probability)
  - price quality (odds/value)

---

## UX Principles

- Keep UI clean and readable (dark theme)
- Do not color entire rows strongly (use accents only)
- Horse names must be clearly readable
- Separate:
  - recommendation
  - price evaluation
- Always explain decisions in simple terms

---

## Future Features

- Play / Skip system
- Combo bets
- Bankroll tracking across races
- Advanced bet types (Exacta, Trifecta, etc.)

---

## Coding Instructions for Claude

- Use BETTING_RULES.md as the source of truth for betting logic
- Do NOT invent betting rules
- Keep logic explainable and simple
- Prefer deterministic behavior over randomness
- Ensure UI updates correctly when odds change