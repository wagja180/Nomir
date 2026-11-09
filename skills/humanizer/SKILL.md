---
name: humanizer
description: Rewrites a script, caption, or voiceover to remove AI-sounding tells (buzzwords, hedging, stock openers, em-dash overuse, no contractions, generic rule-of-three lists) while preserving meaning, and adds specific concrete detail. Use when a draft reads stiff, generic, or "obviously AI-written," or before any script/caption goes out the door.
---

# Humanizer

A pass that makes a draft sound like a person wrote it for this specific account, not like a template filled in for any account. Runs after `caption-writer` or `reel-scriptwriter`, before `caption-linter` (lint rules are easier to satisfy once the filler is gone).

## When to use
- Any script or caption that will be read aloud or posted, as a final pass.
- The user says a draft "sounds like AI," is "too generic," or "needs more personality."

## Process

1. Read `reference/ai-tells.md` for the full tell list.
2. Scan the draft and mark every instance of a tell — quote it, don't just summarize ("found 3 tells" isn't useful; show which words/lines).
3. Rewrite the draft:
   - Cut stock openers, throat-clearers, and buzzwords outright rather than softening them.
   - Replace hedges with a direct claim, or drop the sentence if there's nothing direct to say.
   - Vary sentence length; break up any run of same-length sentences.
   - Add contractions where the content is meant to sound spoken.
   - Find or ask for one concrete, specific, slightly odd detail to anchor the piece — a real number, name, place, or thing that went wrong. If none exists in what's given, ask the user for one rather than inventing a fake specific.
   - Replace generic rule-of-three lists with either a real three-item list (each item distinct and specific) or cut it to one strong point.
4. Preserve the original meaning and CTA — this is a style pass, not a content rewrite. Don't add claims that weren't in the original.
5. Show a before/after, not just the after, so the user can see what changed and why.

## Output format

```
Tells found: [quoted phrase] — [which tell], [quoted phrase] — [which tell], ...

Before:
[original]

After:
[humanized version]

What changed: [1-2 lines on the key moves — e.g. "cut the stock opener, added the specific detail about X, broke up the uniform sentence rhythm"]
```

## Guardrails
- Never invent a fake specific detail (a number, name, or anecdote) to fill the "concrete detail" requirement — ask the user for a real one instead.
- Don't over-correct into forced slang or try-hard casualness — the goal is specific and direct, not performatively "unpolished."
- If the draft is already clean, say so plainly rather than manufacturing changes to justify the pass.
