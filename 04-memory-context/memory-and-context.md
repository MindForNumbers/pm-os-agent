# Context Engineering & Memory: Cortex PM Chief-of-Staff Agent

> Module 4 · Context Engineering & Memory
>
> ✅ **What this validates:** the agent reasons on the right, safe inputs, by the end you'll have proven a context budget, per-source retrieve-vs-long-context decisions, and a memory map with risk mitigations.
>
> 🗂️ **How the lab maps to this file:** In **Part A** (before the lecture) you don't edit this file, you rough-draft on scratch, focused on the per-source calls in **section 2** plus a quick remember/forget + "how it rots" sketch. In **Part B** (after the lecture) you complete **all five sections**; the Lab Guide's guided builder writes this file for you to copy in and commit.

## 1. Context budget

Each run is one project. Every iteration receives, in priority order (cut last → cut first):

1. **Guardrails, never cut:** system rules (`CORTEX_SYSTEM`), team norms (whole, read fresh), and the task brief (whole, wrapped as untrusted data).
2. **Evidence, never truncated:** the project record, that project's activity since the last approved update, the pinned latest approved update, and the project's roadmap section + shareability flag. If the activity slice itself won't fit, **escalate instead of truncating**: a truncated slice is a missed flag nobody can see.
3. **Precedent, cut first:** past-update top matches for format. They only affect style.

Never in Cortex's context: other projects' data, and confidential roadmap sections. The critic gets the confidential/embargoed **names list** separately, so check c still works.

Today a run is ~6–7 KB of input (about $0.003–0.004 per clean run on Haiku 5.5), far under any limit. The order matters once real activity grows.

## 2. Retrieve vs. long-context: per source

For each data source, decide: **retrieve** (narrow a large/changing corpus to the relevant slice) or **long-context** (just include a bounded set you can reason over).

| Source | Size / volatility | Decision | Why |
|---|---|---|---|
| `get_activity` (PRs, issues, Sev-1s, metrics) | large, grows daily; high volatility | **Retrieve, then long-context the slice:** one project's activity since the last approved update; Cortex gets the whole slice | Volatility says retrieve; citation decides the whole slice, because a Sev-1 ranked out would be a missed flag the critic can't see. |
| `search_past_updates` (past updates + decision log) | unbounded, append-only; newest entry matters most | **Retrieve, scoped to the project:** top matches for format, and always pin the latest approved update | Size says retrieve (the history only grows); citation decides the pin, because the color check and the prior metric depend on that one entry being there. Scoping to the project keeps other projects' entries, like the new Pulsar decision, out of Cortex's context. |
| `get_roadmap` | medium, changes per planning cycle; confidential flags | **Retrieve:** Cortex gets only its project's section + shareability flag; the critic separately gets the confidential names list | Citation keeps the SHAREABLE flag, but the real reason is that Cortex can't leak what it never sees, so the line holds even if the prompt rule fails. |
| `get_norms` | small, one document; rarely changes, matters right away when it does | **Long-context, read fresh every run** | Size says include it all (small, one document, and every rule applies every run); volatility decides fresh, because when a rule changes it matters right away, like Pulsar joining the confidential list this week. A cached copy would miss it. |
| `get_task` (inbound brief) | tiny; new each run, static within it; outsider-written | **Long-context, wrapped and labelled as untrusted data** | Size says include it all (half a page, and dropping part of the ask changes the job); the real reason for the wrapper is that the brief is the only source outsiders write, so it's where injection comes in. The line should hold even if the prompt rule fails. M5's jailbreak run will test it. |
| `get_project` | tiny, one record; changes per sprint | **Long-context for the one project;** a not-found error says only "not found" and escalates, with no list of other projects | Citation needs the whole record (status, flags and the PRD summary back the color call and check d). The not-found fix is the same rule as the roadmap: Cortex can't leak what it never sees. In my M2 missing-data run, the known_projects list and the full roadmap together put Orbit into the draft. |

**Build status:** decisions only, nothing built yet. Today `get_roadmap` returns the whole roadmap, `search_past_updates` isn't project-scoped or pinned, the brief isn't wrapped, `get_project`'s not-found error lists every project, and the activity slice has no time window. These go on the M5 build list.

## 3. Retrieval quality plan

Every retrieved source gets the moves its failure mode demands, not all five everywhere. ✓ = used · ✗ = ruled out (with why).

| Move | `get_activity` | `search_past_updates` | `get_roadmap` |
|---|---|---|---|
| **Routing** | ✗ one source; Step 1 already fixes project + window | ✓ split the two jobs: past updates = format; decisions = rules | ✓ look up the section by project ID, so a keyword can't pull in another project's section |
| **Document grading** | ✓ a failed pull or the wrong project/window escalates as missing data; a successful empty pull is reported as "no activity this window" | ✓ drop other projects' entries (the Pulsar leak); confirm the pin is this project's latest approved update | ✓ confirm the section has its flag and isn't confidential; a confidential ask escalates |
| **Reranking** | ✗ the whole slice is kept | ✓ past updates only, by same project + recency (the cut-first tier); all of this project's decisions come back, never ranked out | ✗ only one section comes back |
| **Self-verification** | ✓ critic checks a (grounding) + e (missed Sev-1s) | ✓ the draft's baseline and prior metric match the pin | ✓ check c against the names list; the draft cites the flag it relied on |
| **Caching** | ✗ the data changes daily | ✗ a stale cache could miss a new approval and give the wrong baseline | ✗ the names list is rebuilt from the roadmap every run, or this week's Pulsar would be missed |

