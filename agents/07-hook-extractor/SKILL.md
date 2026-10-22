---
name: hook-extractor
description: Extract and categorize reusable hook patterns from user-provided or authorized material.
---

# Hook Extractor

Derive original hook templates from the hook evaluation concepts in `ig-viral`. Analyze only
user-provided scripts/captions or material from a source the user is authorized to use.

## Workflow

1. Identify the opening line or first visual beat and summarize its promise without copying more than
   needed to analyze the submitted text.
2. Categorize the mechanism (curiosity, problem, contrast, demonstration, question, or story).
3. Assess clarity, audience fit, and whether the content actually pays off the opening.
4. Generate distinct, original variants; flag clickbait, unsupported certainty, or misleading gaps.

## Output

Return source/context, category, concise critique, and a small library of original variants with
audience and format labels. Do not scrape competitor posts or create deceptive hooks.
