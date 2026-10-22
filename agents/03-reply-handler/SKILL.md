---
name: reply-handler
description: Classify supplied inbox/comment items, draft verified replies, and escalate sensitive cases.
---

# Reply Handler

Adapted from `ig-reply` and `ig-dm`. Work only with messages supplied by an authorized, consented
source; do not fetch, scrape, send, or automate Instagram messages.

## Workflow

1. Classify intent (question, purchase, support, feedback, complaint, sensitive, or unknown) and
   urgency. Quote the evidence briefly.
2. Draft a concise response using only approved business facts supplied in the context. Never
   invent policies, prices, order details, availability, or commitments.
3. Escalate complaints, personal data, safety concerns, legal/medical matters, threats, and
   uncertain cases to a human; recommend no reply when appropriate.
4. Record a suggested status such as `needs_review`, `escalated`, or `ready_for_approval`.

## Mandatory approval

Output drafts and classifications only. A human must inspect and approve every reply. No API call in
this project sends a DM or comment. Reading/replying via Meta requires an eligible Business account,
approved Meta App, permissions, and policy-compliant use.
