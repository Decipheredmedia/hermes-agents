---
name: profile-optimizer
description: Audit supplied Instagram profile details and suggest clearer positioning and bio options.
---

# Profile Optimizer

Adapted from the profile and account-audit approaches in `ig-profile` and `ig-audit`. Use only
profile text, links, and brand facts explicitly provided by the account owner.

## Workflow

1. Summarize the audience, offer, proof, and next step communicated by the profile.
2. Identify ambiguity, missing context, mismatched calls to action, and unsupported claims.
3. Propose a searchable display-name idea, concise bio alternatives, link destination guidance,
   and optional Highlight categories.
4. Separate observed facts from recommendations; ask for missing business facts instead of guessing.

## Output

Return a short audit, prioritized checklist, and up to three bio drafts. Do not access or modify a
live profile. Changes are recommendations for owner review; never promise ranking or conversion.
