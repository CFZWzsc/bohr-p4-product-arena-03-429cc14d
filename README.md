# Runtime contract

Bohrium Playground Period 4 submission — challenge `product-arena-03-429cc14d` (track: `academic-writing`).

This repository holds the complete skill package for the challenge: the skill
definition, its executable entry point and all supporting scripts. No precomputed
answers, private data or credentials are included.

## Skill

- Name: `citation-reference-governance`
- Summary: Reconcile a manuscript with its reference library by renumbering citations in first-appearance order, detecting dangling and uncited entries, merging duplicates with an explicit criterion, and rendering a synchronous bibliography. Use when a task asks for citation insertion checks, numbering updates, deduplication or reference-style conversion.

## Contents

| File |
|------|
| `SKILL.md` |
| `scripts/run_skill.py` |
| `README.md` |

## How to run

```bash
python scripts/run_skill.py --case /input/case.json --output /app/output/result.json
```

The entry point is `SKILL.md`; input/output contracts, error handling and a minimal
usage example are documented there.

## Notes

- Pure Python standard library; no network access required.
- The result JSON keeps the input case id, the main results, per-item evidence,
  a run status and an uncertainty section.
