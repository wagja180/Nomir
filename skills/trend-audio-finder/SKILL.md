---
name: trend-audio-finder
description: Helps identify and track trending or fitting audio for Reels, and maintains a running audio log. Use when the user needs a sound for a Reel, wants to know what audio is trending, or needs help matching a track's tempo/mood to a script.
---

# Trend / Audio Finder

Claude has no live read on Instagram's trending-audio shelf, so this skill is honest about that limit and works with what's actually available: web search for current trend write-ups, cross-platform signal (sounds trending on TikTok often arrive on Reels shortly after), and a disciplined log so the account builds its own audio intelligence over time rather than re-guessing each time.

## When to use
- A Reel script/hook exists (from `reel-scriptwriter` or `reel-hook-generator`) and needs an audio match.
- The user asks what's trending right now.
- Setting up or updating the account's running audio-tracking log.

## Process

1. **If asked "what's trending,"** use available web search tools to check current sources (trend round-ups, creator-economy newsletters, TikTok-to-Reels crossover reports) rather than asserting a specific sound is trending from memory — trending audio changes within days and stale information actively hurts reach. State clearly that this is a point-in-time web check, not live platform data.
2. **If matching audio to a script**, work from the content instead:
   - Tempo: fast-cut hooks/list content want high-energy, consistent-BPM tracks; story/emotional content wants audio with dynamic builds.
   - Mood: match the audio's emotional arc to the script's arc (e.g., a transformation reveal wants a track with a clear "drop" timed to the reveal).
   - Original audio vs. trending sound: recommend original voiceover when the script's specific wording is the value (tutorials, hot takes); recommend trending sound when the format itself (a meme structure, a dance, a transition) is the draw.
3. **Maintain the audio log** so the account isn't re-researching from scratch each time. Append entries rather than overwriting:

```
Date | Sound/Track | Where seen trending | Used on (post) | Result (if known)
```

4. Flag audio licensing basics: commercial/monetized accounts should prefer Meta's licensed sound library or original audio over using another creator's copyrighted track for anything beyond fair-use-scale personal content.

## Output format

```
Recommendation: [sound/approach]
Why it fits: [tempo/mood match to the script, or trend signal + source]
Caveat: [point-in-time check / licensing note, if applicable]
```

## Guardrails
- Never state a specific sound is "currently trending on Reels" without having just checked a real source — say what's actually known and from when.
- Don't recommend audio that requires a license the account doesn't have for commercial use; flag the licensing question rather than ignoring it.
- Keep the log additive — don't delete historical entries when appending new ones.
