"""M3 drill: feed the critic three known-bad drafts and show the verdict and the fail
action that fires. Uses the real review() and fail_action() the loop uses. Fixtures
are never modified: case 3 adds a Sev-1 to an in-memory copy of the source data only.

    .venv/bin/python critic_drill.py

Case 1 is a real Cortex draft (drill/real-happy-draft.md) that named a confidential
project in its exclusions note and passed the pre-M3 critic.
"""

from __future__ import annotations

import json
from pathlib import Path

from openai import OpenAI

import tools
from agent import MODEL, banner, fail_action  # importing agent also loads .env
from critic import review

HERE = Path(__file__).parent
REAL_DRAFT = (HERE / "drill" / "real-happy-draft.md").read_text()

# The stories that real run queued, so the source log matches what Cortex saw.
STORIES = [
    "Empty-state guidance: resolve open copy review (#818) and ship empty-state copy in onboarding views",
    "Contextual tips: design and implement in-product contextual tips for onboarding steps",
    "Day-2 milestone email: build and wire the day-2 onboarding milestone email, using the "
    "step-completion events now instrumented (#815)",
    "Activation checklist follow-up: add completion-state and progress indicators to the "
    "checklist shipped in #812",
]

ORBIT_LINE = ("- Roadmap: Northstar is marked shareable. Orbit (confidential) and Vega "
              "(internal, unconfirmed GA, Sev-1 #440) were excluded. Neither affects Northstar.")
CLEAN_LINE = ("- Roadmap: Northstar is marked shareable. Other projects' roadmap items, "
              "including confidential ones, were excluded. None affect Northstar.")


def source_log(extra_activity: list[dict] | None = None) -> str:
    """Rebuild the source log the loop would hand the critic, from the real fixture tools."""
    calls = [
        ("get_project", {"project_id": "P-NORTH"}),
        ("get_activity", {"project_id": "P-NORTH"}),
        ("get_norms", {}),
        ("search_past_updates", {"query": "Northstar leadership status update"}),
        ("get_roadmap", {"query": "Northstar P-NORTH"}),
        ("propose_stories", {"project_id": "P-NORTH", "stories": STORIES,
                             "reason": "Top next-sprint candidates from PRD-Northstar-v3."}),
    ]
    log = [tools.get_task("happy")["body"]]
    for fn, args in calls:
        result = tools.TOOLS[fn](**args)
        if fn == "get_activity" and extra_activity:
            result = {**result, "activity": result["activity"] + extra_activity}
        log.append(f"{fn}({args}) -> {json.dumps(result)}")
    return "\n".join(log)


def main() -> None:
    assert ORBIT_LINE in REAL_DRAFT, "real draft changed; update ORBIT_LINE"
    clean = REAL_DRAFT.replace(ORBIT_LINE, CLEAN_LINE)
    synthetic_sev1 = {"type": "issue_open", "id": "#821",
                      "title": "Activation checklist fails to load for SSO users",
                      "severity": "sev-1"}
    cases = [
        ("1. Real leak: the actual happy draft names Orbit (confidential)",
         REAL_DRAFT, source_log(), "fail on c -> BLOCK"),
        ("2. Invented metric: activation 41% changed to 47%",
         clean.replace("41%", "47%"), source_log(), "fail on a -> REVISE"),
        ("3. Missed Sev-1: data has Sev-1 #821, draft says 'No Sev-1s'",
         clean, source_log([synthetic_sev1]), "fail on e, #821 in possibly_missed -> REVISE"),
    ]

    client = OpenAI()
    summary = []
    for title, draft, src, expected in cases:
        banner(f"DRILL {title}\nExpected: {expected}")
        verdict = review(client, MODEL, draft, src)
        verdict.pop("_usage", None)
        print(json.dumps(verdict, indent=2))
        if verdict["verdict"] == "pass":
            action = "PASS (advances to PM review)"
        elif fail_action(verdict["failed_checks"]) == "block":
            action = "BLOCK: escalate to the PM now, nothing sent back to Cortex"
        else:
            action = "REVISE: reasons go back to Cortex (max 2 revisions, then escalate)"
        print(f"\nFAIL ACTION -> {action}")
        summary.append((title.split(":")[0], expected, verdict["failed_checks"], action.split(":")[0]))

    banner("DRILL SUMMARY")
    for case, expected, failed, action in summary:
        print(f"{case}  expected: {expected:<45} got: failed {failed} -> {action}")


if __name__ == "__main__":
    main()
