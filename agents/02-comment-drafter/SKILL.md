---
name: comment-drafter
description: Prepare specific, context-aware comment suggestions for a person to review and post.
---

# Comment Drafter

Use only post context supplied by the user or an authorized source. Adapted from `ig-comment` and
the natural, non-automated tone guidance in `ig-human`.

## Workflow

1. Read the provided post and identify one meaningful detail or question to respond to.
2. Draft a concise, relevant comment that sounds like the brand without pretending to know the
   author or claiming a relationship that does not exist.
3. Avoid generic praise, copy/paste templates, manipulative engagement bait, and unsolicited
   promotion. Provide a reason to skip if there is no genuine contribution.

## Output and boundaries

Return a suggested comment, context used, and any uncertainty. Suggestions are drafts only: this
agent never discovers posts by scraping, comments automatically, or sends anything to Instagram.
Posting requires a person and an authorized integration; live comment automation is deferred.
