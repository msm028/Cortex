# Cortex Operating Rules

## Rules Of Engagement

- Work in small, buildable chunks.
- Define clear exit criteria before starting each chunk.
- Run deterministic validation first and again after changes.
- State blast radius and rollback for every change.
- Never put secrets in the repo. Use Vaultwarden item IDs only.
- Update relevant docs as each step lands.
- Keep communication in direct AU tone: concise, factual, no fluff.

## Required Per-Task Checklist

- Chunk scope is minimal and testable.
- Exit criteria are explicit.
- Validation path is deterministic.
- Blast radius is documented.
- Rollback command/path is documented.
- Docs touched alongside code changes.
