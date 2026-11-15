# Caption Lint Rules

Run every rule below against a caption and report pass/fail with the fix, not just a verdict.

## 1. First-line hook
- The first line must make sense and create curiosity on its own, before Instagram's "... more" truncation (roughly the first 125 characters, less on some devices).
- Fail if the first line is a greeting, a hashtag, an emoji string, or a sentence that depends on the next line to make sense.

## 2. Length fits the goal
- Reach/discovery posts: short captions (1-3 lines) outperform — the video is the draw.
- Save/share posts (tips, lists, guides): longer captions (150-300+ words) are fine and often help, since they add context worth saving.
- Fail if caption length and post goal are mismatched (e.g., a 300-word caption on a pure entertainment clip).

## 3. One clear CTA
- Exactly one primary call-to-action: save, share, comment, follow, or link-in-bio. Pick one.
- Fail if there are 0 CTAs (missed opportunity) or 3+ competing CTAs (dilutes all of them).
- Flag vague CTAs ("check it out," "let me know") — prefer specific ones ("save this for later," "send this to someone who needs it").

## 4. Readability / formatting
- Short lines, line breaks between ideas, no dense unbroken paragraphs.
- Fail if there's a single block of text longer than ~4 lines with no break.
- Emoji used as visual breaks/bullets is fine; emoji used as filler on every line is a fail (flag density > ~1 per line as excessive).

## 5. Hashtags
- 3-8 specific, relevant hashtags beat 30 generic ones. Fail if hashtags exceed ~10 or are copy-pasted boilerplate unrelated to the post.
- Hashtags belong at the end of the caption or in the first comment, never interrupting the body text.
- Flag any hashtag that's been shadowbanned/flagged as spammy if the user mentions one (can't verify live, but warn on obviously overused generic tags like #follow4follow, #likeforlike).

## 6. Banned / cliché phrases
Flag and suggest a replacement for stock phrases that read as filler or as AI-generated:
- "In today's world," "In this day and age"
- "It's important to note that"
- "Game changer," "elevate your," "unlock," "dive into," "embark on a journey"
- "Let's dive in," "Without further ado"
- Generic triplets with no specific content ("faster, better, stronger" with nothing concrete behind each word)

## 7. Claims & compliance
- Flag unverifiable or risky claims: guaranteed results, specific health/medical/financial outcomes, "doctors hate this," before/after numbers with no basis.
- Fail if a claim could get the account flagged or is simply untrue to what the content shows.

## 8. Accessibility
- Remind the user to add alt text for the post (not part of the caption itself, but a required pairing step) when the image/video content isn't described anywhere in the caption.
- Avoid relying on emoji alone to convey required meaning (screen readers read emoji names aloud, which can be noisy or unclear).

## 9. No dead links
- Caption text can't contain a clickable link on Instagram — flag any URL in the caption body and suggest moving it to bio/CTA instead ("link in bio").

## Report format
For each rule, report **Pass** or **Fail — [specific fix]**. End with a one-line overall verdict (ship / needs one fix / needs rewrite) — don't just list failures without a verdict.
