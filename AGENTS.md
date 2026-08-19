# Repository agent instructions

## Default delivery workflow

Use the repository's `gh-stack` skill for implementation work that has two or more dependent, independently reviewable layers. Keep a small single-layer change in one normal branch and PR. Use separate stacks for unrelated changes.

Before writing code:

1. Associate the work with a ticket and follow the required PR-title format.
2. Update the trunk with a clean working tree.
3. Inspect the current Alembic heads.
4. Plan stack layers from foundational to dependent.
5. Confirm authorization before pushing branches or creating, updating, or merging PRs.

Run every `gh stack` command non-interactively:

```bash
gh stack init <bottom-branch>
gh stack add <next-branch>
gh stack submit --auto --open
gh stack view --json
```

Use commit subjects that are valid PR titles because `gh stack submit --auto` derives titles from commits. For this repository, use `[FACT-xxxxx] Description`.

When a lower layer changes, check out that branch, commit there, run `gh stack rebase --upstack`, and push the stack. Do not place a lower-layer fix in an upper branch.

## Alembic migration policy

GitHub's stack is a Git and PR chain, not the Alembic revision graph.

- Generate each dependent migration from the head provided by its lower stack layer.
- Verify that `down_revision` names the intended parent.
- Require exactly one Alembic head unless a documented design intentionally uses multiple heads.
- Do not assume a successful Git rebase repaired migration ancestry.
- If independent branches created sibling revisions, preserve revisions that may have reached a shared environment and add an Alembic merge revision.
- Test graph shape, clean upgrade, and downgrade before submitting and after every restack.

Run:

```bash
uv run alembic heads --verbose
uv run alembic history
uv run python scripts/verify_migrations.py
```

Use `gh stack merge --yes` rather than `gh pr merge` for a recognized stack. Merge only after all required checks pass and the user has authorized the remote operation.
