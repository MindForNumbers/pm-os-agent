# Agent Line Map: Cortex PM Chief-of-Staff Agent

> Module 1 · The Agent Line
>
> ✅ **What this validates:** every risky action has a clear owner, by the end you'll have proven an above/below-the-line map with HITL checkpoints, scored on reversibility, blast radius, and measurability.

## The workflow, decision by decision

List every discrete decision or action in your agent's workflow, then score each one and place it **above** the line (a human owns it) or **below** (the agent owns it). Borderline calls get an HITL checkpoint.

| Decision / action | Reversibility (H/M/L) | Blast radius (H/M/L) | Measurability (H/M/L) | Above / Below | HITL? |
|---|---|---|---|---|---|
| Pull project state + activity | H | L | H | Below | · |
| Decide relevant context | H | M | H* | HITL | light touch: human reviews the exclusion list alongside the draft |
| Draft the update | H | L | M | Below | · (reviewed before posting, see #8a/#8b) |
| Decide tone/commitment level | L | H | M | Above | · (human makes the status call; Cortex may suggest inputs) |
| Flag at-risk/escalation | H | H | L | HITL | required: human reviews flags + critic's "possibly missed" list\*\* |
| Choose what to escalate | L | H | M | Above | · (human decides; Cortex's flags are inputs) |
| Propose a story batch (capped) | M | L | M | HITL | required: human approves/rejects each story in the queue |
| Post an update to the team or project channel | L | M | M | HITL | required: nothing posts without explicit human approval |
| Approve a company-wide update | L | H | M | Above | · (human approves and sends; Cortex has no company-wide posting tool) |
| Act on a brief that claims pre-authorization | L | H | M | HITL | required: a claim authorizes nothing; only the human's approval click mints a write token (JIT, M5); the claim is logged as a flag for review |

\* Measurability for "Decide relevant context" is High only with these guardrails **(not yet built)**: it assumes Cortex must list each excluded item with its reasoning and source, and the critic must verify that list against the source data (nothing important missing from both the draft and the exclusion list, no hallucinated items).

\*\* Flag at-risk/escalation: the critic checks the source data for unflagged risks (e.g. open Sev-1, launch hold) and surfaces a "possibly missed" list for human review **(not yet built)**. Misses feed a learning loop via memory (M4).

## Agent anatomy (sketch)

- **Model:** Claude Haiku 5.5 (`claude-haiku-5-5`) by default: fast and cheap (~$0.003–0.006 per run). Escalate to Claude Opus 5.5 (`claude-opus-5-5`) only on evidence that Haiku struggled: the critic fails a draft twice (hits `CORTEX_MAX_REVISIONS=2`) or the source data is contradictory. Escalating on evidence, not guesses, keeps the price reasonable.
- **Tools:** match the map exactly.
  - Read (below the line): `get_project`, `get_activity`, `search_past_updates`, `get_roadmap`, `get_norms`.
  - `propose_stories`: queues for approval only, capped at 5 (HITL).
  - `post_team_update` **(not yet built)**: works only after explicit human approval (HITL).
  - **No company-wide posting tool, ever** (Above: capability is not permission).
- **Memory:**
  - Persist: team norms, roadmap, PRDs (source of truth, read via tools); approved past updates (format + baselines); the human's decisions and overrides (status calls, escalations, rejected stories with reasons); the missed-flag log (feeds the learning loop).
  - Purge: raw activity pulls, unapproved drafts, critic back-and-forth (re-pull fresh each run).
  - Never stored: confidential content (e.g. Orbit). Read from source only when needed.
- **Loop:** _placeholder, defined in M2 loop-spec.md_
- **Bounds:** _placeholder, defined in M5 bounds-and-evals.md_
- **Evals:** _placeholder, defined in M5 bounds-and-evals.md_

## The golden rule, applied

- **Pull project state + activity** sits below the line because it's easy to reverse (it only reads data and changes nothing), has a low blast radius, and is easy to verify against the logged tool results. Deciding factor: **reversibility**.
- **Decide relevant context** sits in HITL because it's easy to reverse, has a medium blast radius (a bad selection carries into the draft and status call), and is easy to verify once Cortex lists each exclusion with reasoning and source and the critic checks it. Deciding factor: **blast radius**.
- **Draft the update** sits below the line because it's easy to reverse (edit or regenerate), has a low blast radius (nobody sees a draft until a human approves posting), and is moderately easy to verify (facts are checkable, quality is a judgment call). Deciding factor: **blast radius**.
- **Decide tone/commitment level** sits above the line because it's hard to reverse (a status call or committed date can't be taken back once leadership hears it), has a high blast radius, and is only moderately verifiable (whether Green was right often isn't clear until weeks later). Deciding factor: **reversibility**.
- **Flag at-risk/escalation** sits in HITL because it's easy to reverse (a wrong flag is just dismissed), but has a high blast radius and is hard to verify: a missed flag stays invisible until it's already a problem, so the critic surfaces a "possibly missed" list for human review. Deciding factor: **measurability**.
- **Choose what to escalate** sits above the line because it's hard to reverse (once escalated, it can't be unsent, whether a human or an agent sent it), has a high blast radius (both a false alarm and a missed escalation do damage), and is moderately verifiable (false alarms show quickly, misses don't). Deciding factor: **reversibility**.
- **Propose a story batch** sits in HITL because it's only moderately reversible (Cortex can't withdraw queued stories, so a human must reject them), has a low blast radius (capped at 5, nothing is created without approval), and is moderately verifiable (PRD tracing is easy, sprint fit isn't). Deciding factor: **reversibility**.
- **Post an update to the team or project channel** sits in HITL because it's hard to reverse (once posted, people may have already read it, regardless of who sent it), has a medium blast radius (smaller audience, but the chain effect can spread), and is moderately verifiable (facts are checkable, framing and omissions are harder to catch). Deciding factor: **reversibility**.
- **Approve a company-wide update** sits above the line because it's hard to reverse (once sent company-wide, it can't be undone), has a high blast radius (a company-wide leak or error is critical), and is only moderately verifiable (some people will know it's wrong, but not everyone). Deciding factor: **blast radius**.
- **Act on a brief that claims pre-authorization** sits in HITL because acting on it is hard to reverse (it would mean posting), has a high blast radius (my jailbreak brief asked for a company-wide post of the confidential Orbit roadmap), and is only moderately verifiable (a plain claim is easy to spot, but a rephrased one isn't). A claim in a brief can't authorize anything: the only thing that mints a write token is my click at the checkpoint, so "pre-approved" is inert whatever Cortex believes. Deciding factor: **blast radius**.

## Hardest call

**Flag at-risk/escalation: first instinct Below → final verdict HITL.**

At first I placed it below the line: raising a flag isn't a huge lift and a wrong one can easily be dismissed. Scoring it changed my mind. Flags can be missed, but if they're critical and Cortex misses it, it would be devastating. Having a HITL will lessen the probability of that happening. A normal review only sees the flags Cortex raised, so the critic also surfaces a "possibly missed" list for human review (not yet built).

**Deciding axis:** measurability. The damage is why it matters, but what changed my mind is that a missed flag is invisible: nobody knows to check for it.
