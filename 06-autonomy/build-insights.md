# Build Insights: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 4, what you learned building it
>
> ✅ **What this validates:** you can reflect on what building it taught you, by the end you'll have proven the friction, the learning, and the aha that changes how you'd design your next agent.

## Friction

_Where did the build fight you? (Loop stop conditions? Context budget? The validator? Bounds?)_

The gap between deciding and building. In M4 I designed project-scoped retrieval, then watched Vega's Sev-1 show up in the critic's reasoning on my M6 end-to-end run, because the design wasn't built. Second: write-before-review, seen 5 times. Stories reach my queue before the critic checks them, even on a clean run.

## Learning

_The two or three things you now understand about shipping agents that you didn't before the course._

1. **A bound is enforced outside the model.** If the model can talk its way past it, it isn't a bound. That's why the critic is a soft bound and my HITL review is the hard backstop.
2. **Grade the path, not just the answer.** My M4 withheld-source run produced a plausible draft that passed the critic, from a stale second copy of the data, and nothing caught it. In M5 I built a code check on which sources returned data, and the scripted drill proves it now refuses that run.
3. **Autonomy is set per segment and per risk, not once.** The same Cortex is assisted for an eng lead approving stories, and capped at supervised on a near-launch project.

## Aha moment

_The single insight that changed how you'd design your next agent._

**Capability isn't permission.** The jailbreak told Cortex to post the confidential roadmap company-wide. Cortex refused, but what made success impossible was that it had no tool that can post. No prompt can give it a credential it doesn't have.

## What you'd do differently

_If you rebuilt Cortex from scratch, what changes?_

Write the evals and the scripted drill before the agent, and design the order of writes from day one: queue stories only after the critic passes. And redact what the drafter sees before writing a single prompt, instead of relying on "never output it."
