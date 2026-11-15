---
name: carousel-builder
description: Structures a multi-slide Instagram carousel post - hook slide, one-idea-per-slide body, CTA/save slide - and pairs it with a caption. Use when the user wants to turn a topic or list into a carousel post rather than a Reel.
---

# Carousel Builder

Carousels reward save/share behavior differently than Reels do — the structure here optimizes for "swipe to the end" and "save for later," not watch-time.

## When to use
- The user wants a carousel post (a list, a step-by-step guide, a breakdown) instead of or alongside a Reel.
- An existing Reel idea would actually work better as a carousel (dense, reference-worthy information).

## Process

1. **Confirm the topic and slide count** (5-10 slides is typical; fewer feels thin, more risks drop-off before the end — flag if the content doesn't actually support the requested count).
2. **Slide 1 — hook slide**: use a hook formula from `reel-hook-generator`'s list, written for a static read rather than spoken delivery (large, short text; the viewer sees the whole slide at once, so it must land instantly).
3. **Body slides — one idea per slide.** Each slide gets exactly one point, step, or item. If a slide needs "and also," it's two slides. Keep text short enough to read in 2-3 seconds; the carousel format rewards scannability over density.
4. **Design text rules** (to pass to whoever builds the visual): large font for the main point, smaller supporting text if needed, high contrast against the background, consistent placement across slides so the eye doesn't have to re-orient each swipe.
5. **Final slide — CTA/save slide.** Summarize the value in one line and give one explicit action ("save this so you don't lose it," "share with someone who needs this"). The save/share CTA belongs here, not buried mid-carousel.
6. Hand off the topic and structure to `caption-writer` for a paired caption — carousel captions typically lean longer since they can expand on a slide that needed to stay short.

## Output format

```
Slide 1 (hook): [text]
Slide 2: [one idea]
Slide 3: [one idea]
...
Slide N (CTA/save): [text]

Design notes: [font/contrast/placement guidance]
```

## Guardrails
- Never let a body slide carry two ideas to hit a target slide count — cut the count instead.
- Don't write dense paragraphs onto a slide; if the point needs more than ~2-3 short lines, split it across slides.
- Flag when a topic is too thin for the requested slide count rather than padding with filler slides.
