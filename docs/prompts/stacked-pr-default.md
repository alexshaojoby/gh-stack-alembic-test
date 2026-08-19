# Coding-agent prompt: default stacked PR workflow

Copy the prompt below into a coding-agent harness's repository instructions. Install the official GitHub skill where the harness supports the Agent Skills specification:

```bash
gh extension install github/gh-stack
gh skill install github/gh-stack gh-stack --agent <agent> --scope project
```

## Prompt

```text
Use GitHub stacked pull requests as the default delivery workflow when a change contains two or more dependent layers that can be reviewed independently. Keep a small, cohesive change in one normal PR. Never combine unrelated work into one stack; use separate stacks instead.

Before implementation:
1. Read repository instructions and the installed gh-stack skill.
2. Identify the issue or ticket and required PR-title format.
3. Confirm that the working tree is clean and update the trunk.
4. Check GitHub CLI >= 2.90, Git >= 2.20, authentication, same-repository push access, and the github/gh-stack extension.
5. Plan the stack bottom-up. Foundational schema, types, and APIs belong below dependent consumers, UI, integration tests, and documentation.
6. Obtain explicit authorization before any push, PR creation/update, or merge.

Create and manage stacks non-interactively:
- gh stack init <bottom-branch>
- gh stack add <next-branch>
- git add <intentional-files> && git commit -m "<valid PR title>"
- gh stack submit --auto --open
- gh stack view --json

Always provide branch arguments to init, add, and checkout. Always use --auto with submit and --json with view. Use commit subjects that satisfy the repository's PR-title policy because submit --auto derives titles from commits.

When changing a lower layer:
1. gh stack checkout <branch>
2. Make and commit the change on that layer.
3. gh stack rebase --upstack
4. Resolve conflicts, stage files, and run gh stack rebase --continue, or abort with gh stack rebase --abort.
5. Re-run validation across every affected layer.
6. gh stack push

For Alembic changes, treat the PR stack and migration graph as separate systems:
- Inspect alembic heads and history before creating a migration.
- A dependent upper migration must name the lower migration in down_revision.
- Require one Alembic head unless the repository explicitly documents multiple long-lived heads.
- A Git rebase does not rewrite revision or down_revision.
- Independent sibling migrations may be valid; reconcile them with an Alembic merge revision when one-head deployment tooling requires it.
- Never rewrite a revision that may already exist in a shared or deployed environment merely to make the graph linear.
- Validate clean upgrade, supported upgrades from deployed revisions, graph shape, and downgrade policy.

Before submission and after every rebase, run the repository's lint, format, type, test, migration-head, upgrade, and downgrade checks. Inspect gh stack view --json and verify each PR base points to the layer below it.

Use gh stack merge <stack-or-pr> --yes with the repository's merge method. Do not use gh pr merge for a recognized stack. Do not merge without explicit authorization and passing required checks.

Report the stack from bottom to top with branch names, PR URLs, migration revisions, validation results, unresolved risks, and whether remote preview behavior was directly observed or only inferred from documentation.
```

This default does not serialize separate feature stacks. Teams that require one linear Alembic history still need a CI head check and a policy for merge revisions.
