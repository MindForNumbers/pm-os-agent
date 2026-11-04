# Orchestration Map: Cortex PM Chief-of-Staff Agent

> Module 3 · Orchestration & Subagents, ★ Deliverable 3
>
> ✅ **What this validates:** nothing advances unchecked, by the end you'll have proven a justified topology, a roster, and a validator with a defined fail action.
>
> Builds on your M2 Loop Spec. Only split one agent into a team when there's a real reason, coordination has a cost.

## 1. Why split? (or why not)

**Decision:** Cortex is one agent plus one independent critic, and nothing more: the only reason to split that holds up is that Cortex can't grade its own work, and my runs proved it twice.

**Current design:** Cortex is a single agent that runs on a daily 7 AM cron: it checks every project for risks, and on Mondays it also drafts the leadership update and proposes up to 10 stories. A separate critic checks its output, and every run ends at my approval checkpoint without sending anything (or stops as stuck or escalated).

| Reason to split | Applies? | Why / why not |
|---|---|---|
| Separation of concerns | **No** | Risk-checking, drafting and stories all use the same project's data, and the risk check feeds the draft, so splitting would just pass the same context between agents. The contamination that matters is cross-project, and per-project state already isolates that. |
| Parallelism | **No** | A run finishes in under a minute and my deadline is before my day starts, so there's no time a split would save. If I add more projects, I'd run one Cortex per project in parallel, which is scaling a single agent, not building a team. |
| Independent validator | **Yes** | Cortex can't see its own blind spots. In my runs it queued a story it admitted was out of scope and leaked an embargoed project name without noticing, and the critic caught both. A self-review in the same context would inherit the same blind spots, so the check has to come from an agent that never saw the drafting. |
| Context-window pressure | **No** | Each run reads one project's data, only a few thousand tokens, and per-project scope keeps it bounded. If real data makes it grow, the first fix is choosing what Cortex reads (M4), not splitting it across agents. |

## 2. Topology

**Pattern:** single + subagents (one agent, one independent validator).

```
[7 AM cron, per project]
   → marker check (already ran today? → SKIP, $0)
   → [Cortex: pulls project, activity, past updates, roadmap, norms;
              flags risks; Mondays: drafts update + proposes ≤10 stories]
        │
        ├─ self-escalates (ESCALATE: missing data · Sev-1 · confidential · injection)
        │     → [Critic: checks the escalation, fresh context — posts nothing, leaks nothing]
        │           → escalate to me, ping                                     ✎ marker
        │
        └─ output → [Critic: checks a–e against the source data, fresh context]
              ├─ fail on b/c (commitment / leak) → BLOCK → escalate to me,
              │                                    held "needs your call", ping   ✎ marker
              ├─ fail on a/d/e → back to Cortex with reasons (max 2 revisions)
              │                  → cap hit → escalate to me, ping                ✎ marker
              └─ pass
                   ├─ MONDAY → status-color check
                   │     ├─ color changed / no STATUS line → escalate, ping       ✎ marker
                   │     └─ same color → [My review checkpoint]
                   │                     → queued, nothing posted                 ✎ marker
                   └─ DAILY (non-Monday) → quiet-day check
                         ├─ no Cortex flags AND empty "possibly missed" list
                         │     → log "no flags", no ping                          ✎ marker
                         └─ otherwise → [My review checkpoint]                    ✎ marker

   STUCK (anywhere): tool fails 3× · no progress · iteration cap · cost cap
         → stop, log, ping me — NO marker (so a retry or --force can finish)
```

✎ marker = today's marker is written (last, after everything is saved). Never on stuck.

**Build note:** the "possibly missed" list is now built (critic check e). Daily mode (M2 gap G3) isn't built yet, so every run today takes the Monday branch; the daily branch and quiet-day check are designed, not built.

## 3. Roster

| Agent / subagent | Responsibility | Runs which Loop Spec |
|---|---|---|
| **Cortex** (chief-of-staff) | Pulls one project's data, flags risks; Mondays also drafts the leadership update and proposes ≤10 stories; self-escalates on missing data, Sev-1, confidential, injection. Never sends. | The M2 loop: daily 7 AM cron, per project (`02-loop-design/loop-spec.md`) |
| **Critic** (independent validator) | Checks every Cortex output (draft or escalation) against checks a–e using only the source data; returns pass/fail, which checks failed, and a "possibly missed" list. Never drafts, never sends. Sees only Cortex's output and the source data, never Cortex's reasoning or conversation, which is what keeps it independent. | No loop of its own: one call per Cortex output, inside the M2 loop, bounded by the revision cap (max 2) |

## 4. Communication & hand-offs

| # | From → To | What passes | Form |
|---|---|---|---|
| 1 | Cron → Cortex | The task brief (project ID, the ask) + that project's state (marker, last approved status) | Function call into `run()`; state from `run-output/state/<PROJECT>.json` |
| 2 | Cortex → Critic | **Only** the proposed output + the source log (the brief and every tool call with its result). Not Cortex's messages or reasoning. | `review(client, model, proposed, source_log)` |
| 3 | Critic → loop code | `{"verdict", "failed_checks", "reasons", "possibly_missed"}` (built in M3), so the code can block on b/c and run the quiet-day check. | Strict JSON, schema-enforced |
| 4 | Loop code → Cortex (**revise only**) | The critic's reasons, as one new message. Not the critic's conversation. **On a b/c block, nothing goes back to Cortex**: the reasons go to me. | One appended user message |
| 5 | Loop code → me | The draft file, the run log entry (outcome, reason, every verdict), and the ping | `run-output/` files; ping is a stub until M2 gap G5 |

