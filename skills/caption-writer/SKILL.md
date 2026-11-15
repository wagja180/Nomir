---
name: caption-writer
description: Drafts an Instagram caption for a post (Reel, carousel, or static image) with a standalone first-line hook, right-sized body, and one clear CTA. Use when a post's visual/script exists and needs a caption written, before running it through caption-linter.
---

# Caption Writer

Drafts captions to a format that `caption-linter` can then check mechanically. This skill writes the first draft; it doesn't need to be perfect, since lint and `humanizer` passes follow.

## When to use
- A Reel script, carousel, or static image exists and needs a caption.
- The user wants a caption option set (a few variations) to choose from.

## Process

1. **Get the post's substance**: what the visual/video shows, the content pillar it belongs to (see `ig-strategy`), and the goal (reach, saves, comments, link clicks).
2. **Write the first line as a standalone hook** — it must work before Instagram's truncation point (~125 characters) and should not simply restate the video's hook verbatim; it can complement it (e.g., add the "why" if the video hook was the "what").
3. **Size the body to the goal**: short (1-3 lines) for pure-reach/entertainment content where the video does the work; longer (150-300+ words, broken into short paragraphs) for save-worthy tips/lists/guides where the caption itself adds value.
4. **Include exactly one CTA**, specific rather than generic ("save this for your next [X]" beats "let me know what you think").
5. **Format for readability**: line breaks between ideas, not a single block; emoji used sparingly as visual breaks if at all.
6. **Leave a hashtag placeholder** (`[hashtags]`) rather than guessing — hand off to `hashtag-strategist` for the actual tag selection.
7. If asked for options, produce 2-3 variations that differ in angle (e.g., one leads with a question, one leads with a stat, one leads with a confession) rather than 2-3 trivial rewordings of the same line.

## Output format

```
Caption option 1:
[first-line hook]

[body]

[CTA]

[hashtags]
```

## Guardrails
- Never leave the CTA generic by default — push for specificity even in a first draft.
- Don't duplicate a URL in the caption body (Instagram captions can't render clickable links) — use "link in bio" instead.
- Treat this output as a draft: tell the user it should go through `caption-linter` (and `humanizer` if it reads stiff) before publishing.
