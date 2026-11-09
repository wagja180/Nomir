---
name: content-calendar
description: Builds a weekly or monthly posting calendar mixing formats (Reels, carousels, static, Stories) across the account's content pillars at a sustainable cadence. Use when the user needs to plan what to post and when, or batch-plan a week/month ahead.
---

# Content Calendar

Turns the pillars and cadence from `ig-strategy` into an actual schedule of what to post, in what format, on which day — so content gets produced in batches instead of decided post-by-post under deadline pressure.

## When to use
- Planning a week or month of content ahead of time.
- The account has pillars defined but no concrete posting schedule.
- Re-planning after `performance-reviewer` shows a pillar or format isn't working.

## Process

1. **Pull the inputs**: content pillars and cadence from `ig-strategy` (ask for them if not already established — don't invent pillars here).
2. **Distribute pillars across the period** so no single pillar dominates and none are skipped — rough balance across the week/month, not a rigid rotation that ignores what's timely.
3. **Assign a format to each slot** based on what the pillar/content suits (per `ig-strategy`'s format-mix guidance): Reels for demonstration/story content, carousels for list/reference content, static/Stories for lighter or time-sensitive updates.
4. **Space out formats and pillars** so similar content isn't posted back-to-back — variety across a week keeps the feed from feeling repetitive even with the same few pillars.
5. **Flag production dependencies**: anything needing trending audio research (`trend-audio-finder`), a scripted hook (`reel-hook-generator`/`reel-scriptwriter`), or carousel design (`carousel-builder`) ahead of the post date, so batching actually works.
6. Leave 1-2 flexible slots per week/month for timely/trend-jack content that can't be planned far in advance.

## Output format

```
Week of [date]
Mon: [pillar] - [format] - [one-line topic]
Wed: [pillar] - [format] - [one-line topic]
Fri: [pillar] - [format] - [one-line topic]
[flex slot]: open for timely content

Prep needed before this week: [e.g., "script + hook for Wed Reel", "carousel design for Fri"]
```

## Guardrails
- Don't schedule a cadence the account can't sustain — match `ig-strategy`'s stated capacity, not an aspirational frequency.
- Don't let one pillar or format dominate the schedule by default; actively balance across the period.
- Keep at least one flexible slot rather than locking 100% of the calendar — trend-relevant content loses value if it has to wait for a rigid schedule.
