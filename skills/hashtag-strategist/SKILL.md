---
name: hashtag-strategist
description: Selects a small, relevant, tiered set of hashtags for a post instead of generic high-volume tags, and rotates sets across posts. Use when a caption has a [hashtags] placeholder to fill, or the user asks what hashtags to use.
---

# Hashtag Strategist

Fills the `[hashtags]` placeholder `caption-writer` leaves behind. The approach favors a small set of specific, relevant tags over a large set of generic ones — broad tags like #love or #instagood put a post in front of the biggest, least-relevant audience and rarely move discovery.

## When to use
- A caption is drafted and needs its hashtag set filled in.
- The user asks what hashtags to use for a post or niche.

## Process

1. **Get the post's topic and the account's niche** (from `ig-strategy` if available).
2. **Build a tiered set of 3-8 tags**, not 30:
   - 1-2 broad/niche tags (established, sizable community, directly relevant — not just popular).
   - 2-4 micro-niche tags (smaller, highly specific to the exact topic — these are where discovery actually happens for a smaller account).
   - 0-2 branded/community tags (the account's own tag, or a known community/challenge tag, if relevant).
3. **Reject tags that are**: unrelated to the actual content (even if popular), flagged engagement-bait patterns (#like4like, #follow4follow, #f4f), or so broad they're meaningless (#photooftheday on a business account).
4. **Rotate sets across posts** rather than reusing the identical block every time — note in the output whether this set overlaps heavily with recent posts and suggest swapping 1-2 tags if so.
5. Place hashtags at the end of the caption (default) or note they can go in the first comment if the user prefers a cleaner caption look.

## Output format

```
Hashtags (N total): #tag1 #tag2 #tag3 ...
Tiers: [broad: ...] [micro-niche: ...] [branded/community: ...]
Rotation note: [new set / overlaps with recent posts on X, Y — consider swapping]
```

## Guardrails
- Never default to a large generic block just because it "can't hurt" — it dilutes relevance signal and the guidance here is specifically against that pattern.
- Don't recommend a tag flagged as commonly restricted/shadowbanned if the user names one; suggest a specific alternative instead.
- If the account's niche isn't known, ask rather than guessing a generic set.
