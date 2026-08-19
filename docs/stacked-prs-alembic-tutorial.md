# Tutorial: GitHub stacked pull requests with Alembic

## Decision

Use GitHub stacked PRs for migrations that form one intentional dependency chain. Do not use them as a global queue for unrelated migrations. GitHub orders Git branches and PRs; Alembic independently orders migration scripts through `revision` and `down_revision`.

See [ADR 0001](adr/0001-use-stacked-prs-only-for-dependent-migrations.md) and the [research brief](research/github-stacked-prs-alembic.md).

## Prerequisites

- GitHub CLI 2.90 or newer
- Git 2.20 or newer
- Same-repository push access
- A clean working tree
- An existing Alembic environment

```bash
gh --version
git --version
gh auth status
gh extension install github/gh-stack
git config rerere.enabled true
git config remote.pushDefault origin
```

GitHub's public preview requires no repository enablement. All branches in a stack must be in the same repository.

## Choose whether to create a stack

Create one stack when each upper layer depends on the layer below it:

```text
main
└── schema-a
    └── schema-b
        └── application-and-docs
```

Use separate PRs or stacks for independent features. If two independent migrations use the same parent, Alembic creates two heads; that is not a Git conflict and stacked PRs do not repair it.

## Establish the migration baseline

Start from the latest trunk and inspect the Alembic graph:

```bash
git checkout main
git pull --ff-only
uv sync --locked
uv run alembic heads --verbose
uv run alembic history
uv run python scripts/verify_migrations.py
```

Record the current head. In this repository, the trunk head is `0001`.

## Create the bottom migration layer

```bash
gh stack init fact-17559-add-projects-migration
```

Create the migration and verify that its parent is the trunk head:

```python
revision = "0002"
down_revision = "0001"
```

Run migration verification and commit with a PR-ready subject:

```bash
uv run python scripts/verify_migrations.py
git add migrations/versions/0002_create_projects.py
git commit -m "[FACT-17559] Add projects migration"
```

## Create a dependent upper layer

```bash
gh stack add fact-17559-add-tasks-migration
```

The upper migration must point to the revision introduced below it:

```python
revision = "0003"
down_revision = "0002"
```

```bash
uv run alembic heads --verbose
uv run alembic history
uv run python scripts/verify_migrations.py
git add migrations/versions/0003_create_tasks.py
git commit -m "[FACT-17559] Add tasks migration"
```

The expected graph is:

```text
0001 <- 0002 <- 0003
```

## Add further review layers

Create another branch for a distinct dependent concern, such as integration tests or documentation:

```bash
gh stack add fact-17559-document-stacked-pr-workflow
git add AGENTS.md docs .pi/skills/gh-stack README.md
git commit -m "[FACT-17559] Document stacked PR workflow"
```

## Submit without interactive prompts

```bash
gh stack submit --auto --open
gh stack view --json
```

`submit --auto` pushes every active branch, creates or updates the PRs, and links them as a GitHub stack. A single commit's subject becomes its PR title, so create commits with the required ticket prefix.

Verify the returned data and GitHub UI:

- The bottom PR targets `main`.
- Every upper PR targets the branch immediately below it.
- GitHub displays one stack containing every PR.
- Each PR shows only its layer's diff.
- Required checks run for every layer.

## Change a lower layer

Never put a lower-layer correction into an upper PR. Navigate down, commit the change there, and cascade it upward:

```bash
gh stack checkout fact-17559-add-projects-migration
git add <files>
git commit -m "[FACT-17559] Refine projects migration"
gh stack rebase --upstack --remote origin
gh stack push --remote origin
gh stack top
uv run python scripts/verify_migrations.py
```

A successful Git rebase only replays commits. Reinspect `down_revision` and rerun Alembic checks after every restack.

If conflicts occur:

```bash
git add <resolved-files>
gh stack rebase --continue
```

Abort when the conflict cannot be resolved safely:

```bash
gh stack rebase --abort
```

## Synchronize after remote changes

```bash
gh stack sync --remote origin
gh stack view --json
```

