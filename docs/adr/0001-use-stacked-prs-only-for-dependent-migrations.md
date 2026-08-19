---
status: accepted
---

# Use stacked PRs only for dependent migrations

Use GitHub stacked pull requests when migration changes form one intentional dependency chain, because GitHub can review and land that chain from the bottom up. Do not use a stack as a global migration lock: independent work may keep separate PRs or stacks, CI must reject unexpected Alembic heads, and already-independent heads should normally be reconciled with an Alembic merge revision rather than by rewriting revisions that may have reached a shared environment.
