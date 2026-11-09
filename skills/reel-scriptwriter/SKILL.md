---
name: reel-scriptwriter
description: Turns a chosen hook and content idea into a full, timed Reel script (hook, setup, value beats, CTA) for a target length. Use when the user has a hook and topic and needs the rest of the script written, or needs an existing script tightened to fit a shorter runtime.
---

# Reel Scriptwriter

Takes the output of `reel-hook-generator` (or a hook the user already has) and builds the rest of the script around it, timed to the target length. A script here is the full spoken/on-screen content, not the caption — hand off to `caption-writer` separately once the script is locked.

## When to use
- A hook exists and the Reel needs a full script.
- An existing script is running long/short for its target length and needs restructuring.

## Process

1. **Confirm the hook, topic, and target length** (common targets: 15s, 30s, 60s, 90s+). If no hook is provided, suggest running `reel-hook-generator` first rather than inventing a weak one inline.
2. **Build the beat structure**, scaled to length:
   - **Hook (0-3s)**: the chosen hook line, verbatim.
   - **Setup/context (next ~10-15%)**: just enough framing to make the payoff land — don't over-explain before delivering value.
   - **Value beats (bulk of runtime)**: the actual content, broken into 2-4 distinct beats for longer formats (a list, a sequence of steps, a story's rising stakes) or one continuous demonstration for shorter ones. Each beat should be a single idea — if a beat needs "and also," split it.
   - **CTA (final ~5-10%)**: one clear action, matched to the account's goal (save, follow, comment, link in bio) — see `caption-writer` for pairing this with the caption's CTA so they reinforce rather than duplicate awkwardly.
3. **Time-check**: estimate spoken word count against the target length (roughly 2.5-3 words/second for normal speaking pace) and trim or expand to fit. Flag if the content genuinely needs more time than the target allows rather than cramming it.
4. **Mark on-screen text cues** separately from spoken lines where they diverge (on-screen text is often shorter/punchier than the voiceover).
5. Note suggested cut/B-roll points if the format calls for them (e.g., "cut to demonstration here").

## Output format

```
Target length: [Xs]
Hook (0-3s): "[line]"  [on-screen: "..."]
Setup: "[line(s)]"
Beat 1: "[line(s)]"  [cut/B-roll note if relevant]
Beat 2: ...
CTA: "[line]"

Estimated runtime: [Xs] — [fits / trim by Y / expand]
```

## Guardrails
- Don't pad a short-format script with filler to hit a longer runtime — if the content is genuinely a 20-second idea, say that rather than stretching it to 60s.
- Keep claims consistent with what the account can actually substantiate — don't let the script's energy outrun the facts.
- Hand off to `humanizer` before treating a script as final if it reads stiff or generic.
