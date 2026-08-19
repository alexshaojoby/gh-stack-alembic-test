# Research: GitHub stacked pull requests and concurrent Alembic migrations

## Summary

GitHub's native stacked pull requests feature is currently a **public preview** that requires no repository or organization enablement. It is designed for a single, linear chain of dependent branches and PRs in one repository; it orders review and landing and automates cascading Git rebases, but it does **not** coordinate Alembic revision identifiers or repair Alembic's revision DAG when independent engineers create sibling migrations concurrently.

For Alembic, stacks are useful when migrations are intentionally dependent and are authored as ordered layers in the same stack. For truly independent concurrent work, use Alembic's native multiple-head/merge-revision model plus CI that detects unexpected heads; do not treat GitHub's stack order as a database migration lock or serialization guarantee.

## Findings

### 1. Preview status, availability, and prerequisites

1. **No enrollment switch is required.** GitHub says stacked PRs are in public preview, subject to change, and require “no setup or enablement”; a team that already uses pull requests can create a stack. The launch announcement says the preview rolled out to all repositories, while merge-queue support rolled out progressively. Confirm the controls appear in this specific repository before planning a live test because rollout language does not guarantee that every account saw every control simultaneously. [GitHub rollout tutorial](https://docs.github.com/en/pull-requests/tutorials/roll-out-stacked-prs) · [GitHub changelog](https://github.blog/changelog/2026-07-30-stacked-pull-requests-are-now-in-public-preview/)
2. **Repository constraints:** every stack branch must be in the same repository; cross-fork stacks are unsupported. GitHub Desktop is unsupported. The feature is available through github.com, GitHub CLI, GitHub Mobile, REST/webhooks, and read-only GraphQL stack queries. This matters for contributors who normally push only to forks. [Stack rules](https://docs.github.com/en/pull-requests/reference/stacked-pull-requests) · [API and webhook reference](https://docs.github.com/en/pull-requests/reference/stacked-pull-requests-apis-and-webhooks)
3. **CLI prerequisites:** the quickstart requires GitHub CLI `gh` 2.90.0 or later, Git 2.20 or later, `gh auth login`, and a repository the user can push to. Install the official extension with `gh extension install github/gh-stack`. (The command-reference page contains a looser “gh 2.0 or later” statement, but the task should follow the more specific quickstart prerequisite of 2.90.0.) [Quickstart](https://docs.github.com/en/pull-requests/get-started/stacked-prs-quickstart)

### 2. What a GitHub stack orders

A GitHub stack is a **linear Git/PR chain**, for example:

```text
main <- PR1 branch <- PR2 branch <- PR3 branch
```

Each PR targets the branch immediately below it, while GitHub evaluates reviews, required checks, CODEOWNERS, code scanning, and Actions as though each PR targeted the stack trunk (usually `main`). Every PR therefore has a focused layer diff, but trunk-targeted Actions can run once per PR. [Stack rules](https://docs.github.com/en/pull-requests/reference/stacked-pull-requests) · [CI guidance](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/optimizing-ci-for-stacked-pull-requests)

Before merging a layer, that PR and every lower PR must satisfy the trunk's protections, and the stack must have fully linear branch history. Merges proceed bottom-up: GitHub can merge the lowest PR alone or a contiguous prefix through a selected higher PR, but cannot merge a middle PR without its lower dependencies. Merge commit, squash, and rebase methods are supported. Auto-merge is not supported; merge queues are supported, subject to the preview rollout. [Merge documentation](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-stacked-pull-requests) · [Stack rules](https://docs.github.com/en/pull-requests/reference/stacked-pull-requests)

**This solves (a), ordering dependent changes:** if migration B truly depends on migration A, put A in the lower branch/PR and generate or author B in the next branch with `down_revision` pointing to A. Reviews can proceed independently, but B cannot land ahead of A.

It does not represent a branching dependency graph: a stack is one ordered chain, not a general DAG, and cross-fork or sibling-shaped stacks are unsupported. [GitHub rollout tutorial](https://docs.github.com/en/pull-requests/tutorials/roll-out-stacked-prs)

### 3. Restacking and rebasing are Git operations, not Alembic graph operations

**This solves (b), much of the mechanical rebasing/restacking:** after the bottom PR merges, GitHub automatically rebases and retargets the next unmerged PR to the stack base. If the trunk moves or a lower branch changes, users can select **Rebase stack** in the merge box, or run:

```shell
gh stack rebase
gh stack push
```

For a change made on a lower layer, use `gh stack down` (or `gh stack checkout BRANCH`), commit, then `gh stack rebase --upstack`, `gh stack push`, and `gh stack top`. `gh stack sync --prune` fetches, fast-forwards the trunk, rebases remaining branches, pushes, synchronizes PR state, and optionally deletes merged local branches. Server-side rebases force-push and retrigger CI but produce unsigned commits; repositories requiring signed commits should rebase locally. Conflicts still require human resolution with `gh stack rebase --continue` or abort with `--abort`. [Managing stacks](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/managing-stacked-pull-requests)

Crucially, a cascading Git rebase only replays commits. It does not understand the `revision`, `down_revision`, `branch_labels`, or `depends_on` values inside Alembic Python files. Two independently added migration files normally do not create a textual Git conflict, so a successful restack can still leave two Alembic heads.

### 4. Exact supported creation, UI, and CLI workflow

**Minimal CLI workflow:** [Quickstart](https://docs.github.com/en/pull-requests/get-started/stacked-prs-quickstart)

```shell
gh extension install github/gh-stack
gh auth login
gh stack init first-layer
# edit, git add, git commit
gh stack add second-layer
# edit, git add, git commit
gh stack submit
gh stack view
```

`gh stack push` can push before `submit`; `submit` itself pushes branches, creates or updates PRs, and links them. `gh stack init --base release first-layer` selects a non-default trunk. `gh stack add -Am "message"` can stage, commit, and create the next branch. [Quickstart](https://docs.github.com/en/pull-requests/get-started/stacked-prs-quickstart) · [CLI reference](https://docs.github.com/en/pull-requests/reference/stacked-prs-cli-commands)

**Website workflow:** create the bottom PR against `main` (or another trunk); create the next PR with the lower PR's head branch as its base; select **Create stack**. GitHub can show a recommendation banner for an existing eligible chain. The PR UI then shows a numbered stack icon and stack map. **Add to stack** appends a PR to the top. **Rebase stack** performs the server-side cascading rebase. The merge box merges the bottom layer or a contiguous prefix. The website can unstack open/draft/closed PRs, but merged or queued PRs remain in the stack. [Creating stacks](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-stacked-pull-requests) · [Managing stacks](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/managing-stacked-pull-requests) · [Merging stacks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-stacked-pull-requests)

**Documented `gh stack` command surface:**

- Create/manage: `init`, `add`, `view`, `checkout`, `modify`, `unstack` (`delete` alias).
- Remote operations: `submit`, `sync`, `rebase`, `push`, `link`, `merge`.
- Navigate: `switch`, `up`, `down`, `top`, `bottom`, `trunk`.
- Utilities: `alias`, `feedback`.

`gh stack modify` can drop, fold, insert, reorder, or rename layers in its interactive UI, then `gh stack submit` republishes the structure. `gh stack link` can link existing PRs or branches without local stack tracking. `gh stack merge [STACK_OR_PR]` merges through a selected PR; `--squash`, `--rebase`, and `--merge` select the method when no merge queue controls it. [Complete CLI reference](https://docs.github.com/en/pull-requests/reference/stacked-prs-cli-commands)

Programmatic merging must use GitHub's asynchronous merge API; legacy synchronous endpoints and mutations cannot merge stacks. REST can read/create/extend/dissolve stacks, GraphQL stack support is read-only, and pull-request webhook payloads expose stack metadata. [API and webhook reference](https://docs.github.com/en/pull-requests/reference/stacked-pull-requests-apis-and-webhooks)

### 5. Alembic's DAG is separate from GitHub's PR stack

**This is (c), Alembic's actual migration model:** Alembic orders scripts from declarations inside migration files. `down_revision` points to the parent revision; `down_revision = None` is a root. When two independently created migrations name the same parent, Alembic forms a branch point and two heads. This occurs naturally when divergent source trees are merged. [Alembic branch documentation](https://alembic.sqlalchemy.org/en/latest/branches.html) · [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

With multiple heads:

- `alembic heads` lists them.
- `alembic upgrade head` is ambiguous and fails.
- `alembic upgrade heads` deliberately applies all heads and can leave multiple rows in `alembic_version`.
- A specific revision or `<branchname>@head` selects one branch.
- `alembic revision` requires `--head` when multiple heads exist.

For ordinary source-merge concurrency, Alembic's documented reconciliation is a merge revision:

```shell
alembic merge -m "merge concurrent heads" heads
```

The resulting revision has a tuple such as `down_revision = ("head_a", "head_b")`, creating a diamond and restoring a single head. Reconciliation operations, if any, can go in that merge migration. `branch_labels` support intentionally long-lived named branches. `depends_on` expresses a cross-branch prerequisite while retaining semantically independent lineages; it is not the same as merging those lineages. [Alembic branch documentation](https://alembic.sqlalchemy.org/en/latest/branches.html)

### 6. Concurrent-engineer scenarios

| Scenario | Do stacked PRs help? | Required Alembic handling |
| --- | --- | --- |
| One feature has migration B that depends on A | **Yes.** Put A below B in one stack; bottom-up landing preserves intended PR order. | Generate B from A so B's `down_revision` is A; test upgrade/downgrade across the chain. |
| A lower PR merges and upper dependent work remains | **Yes, mechanically.** Automatic retarget/rebase or `gh stack sync`/`rebase` updates Git history. | Verify migration contents and `down_revision` after rebase; GitHub does not rewrite them. |
| Two engineers independently branch from the same `main` head and each add a migration | **No coordination guarantee.** Their separate stacks/PRs can both be valid against the same trunk and use the same parent. | After coexistence, either intentionally retain multiple heads and use `heads`/labels, or add an Alembic merge revision. Enforce the chosen policy in CI. |
| Two independent migrations touch the same table/object | **No semantic safety guarantee.** Git may report no conflict even if DDL order or data assumptions conflict. | Exercise both upgrade orders where relevant, test from production-like prior revisions, and write reconciliation/merge migration logic if needed. |
| Busy trunk with merge queue | **Partially.** Queue checks combined Git changes and orders stack layers, but cannot infer or modify Alembic ancestry. | Run a required single-head/DAG and database-upgrade check in the merge queue's `merge_group` workflow as well as `pull_request`. |

### 7. Repository test evidence

This repository now contains an Alembic environment, a single-head verification script, and CI for `pull_request`, `merge_group`, and pushes to `main`. The test stack is intentionally linear:

```text
0001 create accounts <- 0002 create projects <- 0003 create tasks
```

Local execution established the following:

1. Each stack layer had exactly one head and upgraded a clean temporary SQLite database before downgrading to the base.
2. Adding a temporary sibling revision `0003b` with the same `down_revision = "0002"` produced heads `0003` and `0003b`.
3. The repository's verification script rejected that graph with `Expected exactly one Alembic head`.
4. `alembic merge -m "merge concurrent heads" heads` restored one head, after which the clean upgrade and downgrade verification passed.

The remote stack lifecycle, PR chain, and CI observations are recorded in the [tested workflow tutorial](/docs/stacked-prs-alembic-tutorial.md). A successful remote demonstration shows that GitHub orders one declared dependency chain; it does not prove that separate stacks cannot create sibling Alembic heads.

## Recommendations

1. **Use stacks only for genuine dependency chains.** For a feature whose migrations are sequential, create the first migration in the bottom layer and subsequent migrations above it. Do not place unrelated engineers' work into one shared stack merely to impose a global migration order.
2. **Make Alembic DAG policy explicit.** If production tooling expects `alembic upgrade head`, require exactly one script head. If multiple long-lived heads are intentional, document labels, use `upgrade heads` or targeted branches deliberately, and test that deployment tooling supports multiple `alembic_version` rows.
3. **Add a required DAG check.** A robust single-head check can load the Alembic config and call `ScriptDirectory.get_current_head()`; do not rely on Git conflict detection. Run it on both `pull_request` and `merge_group` when merge queue is enabled.
4. **Prefer a merge revision for already-independent work.** When two valid migration PRs were created independently from the same parent, preserve both immutable revision IDs and add `alembic merge ...` after both are present. Only rewrite an unmerged migration's `down_revision` to serialize it when that ordering is intentional and the migration has not escaped into deployed/shared environments.
5. **Test database semantics, not just graph shape.** Validate clean upgrade, upgrade from each supported deployed revision/head, downgrade policy, and incompatible operations on shared tables. A one-head graph can still contain unsafe DDL.
6. **Pilot remote stack behavior separately.** Once authorized, use two dependent, non-production test changes in this repository; verify required checks per layer, lower-layer changes plus cascading rebase, bottom-only merge and upper retarget, and (if configured) `merge_group` migration checks. Do not claim that this test proves concurrency serialization.
7. **Pin/document preview tooling.** Record `gh >= 2.90.0`, Git `>= 2.20`, installation of `github/gh-stack`, same-repository push access, and the public-preview/change-risk caveat in contributor documentation before adoption.

## Sources

### Kept (primary)

- [Stacked pull requests are now in public preview](https://github.blog/changelog/2026-07-30-stacked-pull-requests-are-now-in-public-preview/) — official launch status and rollout.
- [Roll out stacked pull requests to your organization](https://docs.github.com/en/pull-requests/tutorials/roll-out-stacked-prs) — official no-enablement statement, fit constraints, and automation guidance.
- [Stacked pull requests reference](https://docs.github.com/en/pull-requests/reference/stacked-pull-requests) — canonical rules, protections, merge methods, limitations, and rebasing.
- [Quickstart for stacked pull requests](https://docs.github.com/en/pull-requests/get-started/stacked-prs-quickstart) — prerequisites and minimal workflow.
- [Creating stacked pull requests](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-stacked-pull-requests) — CLI and website creation UI.
- [Managing stacked pull requests](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/managing-stacked-pull-requests) — cascading rebase, restacking, synchronization, and conflicts.
- [Merging stacked pull requests](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-stacked-pull-requests) — bottom-up/contiguous merge behavior and auto-merge limitation.
- [Stacked pull requests CLI commands](https://docs.github.com/en/pull-requests/reference/stacked-prs-cli-commands) — complete official extension command surface.
- [Stacked pull requests APIs and webhooks](https://docs.github.com/en/pull-requests/reference/stacked-pull-requests-apis-and-webhooks) — REST, GraphQL, webhook, and asynchronous merge constraints.
- [Optimizing CI for stacked pull requests](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/optimizing-ci-for-stacked-pull-requests) — event semantics and stack metadata.
- [Alembic: Working with Branches](https://alembic.sqlalchemy.org/en/latest/branches.html) — official branch/head/merge/label/dependency behavior.
- [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) — official explanation that `down_revision` determines order.
- [Alembic Script Directory API](https://alembic.sqlalchemy.org/en/latest/api/script.html) — official API behavior for head inspection.

### Dropped

- Third-party stacked-PR products, blog posts, and issue commentary — excluded because official GitHub documentation now describes the native preview directly.
- Search-result snippets pointing to older Alembic documentation versions — excluded where the current official `latest` pages covered the same behavior.

## Gaps and residual risks

- The private test repository does not reproduce every organization's rulesets, CODEOWNERS, merge queue, signing requirements, or in-house merge automation.
- Public-preview behavior and command flags are explicitly subject to change. The GitHub quickstart and CLI reference currently disagree on the minimum `gh` version (2.90.0 versus 2.0); use the stricter 2.90.0 prerequisite.
- A single successful stack does not exercise races between independent stacks or prove global serialization of migration creation.
- Stacked PRs cannot guarantee DDL commutativity, safe deploy ordering across separate stacks, compatibility with already-deployed revisions, or the absence of Alembic multiple heads.