**What each move covers:**
- **`get_activity`:** grading covers the invisible missing slice from my brain-off run. A failed pull escalates, but a successful empty pull isn't an error. The draft must say "no activity this window" explicitly, so a quiet week doesn't cause a false alarm. Self-verification covers grounding and missed Sev-1s.
- **`search_past_updates`:** decisions are rules, so all of this project's decisions come back, never ranked out, the same logic as "every norm applies every run." Only the format tier is reranked.
- **`get_roadmap`:** routing by project ID makes "Cortex can't leak what it never sees" true at lookup. The names list follows the same reasoning as my norms call: rebuilt every run, never cached.

**Cross-source rules (observed in the M4 Step 4 withheld-source run):**
- **Required sources:** withholding a tool didn't withhold the data. With `get_activity` removed, the roadmap held a stale copy of the activity facts (41% → 43%, "shipped"), so Cortex grounded on it and the run passed silently: critic pass, success, no rule fired. So a run can't succeed unless activity was pulled and came back: a required-sources check in code (M5).
- **One source of truth per fact:** metrics and "shipped" claims must cite `get_activity`, not the roadmap or past updates.

**Built today:** self-verification only (critic checks a, c, e), plus `agent.py`'s `last_approved_status()`, which pins the baseline in code for the color check, though not in Cortex's context. Routing, grading, reranking, and the fresh names list go on the M5 build list.

## 4. Memory map (your PM brain)

Cortex learns only from what I've approved: approved updates, my decisions and overrides, and missed flags I confirmed. If it read its own unchecked drafts and verdicts, its mistakes could teach it more mistakes. All memory is per project (M2 §4); nothing is shared across projects.

| Memory type | What Cortex stores | Scope / TTL |
|---|---|---|
| **Working** (in-loop) | This run's tool results, drafts, critic verdicts and reasons | This run; purged at exit |
| **Episodic** (past runs) | Approved past updates; my decisions and overrides; missed flags I confirmed. Cortex reads these. The run log and verdict log are kept for audit only and never read by Cortex. | Per project. Approved updates: 12 weeks, latest always pinned. Decisions and overrides: until superseded. Confirmed missed flags: until a norm covers them. Run and verdict logs: 90 days. |
| **Semantic** (durable facts/prefs) | Nothing copied. Norms, roadmap and PRDs are read from source every run (§2); durable preferences live in the norms doc. | Source of truth; no TTL because nothing is cached |
| **Shared** (across agents) | Cortex ↔ critic: only this run's source data, Cortex's output, and the confidential names list (M3 Field 6) | This run; never across projects |

**Read/write scope (M1 agent line):** Cortex reads episodic memory but never writes to it. Only I approve what goes in, the same rule as approving the update itself (M1 #8a). **TTLs → M5 bounds.**

## 5. Memory risks & mitigations

| Risk | Where it bites Cortex | Mitigation |
|---|---|---|
| **Drift** | Output changes from run to run, or after a change. The same happy brief gave 2 stories in one run and 3 in the next (including a made-up dashboard), and the `ESCALATE:` fix changed behavior. The eval itself has drifted too: `critic_drill.py` no longer matches the new fixtures. | Critic checks every run. Re-run evals on every prompt or memory change (M5); pin or update the drill first. |
| **Poisoning** | Bad content becomes something Cortex "learns": injected text in a brief, or a wrong entry written to episodic memory. | Only I write what Cortex learns from (§4). The brief is wrapped as untrusted and never written to memory. |
| **Staleness** | Planning from old data: brain-off's 2 already-shipped stories; a cached names list would miss Pulsar; a stale baseline gives a wrong color check. Seen in the M4 Step 4 grounded run: the draft says "Shipped the guided activation checklist and step-completion instrumentation," which is last week's news (06-29 update + roadmap), not this week's activity. The critic passed it on check a, because it traces to *a* source, just not this window. Seen again in the M4 Step 4 withheld-source run: with `get_activity` removed, Cortex grounded on the roadmap's stale copy of the activity facts, re-proposed two stories that had already merged (#820, #823), and the run passed silently. | Read fresh every run, no caching, the pinned latest update, the activity window, grading (§3), and the TTLs (§4). A required-sources check in code: a run can't succeed unless activity was pulled and came back (M5). One source of truth per fact: metrics and "shipped" claims must cite `get_activity`, not the roadmap or past updates (§3). |
| **Confidential / retention** | Orbit got into two real drafts (M2 missing-data, and the M2 happy run, later used as the M3 drill's real-leak case), and the Pulsar decision is in the shared log. **Retention gap:** raw traces in `run-output/` keep the full roadmap forever, which breaks my purge rule and 90-day TTL. | Per-project scope, the critic gets only the names list, working memory is purged, and confidential content is never stored. Purge raw traces and unapproved drafts at the TTL (M5 build). **Labelled exception:** `00-build/drill/real-happy-draft.md` names Orbit. Orbit is fictional and already named in the committed fixtures, so it exposes nothing new; when the drill is updated for the new fixtures (M5), swap in a synthetic name. |
| **Write-before-review** | `propose_stories` queues before the critic checks, so a failed story can't be withdrawn. Seen in the "verify escalate fix" run: a non-PRD story was queued, the critic failed it on check d, and the run had to escalate. | Queue only after the critic passes (M5). |