Use `--prune` when merged local branches should be deleted without a prompt:

```bash
gh stack sync --remote origin --prune
```

## Merge

Merge the bottom PR alone or a contiguous prefix through a selected PR:

```bash
gh stack merge <pr-number> --yes --squash
```

Merge the complete active stack with:

```bash
gh stack merge --yes --squash
```

Do not use `gh pr merge` for a recognized stack. If the base uses a merge queue, GitHub queues the stack and chooses the configured merge method.

## Handle independent migrations

Suppose two engineers independently create these revisions:

```text
0002 <- 0003
     └- 0003b
```

Both files can merge without a textual conflict, but `alembic heads` reports two heads and `alembic upgrade head` is ambiguous. The repository check fails intentionally:

```text
Expected exactly one Alembic head, found: 0003, 0003b
```

When both revisions should remain valid, reconcile them with a merge revision:

```bash
uv run alembic merge -m "merge concurrent heads" heads
uv run alembic heads --verbose
uv run python scripts/verify_migrations.py
```

The generated merge revision has both heads in `down_revision`, restoring one head without deleting either history. Do not rewrite a revision that may already be present in a shared database.

## CI policy

Run migration checks for pull requests, merge-queue groups, and trunk pushes:

```yaml
on:
  merge_group:
  pull_request:
  push:
    branches:
      - main
```

The check in `scripts/verify_migrations.py` requires one script head, upgrades a clean temporary database to that head, verifies the recorded database revision, and downgrades to the base.

A one-head check does not prove that DDL is safe. Production repositories should also test upgrades from supported deployed revisions and operations involving shared tables or data.

## Live validation record

Repository: <https://github.com/alexshaojoby/gh-stack-alembic-test>

Local results:

- `0002` was verified as the sole head in the bottom migration layer.
- `0003` was verified as the sole head in the dependent layer.
- A temporary sibling `0003b` produced two heads and failed CI as expected.
- An Alembic merge revision restored one head and passed upgrade and downgrade verification.

Remote results on GitHub stack `#4`:

| Position | Pull request | Head branch | Initial base | Result |
| --- | --- | --- | --- | --- |
| Bottom | [#1 Add projects migration](https://github.com/alexshaojoby/gh-stack-alembic-test/pull/1) | `fact-17559-add-projects-migration` | `main` | Merged first with squash |
| Middle | [#2 Add tasks migration](https://github.com/alexshaojoby/gh-stack-alembic-test/pull/2) | `fact-17559-add-tasks-migration` | projects branch | Retargeted to `main`, then merged with #3 |
| Top | [#3 Document stacked PR workflow](https://github.com/alexshaojoby/gh-stack-alembic-test/pull/3) | `fact-17559-document-stacked-pr-workflow` | tasks branch | Merged with #2 |

Observed behavior:

- `gh stack submit --auto --open` created three ready-for-review PRs and linked them as stack `#4`.
- The Stacks API and `gh stack view --json` returned the expected bottom-to-top branch chain.
- GitHub ran the `pull_request` migration workflow for all three PRs; every `verify` job passed.
- A new commit on the bottom layer followed by `gh stack rebase --upstack` changed both upper commit IDs while preserving a linear stack and `needsRebase: false`.
- `gh stack merge 1 --yes --squash` merged only #1. GitHub automatically retargeted #2 from the projects branch to `main` and rebased both remaining remote branches.
- `gh stack sync --remote origin` fast-forwarded local `main`, skipped merged #1, rebased #2 and #3, pushed them, and retained the same GitHub stack.
- `gh stack merge 3 --yes --squash` merged the contiguous #2 and #3 group into `main` in one operation.
- The final push workflow passed, and `gh stack sync --remote origin --prune` removed all three merged local branches.

## Agent adoption

- Repository default instructions: [`AGENTS.md`](../AGENTS.md)
- Copyable harness prompt: [`docs/prompts/stacked-pr-default.md`](prompts/stacked-pr-default.md)
- Official project skill: [`.pi/skills/gh-stack/SKILL.md`](../.pi/skills/gh-stack/SKILL.md)
