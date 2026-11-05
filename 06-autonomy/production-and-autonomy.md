# Production & Autonomy: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 5, how you'd ship it, govern it, and widen trust over time
>
> ✅ **What this validates:** you can ship it, govern it, and widen trust deliberately, by the end you'll have proven an autonomy dial, a Trust Ladder rung with its eval gate, and a governance plan.

## Autonomy Dial by segment

_Autonomy is a product decision per user, not one global setting._

| Segment | Desired autonomy | Why |
|---|---|---|
| Seasoned PM who owns the project | **Target: bounded-autonomous · assisted today; supervised once posting and JIT ship** | Target: they know the project, so the exclusion review becomes a weekly spot-check rather than "only when the critic flags," because the critic is a soft bound. Assisted today because the posting tool, JIT, EV-5 and RP-6 aren't done. |
| New PM / APM onboarding to a project | supervised (assisted today; supervised once posting and JIT ship) | Every checkpoint pauses, because they don't yet know what normal looks like for the project. |
| Eng lead receiving story batches | assisted | Approves each story, because stories turn into real sprint work. |

**Override:** any Yellow/Red or near-launch project caps every segment at supervised: higher blast radius, less autonomy. A cap only lowers autonomy, never raises it. Near-launch = within 2 weeks of a launch date on the roadmap, or any `launch_hold` flag on the project, both checkable from `get_roadmap` and `get_project`. An unconfirmed launch date counts as near-launch (fail safe, like my M2 rule that unclear output defaults to escalate).

_The dial only changes how many HITL checkpoints pause for a segment. It never moves the M1 agent line: tone/status calls, what to escalate, and company-wide updates stay above the line for everyone, and a pre-authorization claim still mints nothing without my approval click._

## Trust Ladder

- **Current rung:** assisted. Cortex drafts and recommends, but a human copies the draft and posts it, because there's no write tool.
- **Eval gate to reach the next rung (supervised):**
  - **Build first:** `post_team_update` + JIT; queue-after-critic (RP-6 green); the daily vs Monday modes, so daily runs exist.
  - **Window:** 4 consecutive weeks and at least 20 real runs (the daily 7 AM cron gives about 20 per project).
  - **Thresholds:** EV-5 and EV-1 at 100% across all runs; EV-4 at 4 of 4 Monday update runs; the scripted drill (EV-3, EV-6) green on every commit; RP-1…RP-6 all green in the final week.
- **Incident record (clean = 0 of each in the window):** a post without approval · an embargoed project named in any critic-passed output · a story queued before a critic pass · a kill-switch pull for misbehavior. A critic catch doesn't reset the window, but two catches of the same kind (the same critic check failing) in one window trigger a review, because Cortex is repeating a mistake and leaning on a soft bound to cover it. Evidence: Orbit has been named in four runs, all check (c) leaks, two of them jailbreaks: the M2 happy run (used as M3 drill case 1), the M2 missing-data draft (per M4 §5), my M5 Part A jailbreak probe (run log: "M5 Part A probe", critic blocked c), and the M5 Step 3 jailbreak proof.
- **Incident record so far:** no production runs yet. Prototype near-misses, all caught or documented: RP-4 (Orbit named, critic blocked), RP-3 / M4 withheld source (passed silently in M4; the M5 required-sources check now refuses it, proven by the scripted drill), RP-6 (stories queued before review, open).

## Deployment plan

- **Runtime:** serverless scheduled job on the M2 daily 7 AM cron, because it's a short, ~1¢ daily job. State files and the `KILL` file move to durable storage, since a kill switch that resets every run isn't one.
- **Operator / on-call owner:** me (PM). Backup: the Northstar eng lead on-call, who can pull the kill switch. Escalation: Cortex pings my DM → no acknowledgement in 4 business hours → backup → 4 more hours → eng manager. Monitoring alerts follow the same chain. The kill switch stays owner-only to clear: if it's pulled while I'm away, Cortex stays off until I'm back. That's safe at assisted, because humans write the update the old way.
- **Rollback (smallest lever first):** drop the dial a rung → disable a tool (e.g. `post_team_update` off = back to assisted) → revert prompt/model to the last gated tag → kill switch.
- **Monitoring (signals from `run_log`, alert when):**
  - **Eval pass %:** EV-1 or EV-5 below 100%, or any EV-4 miss.
  - **Escalation / STUCK rate:** more than 2 STUCK runs a week, or more than 1 in 3 runs escalating.
  - **Cost-to-serve:** any run over $0.01, or the $0.25 daily cap trips.
  - **Trust incidents:** any one, which alerts and drops the dial a rung.
  - **Critic fails by check:** the same critic check fails twice in a window.
  - **Ping volume:** more than 5 pings a week, or false alarms two weeks running.

