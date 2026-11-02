# Prototype: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 1, the working agent demo
>
> ✅ **What this validates:** the agent actually runs end to end, by the end you'll have proven it with real screenshots of your Cortex across the six required moments (M2 to M6).

## What it does

_One paragraph: the agent in action, end to end._

## How you built it

- **Coding agent:** _which one you directed (Claude Code / Cursor / Codex)_
- **Model + bounds:** _model used, max iterations, cost cap, queue cap_
- **Repo / config:** _path to your build in `00-build/`_
- **Live link:** _[shareable URL, optional bonus]_

## Screenshots (required, collected M2 to M6)

Real screenshots of *your* Cortex running. These are the `00-build/CORTEX-ANATOMY.md` set and they are required, a link alone is not enough.

| # | Screenshot | What it shows | From |
|---|---|---|---|
| 1 | [happy 1](screenshots/m2-happy-1-tools-and-draft.png) · [2](screenshots/m2-happy-2-critic-pass.png) · [3](screenshots/m2-happy-3-hitl-checkpoint.png) | happy-path run: a real drafted update + the HITL checkpoint (queued, not posted) | M2 |
| 2 | _[img]_ | the critic rejecting a bad draft (revise/block) | M3 |
| 3 | _[img]_ | a grounded update citing pulled activity + a caught hallucination | M4 |
| 4 | _[img]_ | jailbreak refused + escalated | M5 |
| 5 | _[img]_ | an iteration/cost/queue bound halting a runaway | M5 |
| 6 | _[img]_ | end-to-end run | M6 |

### M2 captures

![M2 happy 1](screenshots/m2-happy-1-tools-and-draft.png)
Happy path (P-NORTH): Cortex pulls data with five read tools, queues 4 stories for approval, and drafts the update ending in `STATUS: Green`.

![M2 happy 2](screenshots/m2-happy-2-critic-pass.png)
The draft's "data relied on" and story caveats, then the independent critic's `pass` with its reasons.

![M2 happy 3](screenshots/m2-happy-3-hitl-checkpoint.png)
HITL checkpoint: the validator-approved draft is saved for review and nothing is posted (~$0.0033); below it, a `--force` run of missing-data is logged with who and why.

![M2 missing data 1](screenshots/m2-missing-data-1-tools.png)
Missing data (P-HALO): `get_project` and `get_activity` return `project_not_found`; Cortex refuses to invent a GA date and ends with an `ESCALATE:` line.

![M2 missing data 2](screenshots/m2-missing-data-2-escalate.png)
The critic passes the escalation; the run exits as ESCALATE, holds the draft ("needs your call"), and fires the ping stub.

## How to run it

_Minimal steps for someone to reproduce the demo (env vars, and the command or the coding-agent prompt you used)._
