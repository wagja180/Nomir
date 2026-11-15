---
name: caption-linter
description: Checks a draft Instagram caption against a fixed rule set (hook line, length-to-goal fit, single clear CTA, readability, hashtag count/placement, banned cliché phrases, unverifiable claims, accessibility, dead links) and reports pass/fail with fixes. Use when the user has a drafted caption and wants it checked, tightened, or approved before posting.
---

# Caption Linter

A mechanical pass over a caption draft — not a rewrite from scratch (use `caption-writer` for that, and `humanizer` if the draft reads like AI wrote it). This skill's job is to catch concrete, fixable problems: a buried hook, a missing or overloaded CTA, hashtag spam, cliché phrases, unsupported claims, bad formatting.

## When to use
- A caption already exists (drafted by the user or by `caption-writer`) and needs a check before publishing.
- The user asks "does this caption work?" or "what's wrong with this caption?"

## Process

1. Read `reference/lint-rules.md` for the full rule set.
2. Run the caption against every rule in order. Don't skip rules because the caption "looks fine" — check each one explicitly.
3. For each rule, report **Pass** or **Fail — [specific fix]**, quoting the exact phrase/line that failed when relevant.
4. End with one overall verdict: **Ship it**, **One fix needed**, or **Needs a rewrite** — and say which rule(s) drove that verdict.
5. If the verdict is anything but "ship it," offer to apply the fixes directly rather than just listing them.

## Output format

```
Caption lint: [post topic/first few words]

1. First-line hook: Pass/Fail — [note]
2. Length fits goal: Pass/Fail — [note]
3. Single clear CTA: Pass/Fail — [note]
4. Readability/formatting: Pass/Fail — [note]
5. Hashtags: Pass/Fail — [note]
6. Banned/cliché phrases: Pass/Fail — [note]
7. Claims & compliance: Pass/Fail — [note]
8. Accessibility: Pass/Fail — [note]
9. No dead links: Pass/Fail — [note]

Verdict: [Ship it / One fix needed / Needs a rewrite]
```

## Guardrails
- Don't soften a real failure to be agreeable — a caption with three competing CTAs is a fail even if the writing is otherwise good.
- Don't flag a long caption as automatically bad — length is only a fail when it doesn't fit the post's goal (see rule 2).
- If a claim-and-compliance fail is borderline, ask the user whether the claim is actually substantiated before flagging it as unverifiable.
