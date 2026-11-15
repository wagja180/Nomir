---
name: reel-hook-generator
description: Generates and scores opening hooks for Instagram Reels using 26 formulas (callouts, contrarian takes, curiosity gaps, confessions, stats, questions, urgency). Use when the user needs a hook, opening line, or first 3 seconds for a Reel, or asks to improve a weak-performing hook.
---

# Reel Hook Generator

The first 1-3 seconds of a Reel decide whether it gets watched. This skill produces several hook candidates from different formulas, scores each on a fixed rubric, and recommends a winner — instead of guessing at one line.

## When to use
- User is starting a new Reel and needs an opening line (spoken, on-screen text, or both).
- User has a Reel idea but it's getting low 3-second retention and needs a sharper hook.
- Feeding into `reel-scriptwriter`, which expects a chosen hook as its starting point.

## Process

1. **Get the content core.** Ask for (or infer from what's already provided): the topic/outcome, who it's for, and the one non-obvious thing the Reel actually teaches or shows. A hook with nothing specific behind it will score low no matter the formula.
2. **Load the formula list.** Read `reference/hook-formulas.md` for the full set of 26 formulas and the scoring rubric.
3. **Generate 5-8 candidates** pulled from at least 4 different formula categories (don't cluster all picks in "curiosity gap," for instance) — variety surfaces which angle actually fits the content.
4. **Score every candidate** 1-5 on each of: curiosity gap, specificity, targeting, pattern interrupt, stakes (see rubric). Show the scores, don't just assert a winner.
5. **Present the top 3**, ranked, with their total score and one line on why each works. For the top pick, also give the on-screen text version (short, punchy) separate from the spoken version if they differ.
6. **Offer one iteration**: if the user wants to push the winner further, rewrite only its lowest-scoring dimension and re-score.

## Output format

```
Top hooks for: [topic]

1. [Formula name] — "[hook line]"  — Score: XX/25
   On-screen text: "[shortened version]"
   Why it works: [one line]

2. ...
3. ...

Recommended: #[n]
```

## Guardrails
- Never leave a bracket/placeholder unfilled in a delivered hook — use the real specifics the user gave you.
- Don't fabricate a statistic or urgency claim to fit a formula (see formulas 9, 19, 24 in the reference file) — if there's no real number, pick a different formula.
- If the user's content doesn't support a strong hook (too generic, no real payoff), say so and ask one clarifying question rather than inflating scores.
