# GitHub stacked PRs with Alembic

This repository tests GitHub's stacked pull requests public preview against a linear Alembic migration workflow.

Tracked in [FACT-17559](https://linear.app/joby/issue/FACT-17559).

## Local verification

```bash
uv sync --locked
uv run python scripts/verify_migrations.py
```

The verification fails when the revision graph has anything other than one head, then upgrades a temporary SQLite database to that head and downgrades it back to the base.

## Finding

Stacked PRs preserve the order of one intentional chain of dependent migrations, but they do not serialize independent feature branches or repair Alembic `down_revision` values. Use CI to detect unexpected heads and an Alembic merge revision to reconcile already-independent migrations.

## Documentation

- [Tested tutorial](docs/stacked-prs-alembic-tutorial.md)
- [Research brief](docs/research/github-stacked-prs-alembic.md)
- [Decision record](docs/adr/0001-use-stacked-prs-only-for-dependent-migrations.md)
- [Coding-agent prompt](docs/prompts/stacked-pr-default.md)
- [Official GitHub `gh-stack` skill](.pi/skills/gh-stack/SKILL.md)
