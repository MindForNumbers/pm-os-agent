# Cortex: a PM Chief-of-Staff Agent

**R.J. Rimando** · Product School, Agentic Workflows & Loops · October 2026 cohort · final project

Cortex is a chief-of-staff agent for a PM: one drafting agent plus a separate critic call that pulls a project's state, drafts the weekly status update and a capped story batch, and stops at my approval. **Today it runs at assisted: nothing posts without a human.**

▶ **Pitch deck:** [`06-autonomy/pitch.html`](06-autonomy/pitch.html) (download and open in a browser; GitHub shows HTML as source)

---

## Dashboard

| Module | Framework | Artifact |
|---|---|---|
| M1 | The Agent Line | [`01-agent-line/agent-line-map.md`](01-agent-line/agent-line-map.md) |
| M2 | Loop Engineering | [`02-loop-design/loop-spec.md`](02-loop-design/loop-spec.md) ★ |
| M3 | Orchestration & Subagents | [`03-orchestration/orchestration-map.md`](03-orchestration/orchestration-map.md) ★ |
| M4 | Memory & Context | [`04-memory-context/memory-and-context.md`](04-memory-context/memory-and-context.md) |
| M5 | Bounds & Evals | [`05-bounds-evals/bounds-and-evals.md`](05-bounds-evals/bounds-and-evals.md) |
| M6 | Autonomy & Production | [`06-autonomy/production-and-autonomy.md`](06-autonomy/production-and-autonomy.md) ★ · [`06-autonomy/prototype.md`](06-autonomy/prototype.md) ★ · [`06-autonomy/build-insights.md`](06-autonomy/build-insights.md) ★ · [`06-autonomy/pitch.html`](06-autonomy/pitch.html) |

★ = graded deliverable

## Where it sits on the Trust Ladder

**Assisted.** Cortex drafts and recommends; a human copies the draft and posts it, because there's no write tool. To reach **supervised**: build the posting tool + JIT, queue-after-critic, and daily vs Monday modes, then 4 consecutive weeks and ≥ 20 real runs with EV-1 and EV-5 at 100%, EV-4 at 4 of 4 Monday runs, the scripted drill green on every commit, and RP-1…RP-6 green in the final week. Full gate, incident record, and the 17-item still-to-build list: [`production-and-autonomy.md`](06-autonomy/production-and-autonomy.md).

## Build & run

- **Built with:** Claude Code, directed in plain English. Model `claude-haiku-5-5`; the critic is the same model in a separate call with fresh context.
- **Code:** [`00-build/`](00-build/) (`agent.py`, `critic.py`, `tools.py`, `prompts.py`, `bound_drill.py`, mock fixtures).
- **Run it:** see [How to run it](06-autonomy/prototype.md#how-to-run-it); six required run captures (M2→M6) are in [`prototype.md`](06-autonomy/prototype.md).
