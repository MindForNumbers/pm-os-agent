# Loop Spec: Cortex PM Chief-of-Staff Agent

> Module 2 · Loop Engineering, ★ Deliverable 2
>
> ✅ **What this validates:** the agent knows when to run and when to stop, by the end you'll have proven a one-page Loop Spec with a trigger, a definition of "done," and explicit stop conditions.
>
> Your one-page blueprint for how the work you handed to the agent (M1) actually *runs*.
> An agent is just a prompt that fires itself, this spec says when it fires, what "done" means, and what it needs to do the job. Living document; refine as the course progresses.

## 1. Trigger & loop type

**Chosen type:** cron, daily at 7 AM, with the job varying by day.

- **Every day (7 AM):** risk check. Pull project state + activity and flag at-risk items, so a Sev-1 never waits a week.
- **Mondays (7 AM):** the risk check, plus draft the weekly leadership update and propose next sprint's stories.

**Why:** Status work runs on a predictable rhythm. A daily 7 AM run means risks are flagged before my day starts, and the weekly update is ready before my Monday VP sync. Nothing in Cortex's job needs a real-time reaction.

**Ruled out:**
- **Heartbeat:** checking continuously adds cost, and nothing changes fast enough to need it.
- **Hook:** event triggers would fire on every completed action, which means too many runs and drafts. (Future: a hook filtered to high-signal events like a Sev-1 or a new PRD.)
- **Goal:** Cortex's job ends at a draft I approve, not when it decides it's "done."

**Double-run protection:** one run per project per day. A run that finishes writes today's date as a marker. Any later run that sees today's marker exits without drafting or queuing stories. A run that failed doesn't write the marker, so a retry can still finish the job.

**Manual override (`--force`):** human-only. It ignores today's marker so a fresh run can go (e.g. after fixing bad data), logs who ran it and why, and still stops at my approval checkpoint.

## 2. Goal / definition of done

