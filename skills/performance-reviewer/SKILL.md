---
name: performance-reviewer
description: Diagnoses a post's performance from its metrics (views, 3-second retention, likes, comments, saves, shares, follows, profile visits) against benchmarks, identifies whether the hook, retention, or CTA is the weak point, and feeds the finding back into strategy. Use when the user shares post metrics and wants to know what to fix.
---

# Performance Reviewer

Closes the loop: takes real metrics and turns them into a specific, actionable diagnosis — which stage of the post failed — rather than a vague "post more" verdict. Findings here should feed back into `ig-strategy` (pillar working or not) and `viral-research`/`reel-hook-generator` (hook/format working or not).

## When to use
- The user shares metrics for a post (from Instagram Insights) and wants to know what worked or didn't.
- Deciding whether to adjust pillars, hook approach, or format based on a pattern across several posts.

## Process

1. **Get the available metrics.** At minimum: views/reach, average watch time or 3-second retention (for Reels), likes, comments, saves, shares, follows from the post, profile visits. Work with whatever subset is actually available — don't block on having every metric.
2. **Diagnose by stage, in order**, since an early-stage failure invalidates reading later-stage numbers:
   - **Low reach relative to the account's baseline** → distribution problem (timing, format mismatch for current algorithm favor, or simply low initial engagement velocity) — not necessarily a content problem.
   - **Low 3-second retention / high early drop-off** → hook problem. Point back at `reel-hook-generator`: which formula was used, and did it actually create a gap or just describe the topic.
   - **Good retention through the middle but low completion** → pacing/payoff problem — the value was promised but took too long to deliver, or the ending was weak.
   - **Good retention but low saves/shares** → value-density problem — people watched but didn't find it worth keeping or passing on; often means the content was entertaining but not useful, or vice versa when the goal needed the other.
   - **Good engagement but low follows** → profile-conversion problem — point at `bio-optimizer`.
   - **Good everything but low link clicks/conversions** → CTA problem — check whether the caption's CTA (per `caption-linter`) was clear and singular.
3. **Compare against the account's own baseline**, not generic industry benchmarks pulled from nowhere — a post's "good" or "bad" is relative to what this specific account normally gets, since audience size and niche vary enormously.
4. **State one primary fix**, not five — pick the earliest-stage problem found, since fixing a downstream stage won't matter if an upstream one is broken.
5. **Route the finding**: hook issues → `reel-hook-generator`/`viral-research`; pacing issues → `reel-scriptwriter`; profile issues → `bio-optimizer`; pattern across multiple posts in one pillar → back to `ig-strategy` to reconsider that pillar.

## Output format

```
Post: [topic/date]
Metrics: [what was provided]
Stage diagnosis: [reach / hook / pacing / value-density / profile-conversion / CTA]
Primary fix: [one specific, actionable change]
Route to: [which skill handles the fix]
```

## Guardrails
- Don't diagnose a later-stage problem (e.g., CTA) when an earlier stage (e.g., retention) already explains the result — fix the earliest broken stage first.
- Don't compare against generic "good engagement rate" numbers without the account's own baseline — ask for recent-post averages if not given.
- One post is a data point, not a trend — flag when a recommendation should wait for a pattern across several posts rather than overreacting to one outlier.