## ROI metrics (beyond adoption & tokens)

| Metric | Target | How it's captured |
|---|---|---|
| **Outcome: PM time saved on the weekly update** | Review in 15 minutes or less versus about 60 by hand, so about 45 min/week saved per project. Baseline is an estimate until measured. | Log manual time for 2 weeks before deploy, then measure review time from `run_log`: draft opened → approval (needs an "opened" event, on the build list). |
| **Cost-to-serve: fully loaded cost per approved update** | About $19 per update (15 min at an assumed $75/hr) versus about $75 by hand. The model cost (~$0.005) is negligible, so review time is the cost to drive down. | Model spend from `run_log` + review minutes × hourly rate. |
| **Trust incidents** | 0 per month on my four zero-tolerance criteria, plus escape rate: 0 escaped errors that change a status call or a commitment, and no more than 1 minor correction per 10 posted updates. | Incident log for the four criteria; corrections and follow-ups in the channel for escapes. |

## Widen-autonomy decision rule

_What evidence lets you turn the dial up one notch, stated in advance._

Turn a segment's dial up one rung only when Cortex has already cleared the eval gate for that rung and that segment has 4 consecutive weeks at its current rung with 0 trust incidents, 0 escaped errors that change a status call or commitment, and reviews averaging 15 minutes or less; never on a Yellow/Red or near-launch project. Only I approve a promotion; anyone on the escalation chain can trigger a demotion, and any trust incident drops the dial a rung and restarts the 4 weeks.

## Governance & forward strategy

- **Compliance:** never in a prompt: secrets and credentials (including the JIT token, which the model never sees), customer PII from tickets, HR or performance data. Confidential projects are redacted per my M4 decision: Cortex gets only its project's roadmap section, and the critic gets the confidential/embargoed names list for check (c) (on the build list). Internal author handles are fine; customer emails and names in tickets are redacted when a tool returns them; raw pulls are purged at run exit (M4). Limit: the jailbreak brief itself contains "Orbit", so redaction alone can't keep the name out of context. The prompt fix is still needed, with check (c) as the backstop.
- **Safety:** above the line for every segment: tone/status calls, what to escalate, company-wide updates (no tool, ever), and pre-authorization claims mint nothing without my approval click. Kill switch: the `KILL` file in durable storage; I or the backup can pull it, only I can clear it.
- **Reliability:** caps in code (7 iterations, 90s timeout, $0.02/run, $0.25/day, story cap 5); a tool failing 3× in a row → STUCK, ping, rollback. Model down: fail safe: retry within the timeout, then STUCK and ping, and the team writes the update the old way. A failover model hasn't passed my eval gate, and at assisted, off is safe.
- **Strategy:** widen to a second project, Vega (`P-VEGA`), not P-HALO (HALO isn't a real project). Vega is at risk with a launch hold and an open Sev-1 (#440), so it tests check (e), and my near-launch override caps it at supervised. Gate: EV-1 cross-project at 100% across both projects, plus EV-4 and EV-5 green on Vega, over 4 weeks.

### Still to build

1. `post_team_update` + JIT single-use post token
2. Queue stories only after the critic passes (RP-6 green)
3. Daily vs Monday modes
4. An "opened" event in `run_log` (ROI review-time capture)
5. State files + `KILL` moved to durable storage
6. Enforce owner-only kill-switch clear (policy today, not enforced)
7. Prompt fix: Cortex doesn't name the embargoed project when reporting an injection
8. Confidential redaction (M4): `get_roadmap` scoped to the project's own section; critic names list rebuilt per run
9. Project-scoped `search_past_updates` by ID
10. Pin the latest approved update in `search_past_updates` (M4)
11. Wrap the brief as untrusted data (M4 `get_task`)
12. `get_project` not-found returns only "not found", no project list (M4)
13. One source of truth per fact
14. Purge run-output at TTL
15. Update the stale `critic_drill.py`
16. Pin the model ID and prompt version in git, so rollback lever (iii) works
17. Critic on a different model from the drafter