"Done" means **ready for me, not delivered**. Cortex never sends, posts, or commits anything (M1 #8a HITL, #8b Above). Each part can be checked.

- **Daily:** the risk check ran on fresh data; every at-risk item is flagged, along with the critic's "possibly missed" list; the result is queued for my review; today's marker is written.
  - **Quiet day:** counts only if **both** Cortex's flags and the critic's "possibly missed" list are empty. Then it logs "no flags," writes the marker, and doesn't ping me. Otherwise the missed-flag guardrail I designed in M1 switches off exactly when it matters.
- **Monday:** everything in Daily, plus the weekly update is drafted, has passed the critic, and is saved for my review, with up to 10 stories queued for approval. Today's marker is written.

Not a goal loop, so no self-validation step: the independent critic grades the output, not Cortex.

## 3. Stop conditions

| Condition | What it looks like | What happens |
|---|---|---|
| **Success** | Verifiable, not self-reported: the critic returned `pass`, outputs are on disk (Daily: flags + "possibly missed" list, or the quiet-day log; Monday: also the draft), and stories show `queued_for_approval`. The model saying "DONE" isn't proof, it's Cortex grading itself. | Halt at my HITL checkpoint. Write today's marker **last**, only after everything is saved, so a crash mid-run still allows a retry. |
| **Stuck / give up** | Any of: (1) a tool call fails 3× in a row; (2) iteration cap hit, `CORTEX_MAX_ITERATIONS=8`; (3) cost cap hit, `CORTEX_COST_CAP_USD=0.50`; (4) no progress, meaning 2 iterations with no new tool result or output. | Stop, log the reason, **don't** write the marker, and **ping me**. A silent give-up on the daily run looks exactly like a quiet day. Skipping the marker means a retry or `--force` can still finish. |
| **Escalate to human** | Any of: (1) the critic rejects the draft 2× (revision cap, `CORTEX_MAX_REVISIONS=2`) → M1 #3; (2) the proposed status would change color vs. last approved update → #4 Above; (3) an open Sev-1 or launch hold → #6 Above; (4) a confidential/embargoed project (e.g. Orbit) is in scope → #8b Above; (5) a story fails the PRD check or would exceed the cap of 10 → #7 HITL; (6) a possible prompt injection in the brief. | Stop at the HITL checkpoint and ping me with one `ESCALATE:` line saying why, plus whatever was safely finished (e.g. the draft saved, marked "needs your call"). **Write the marker**: escalate means the run worked and handed me a decision, so a rerun would just re-ping me. `--force` still covers a fresh run after I decide. |

**Build status** (spec vs. `00-build/agent.py`):
- **Enforced in code:** stuck triggers 1–4 (tool fails 3×, iteration cap, cost cap, no progress); escalate on revision cap and on a status color change vs. the last approved update (a draft with no `STATUS:` line also escalates, so the check can't be skipped); the per-project daily marker + human-only `--force` (logged who/why/when); the story-batch cap of 10 (`tools.py`).
- **Enforced by prompt + critic; code enforcement in M5:** Sev-1 / launch hold, confidential/embargoed project, story fails the PRD check, prompt injection.
- **Designed, not yet built:** daily vs. Monday modes (every run today is Monday mode); pings (stubbed in the trace as `PING -> owner (not wired)`, on stuck and escalate); the critic's "possibly missed" list (so the quiet-day rule can't run yet).

## 4. State

**Scope: per project. Nothing is shared across projects.** Per-project scope prevents cross-project leaks by design, not by a prompt rule, and matches my M1 memory row.

Each project (e.g. P-NORTH) keeps its own:
- **Run marker:** date of the last successful or escalated run, plus the `--force` log (who, why, when).
- **Last approved update:** status color, metrics, date (drives the color-change escalation and the baselines).
- **Run log:** each run's outcome (success · quiet · stuck · escalated) and reason.
- **My decisions:** overrides, rejected stories with reasons, and the missed-flag log (M1 learning loop).

**Shared sources, not state:** team norms and the roadmap are read fresh each run, never stored.
**Never stored:** confidential content (M1 rule). Raw pulls and unapproved drafts are purged after each run.

## 5. The five things a loop can lean on

_`state` is always-on. `connectors` only if you already have one wired (e.g. a Jira key or Google MCP), otherwise just note it as a plan. `skills`, `subagents`, `work tree` scale with autonomy; "not needed yet, because…" is a valid answer._

| Component | For Cortex |
|---|---|
| **Work tree** (isolated workspace per run, a git worktree) | Not needed yet, because Cortex doesn't edit code or shared files; it reads data and writes drafts to `run-output/`, per project. Revisit if it ever edits shared files. |
| **Skills** (reusable capabilities) | Not needed yet, because there's only one job and format so far. Plan: a "weekly update format" skill once a second project or team reuses it. |
| **Plugins / connectors** (tools & access, optional if you don't have one yet) | **Plan, not wired** (today's tools read mock fixtures). Read-only by default: Jira/GitHub for project + activity; Google Docs/Drive (MCP) or Confluence for past updates, roadmap, norms. Only two writes, both through my approval: Jira approval queue for proposed stories (never creates issues); Slack team channel for `post_team_update`. **No company-wide posting connector, ever.** Read-only access means the line holds even if a prompt rule fails: if Cortex gets tricked or makes a mistake, it can't change anything. Pings (stuck, escalate, flagged days) go to me only, via Slack DM. They're notifications to the owner, not content posted for others, so they don't add a write path, enforced by scope: the ping integration can only reach my DM (separate token or webhook), not channels. |
| **Subagents** (independent check when the loop can't grade itself) | Partly there: the critic (`00-build/critic.py`) already acts as an independent check, because the loop can't grade itself. Next job: the "possibly missed" list. Full design → M3 `orchestration-map.md`. |
| **State tracking** | Per project, as in §4. |

> Context plan (M4) and the hand-off to bounds & evals (M5) come in later modules, you'll add them to their own deliverables then, not here.

## Link to live loop

[`00-build/agent.py`](../00-build/agent.py)
