# Nomir

Thirteen Claude skills that run an Instagram account end to end — strategy, research, scripting, writing, and review. Free, MIT licensed.

Drop the `skills/` folder into a project with Claude Code (or any Claude surface that loads skills) and each one triggers automatically when the task fits — generate a Reel hook, lint a caption, humanize a stiff draft, diagnose a flop.

## The pipeline

```
ig-strategy  ──────────────────────────────────────────────┐
     │                                                      │
     ▼                                                      │
viral-research ──► trend-audio-finder                       │
     │                                                       │
     ▼                                                       │
reel-hook-generator ──► reel-scriptwriter ──► caption-writer │
                                                    │         │
                                                    ▼         │
                                            caption-linter     │
                                                    │          │
                                                    ▼          │
                                               humanizer       │
                                                    │          │
                                                    ▼          │
                                          hashtag-strategist   │
                                                                │
carousel-builder (alt. to reel-scriptwriter for list/guide posts)
                                                                │
content-calendar  ◄─────────────────────────────────────────┘ (schedules all of the above)
bio-optimizer      (profile-level, run independently)
performance-reviewer ──► feeds findings back into ig-strategy / viral-research / bio-optimizer
```

## Skills

| Skill | Does |
|---|---|
| [`ig-strategy`](skills/ig-strategy) | Defines niche, audience, content pillars, cadence, and success metrics. |
| [`viral-research`](skills/viral-research) | Breaks down why a given top-performing post worked and extracts a reusable pattern. |
| [`trend-audio-finder`](skills/trend-audio-finder) | Matches audio to a script's tempo/mood and keeps a running trend log. |
| [`reel-hook-generator`](skills/reel-hook-generator) | Generates and scores Reel hooks against **26 formulas** on a 5-dimension rubric. |
| [`reel-scriptwriter`](skills/reel-scriptwriter) | Builds a full timed script around a chosen hook. |
| [`caption-writer`](skills/caption-writer) | Drafts a caption with a standalone hook line and one CTA. |
| [`caption-linter`](skills/caption-linter) | Checks a caption against 9 fixed rules and reports pass/fail with fixes. |
| [`humanizer`](skills/humanizer) | Strips AI-sounding tells from a script or caption and adds concrete specificity. |
| [`hashtag-strategist`](skills/hashtag-strategist) | Picks a small tiered hashtag set instead of 30 generic tags. |
| [`carousel-builder`](skills/carousel-builder) | Structures a multi-slide carousel: hook slide, one idea per slide, CTA slide. |
| [`content-calendar`](skills/content-calendar) | Turns pillars + cadence into an actual weekly/monthly posting schedule. |
| [`bio-optimizer`](skills/bio-optimizer) | Optimizes bio text, link-in-bio, highlights, and searchability. |
| [`performance-reviewer`](skills/performance-reviewer) | Diagnoses which stage of a post failed (reach, hook, pacing, value, profile, CTA) from its metrics. |

## Usage

Each skill is a standard `SKILL.md` (with reference files where the subject needs more detail than belongs inline — the 26 hook formulas, the caption lint rules, the AI-tell list). Point Claude at this repo, or copy `skills/` into your own project's skills directory, and ask for what you need:

- "Give me a hook for a Reel about [topic]" → `reel-hook-generator`
- "Does this caption work?" → `caption-linter`
- "This script sounds like AI wrote it" → `humanizer`
- "Here are last week's numbers, what should I fix?" → `performance-reviewer`

No skill here has live access to Instagram's own data (trends, algorithm signals, account insights) — they work from what you give them (metrics you paste in, posts you link or describe) and say so rather than guessing.

## License

MIT — see [LICENSE](LICENSE).
