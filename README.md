# GitHub stacked PRs with Alembic

This repository tests GitHub's stacked pull requests public preview against a linear Alembic migration workflow.

Tracked in [FACT-17559](https://linear.app/joby/issue/FACT-17559).

## Local verification

```bash
uv sync --locked
uv run python scripts/verify_migrations.py
```

The verification fails when the revision graph has anything other than one head, then upgrades a temporary SQLite database to that head and downgrades it back to the base.