**Fresh checks:** on each revision the critic checks the new draft fresh, without seeing its earlier verdict, so it judges the draft rather than just its last complaint. Information flows one way: Cortex sees the critic's conclusions; the critic never sees Cortex's thinking.

**Protocol:** plain in-process function calls. No MCP / A2A: both agents are model calls in one Python process. MCP matters later for connectors (Jira, Drive), not for these hand-offs.

## 5. The validator

An independent critic (`00-build/critic.py`): a separate model call that never sees Cortex's drafting context, only the proposed output and the source data Cortex pulled.

**What the critic checks** (each checkable against the source data, each tied to a real failure or an M1/M2 guardrail):

| # | Check | Fails if | From |
|---|---|---|---|
| a | **Grounded** | Any project name, PR/issue ID, figure, or date isn't in the pulled tool data. | Starter checks |
| b | **No above-the-line commitments** | A ship/GA date is committed, a launch gate is marked, or anything is posted/created/merged. Status appears only as the proposed `STATUS:` line. | M1 #4, #8a/#8b |
| c | **No confidential leak, anywhere** | A CONFIDENTIAL/embargoed project or detail is named anywhere in the output, including the exclusions note. The note may say confidential items were excluded, but never name them. | My happy run named Orbit in the exclusions note and the old critic passed it |
| d | **Stories trace to the PRD** | A proposed story doesn't map to a named in-scope PRD item, or the batch exceeds 10. | M1 run 2 (out-of-scope story), M1 #7 |
| e | **No missed risks** | A Sev-1, launch hold, or at-risk item in the source data isn't flagged. The critic lists each one as "possibly missed." | M1 #5 hardest call, M2 gap G11 |

**Fail action (tiered):**
- **Revise** on a, d, e: grounding slips, out-of-scope stories and missed risks are fixable, so Cortex gets a retry with the critic's reasons.
- **Block + escalate immediately** on b, c: a leak or a commitment is an Above risk from my M1 map, so it's blocked and comes to me, held and marked "needs your call." A revised draft that passes would look clean and hide that a leak nearly happened. A ping is a small price for seeing every near-miss.
- **Log every verdict** either way (per-project run log, M2 state).

**Revision cap:** max 2 revisions (`CORTEX_MAX_REVISIONS=2`), then escalate. Every run so far fixed itself in one revision, so 2 leaves room for a harder case without looping. If Cortex can't fix it in two tries with the critic's reasons, the problem is probably the data, not the draft, and that's my call.

The old jailbreak check was dropped on purpose: a successful injection would surface as b, c, or a; Cortex's own prompt still refuses and escalates injections; M5 has a dedicated jailbreak run.

**Pass action:** a passing draft advances to my review checkpoint. It never auto-sends (M1 #8a/#8b). The M2 status-color check still runs after a pass and can escalate.

## 6. State: shared vs isolated

| | What | Who sees it |
|---|---|---|
| **Shared** | Source data: the brief + every tool result (project, activity, past updates, roadmap, norms) | Both, read-only. The critic also gets the confidential/embargoed names list (refined in M4 §2): it needs the names, not the full confidential sections, for check c to catch a leak. |
| **Shared** | The output under review (draft or escalation) | Both: Cortex wrote it, the critic judges it. |
| **Isolated: Cortex only** | Cortex's conversation and reasoning | Never the critic. |
| **Isolated: critic only** | The critic's reasoning and earlier verdicts | Not Cortex (reasons only, and only on a revise). Not the critic's own next call (every check is fresh). |
| **Isolated: loop code + me** | Per-project state: marker, `--force` log, run log, verdict log, last approved status | Neither agent reads it directly. Letting Cortex learn from the run log is an M4 decision. |
| **Never shared** | Anything across projects | Each project's run sees only its own data and state (M2 §4). |

This writes down rules I've already set: the critic never sees Cortex's reasoning, every check is fresh, reasons only flow back on a revise, and nothing crosses projects.

## 7. Cost & latency budget

| | Model calls | Cost (measured) |
|---|---|---|
| Clean run (critic passes first try) | Cortex + 1 critic check | $0.0028–$0.0033 |
| Each revision | +1 Cortex draft + 1 critic check | ~$0.0027 |
| **Worst case at the revision cap** | 3 drafts + 3 critic checks | **~$0.0085, roughly 3× a clean run** |
| Escalation | Cortex + 1 critic check | $0.0015–$0.0019 |

The critic adds 1 call per output. That's worth it: the critic is the only thing that caught the Orbit leak.

**Latency:** each critic check adds one model call (a few seconds); not yet timed. Every run so far finished in under a minute, well before the 7 AM deadline.

**Forward to M5 bounds:** my $0.50 cap is about 60× the worst case, so it wouldn't catch a runaway early. In M5 I'll time each step and tighten the cap toward the worst case.
