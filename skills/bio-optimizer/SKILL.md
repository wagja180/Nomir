---
name: bio-optimizer
description: Optimizes an Instagram profile - bio text, link-in-bio structure, highlight naming, username/display-name searchability. Use when setting up a new account or when the profile isn't converting profile visits into follows/clicks.
---

# Bio Optimizer

The profile is the second conversion step after a hook earns a profile visit — this skill makes sure that visit actually converts to a follow or a click.

## When to use
- Setting up a new account's profile.
- An account gets profile visits (per `performance-reviewer`) but a low follow or link-click rate from them.

## Process

1. **Bio formula**: who you help + what result + one differentiator, in as few words as possible (Instagram bios have a hard character limit — brevity isn't optional). Structure: line 1 = who/what you do, line 2 = the specific result or proof point, line 3 = the CTA pointing at the link.
2. **Display name field**: should contain a searchable keyword from the niche (what people would actually type into Instagram's search), not just a stylized version of the account name — this field is searchable in a way the bio text isn't.
3. **Username**: flag if it's hard to say out loud, hard to spell, or buried under numbers/underscores that make it hard to find; a clean, memorable, niche-relevant handle beats a clever one that's hard to type correctly.
4. **Link-in-bio structure**: one clear primary link if there's one dominant goal (a specific offer, a single destination); a link-in-bio tool with a short menu (3-5 options max) if there are multiple goals — more than that and visitors won't scan the whole list.
5. **Highlight covers and naming**: name highlights by the viewer's need ("Start Here," "FAQ," "Results") rather than vague labels; recommend a consistent visual style across covers so the profile looks curated at a glance, without prescribing a specific design tool.

## Output format

```
Bio:
[line 1: who/what]
[line 2: result/proof]
[line 3: CTA -> link]

Display name: [name with searchable keyword]
Username note: [keep / flag + suggested fix]
Link-in-bio: [single link / menu with N options]
Highlights: [suggested names in priority order]
```

## Guardrails
- Keep the bio within Instagram's actual character limit — don't draft something that would get cut off.
- Don't recommend a link-in-bio menu with more than ~5 options; more than that undermines the "clear primary action" goal.
- Don't invent a result/proof point the account hasn't actually achieved — ask for a real one.
