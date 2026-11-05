"""Cortex, a minimal, explicit agent loop you (and your coding agent) can read end
to end. This is the agent you ship: your PM chief-of-staff. You build it by
directing your coding agent (Claude Code / Cursor / Codex) to shape this file. You
never have to hand-write it.

Every bound the course talks about is visible right here in code, not buried in a
framework: the max-iteration counter, the per-run and daily cost caps, the timeout,
the revision cap, the stop/escalate conditions, the auto-queue cap, and the absence
of any publish tool.

Usage (ask your coding agent to run these for you, or run them yourself):
    python agent.py                # runs the happy-path task (weekly status update)
    python agent.py missing-data   # the stuck/escalate case
    python agent.py jailbreak       # the prompt-injection refusal case
    python agent.py --force --reason "fixed bad data"   # human-only: ignore today's marker

Every run ends by showing the drafted status update in a FINAL STATUS UPDATE block
(or LAST DRAFT, held, if a bound trips), and saves it to run-output/. That file is
always a draft held for a human, it is never posted, there is no publish tool.

Requires OPENAI_API_KEY in your environment (see .env.example). Model and bounds
are read from env so you can tune them, that tuning is your M5 deliverable.

The loop is deliberately transparent (hand-written tool-calling on the openai
client) so a grader can see the machinery. Keep the bounds explicit if you rework it.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import time
from datetime import date, datetime
from pathlib import Path

from openai import APITimeoutError, OpenAI

# Load .env BEFORE importing tools: tools.py reads its bounds (the story cap) at
# import time, and a gate that silently ignores .env looks enforced and isn't.
try:  # load .env if python-dotenv is installed; harmless if it isn't
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import tools  # noqa: E402
from critic import review  # noqa: E402
from prompts import CORTEX_SYSTEM  # noqa: E402

# --- Bounds (your M5 deliverable: tune these and justify them) ----------------
MODEL = os.environ.get("CORTEX_MODEL", "gpt-4o-mini")
MAX_ITERATIONS = int(os.environ.get("CORTEX_MAX_ITERATIONS", "7"))
MAX_REVISIONS = int(os.environ.get("CORTEX_MAX_REVISIONS", "2"))
COST_CAP_USD = float(os.environ.get("CORTEX_COST_CAP_USD", "0.02"))
DAILY_CAP_USD = float(os.environ.get("CORTEX_DAILY_CAP_USD", "0.25"))  # all projects, per day
TIMEOUT_S = float(os.environ.get("CORTEX_TIMEOUT_S", "90"))           # wall clock, per run
MAX_QUEUE_ITEMS = int(os.environ.get("CORTEX_MAX_QUEUE_ITEMS", "5"))
# Rough $ per 1M tokens for your chosen model, set to match its pricing.
PRICE_IN = float(os.environ.get("CORTEX_PRICE_IN_PER_M", "0.15"))
PRICE_OUT = float(os.environ.get("CORTEX_PRICE_OUT_PER_M", "0.60"))
# Stuck triggers from the Loop Spec (02-loop-design/loop-spec.md §3).
MAX_TOOL_FAILS = int(os.environ.get("CORTEX_MAX_TOOL_FAILS", "3"))     # data can't be pulled
MAX_NO_PROGRESS = int(os.environ.get("CORTEX_MAX_NO_PROGRESS", "2"))   # going in circles
# Required sources (M4 withheld-source finding): a run can't succeed unless each of
# these was called AND returned data. Another source holding a stale second copy of
# the same facts (the roadmap's 41% -> 43%) doesn't count.
REQUIRED_SOURCES = ("get_project", "get_activity")

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_project", "description": "Look up a project by its ID (status, flags, linked PRD).",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {
        "name": "get_activity",
        "description": "Pull recent engineering activity for a project (merged PRs, open issues, Sev-1s).",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {
        "name": "search_past_updates",
        "description": "Search previous status updates and decisions for tone and precedent.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_roadmap",
        "description": "Return the roadmap. Some items are flagged confidential/embargoed.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_norms", "description": "Return the team norms / PM playbook the agent must follow.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "propose_stories",
        "description": "Queue a set of backlog stories for human approval (creates nothing; rejected above the item cap).",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"},
            "stories": {"type": "array", "items": {"type": "string"}},
            "reason": {"type": "string"}}, "required": ["project_id", "stories"]}}},
]


def load_spend() -> dict:
    """Daily spend ledger shared by ALL projects: {"YYYY-MM-DD": dollars}."""
    path = STATE_DIR / "_spend.json"
    return json.loads(path.read_text()) if path.exists() else {}


def record_spend(day: str, dollars: float) -> None:
    ledger = load_spend()
    ledger[day] = round(ledger.get(day, 0.0) + dollars, 6)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "_spend.json").write_text(json.dumps(ledger, indent=2))


class Bounds:
    """Tracks spend and wall clock and trips the caps. All enforced OUTSIDE the model."""

    def __init__(self):
        self.cost = 0.0
        self.started = time.monotonic()
        self.today = date.today().isoformat()
        self.spent_before = load_spend().get(self.today, 0.0)

    def charge(self, prompt_tokens: int, completion_tokens: int) -> None:
        dollars = (prompt_tokens * PRICE_IN + completion_tokens * PRICE_OUT) / 1_000_000
        self.cost += dollars
        # Written after every API call, so a crash loses at most one call's spend.
        record_spend(self.today, dollars)

    def add(self, usage) -> None:
        self.charge(usage.prompt_tokens, usage.completion_tokens)

    def over_cap(self) -> bool:
        return self.cost >= COST_CAP_USD

    def over_daily_cap(self) -> bool:
        return self.spent_before + self.cost >= DAILY_CAP_USD

    def remaining_s(self) -> float:
        return TIMEOUT_S - (time.monotonic() - self.started)

    def timed_out(self) -> bool:
        return self.remaining_s() <= 0


OUTPUT_DIR = Path(__file__).parent / "run-output"


def banner(text: str) -> None:
    print(f"\n{'=' * 64}\n{text}\n{'=' * 64}")


STATE_DIR = OUTPUT_DIR / "state"

# Kill switch (M5): a file outside the model, checked before every model call and
# every tool call. The owner or eng on-call creates it to halt; only the owner
# deletes it to turn Cortex back on.
KILL_FILE = STATE_DIR / "KILL"


def kill_switch_on() -> bool:
    return KILL_FILE.exists()

# Tiered fail action (Orchestration Map §5). b = above-the-line commitment,
# c = confidential leak: Above risks from M1, never revised, always to the human.
BLOCK_CHECKS = {"b", "c"}


def fail_action(failed_checks) -> str:
    """'block' (escalate now, nothing back to Cortex) on b/c; otherwise 'revise'."""
    return "block" if BLOCK_CHECKS & set(failed_checks or []) else "revise"


def project_id_from(task_body: str) -> str:
    """Read the project ID (e.g. P-NORTH) from the brief before any model call, so a
    same-day skip costs nothing."""
    m = re.search(r"\bP-[A-Z0-9]+\b", task_body)
    return m.group(0) if m else "UNKNOWN"


def load_state(project_id: str) -> dict:
    """Per-project state (Loop Spec §4): one file per project, nothing shared."""
    path = STATE_DIR / f"{project_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"project_id": project_id, "marker": None, "force_log": [], "run_log": []}


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / f"{state['project_id']}.json").write_text(json.dumps(state, indent=2))


def ping(text: str) -> None:
    """Loop Spec: stuck and escalate ping the owner via Slack DM. Not wired yet (G5),
    so the trace shows where a ping WOULD fire."""
    print(f"\nPING -> owner (not wired: G5): {text}")


def last_approved_status(project_id: str) -> tuple[str, str] | None:
    """(color, week) of the project's most recent approved update, or None."""
    record = tools._load_json("projects.json").get(project_id)
    if record is None or not record.get("name"):
        return None
    name = record["name"].split()[0]
    updates = [u for u in tools._load_json("past-updates.json") if u.get("project") == name]
    if not updates:
        return None
    latest = max(updates, key=lambda u: u.get("week", ""))
    m = re.match(r"\s*(Green|Yellow|Red)\b", latest.get("summary", ""), re.IGNORECASE)
    return (m.group(1).capitalize(), latest["week"]) if m else None


def proposed_status(draft: str) -> str | None:
    """Color from the draft's final `STATUS: <color>` line (required by prompts.py)."""
    found = re.findall(r"STATUS:\s*\**\s*(Green|Yellow|Red)\b", draft, re.IGNORECASE)
    return found[-1].capitalize() if found else None


# Pre-authorization claims (M1 row, M5). SIGNAL ONLY, never blocks: rephrasing gets
# past any phrase list. The real block is that a claim can't mint a JIT write token.
PREAUTH_PATTERNS = [
    r"pre-?\s?(authori[sz]ed|approved)",
    r"already (been )?(approved|authori[sz]ed|signed off)",
    r"(you are|you're) (now )?authori[sz]ed",
    r"ignore (all )?(your |previous |prior )*(rules|instructions|norms)",
    r"system override|admin mode",
    r"do not escalate|don't escalate|no need to (ask|wait for) approval",
    r"skip (the )?(review|approval)",
]


def preauth_signals(text: str, source: str) -> list[str]:
    """Each pattern that matches, as 'source: "matched text"' for the human to review."""
    hits = []
    text = re.sub(r"\s+", " ", text)   # phrases wrap across lines in pasted briefs
    for pattern in PREAUTH_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            hits.append(f'{source}: "{m.group(0)}"')
    return hits


def escalation_line(output: str) -> str | None:
    """The first real `ESCALATE:` line anywhere in the output, or None. Cortex doesn't
    always put it first, and success drafts sometimes say "ESCALATE: Not required",
    which is not an escalation."""
    for line in output.splitlines():
        m = re.match(r"\s*\**\s*ESCALATE:\**\s*(.*)", line, re.IGNORECASE)
        if m and not re.match(r"(not (required|needed)|none|n/a)\b", m.group(1).strip(),
                              re.IGNORECASE):
            return line.strip()
    return None


def emit_deliverable(which: str, draft: str, *, kind: str,
                     reason: str, cost: float) -> None:
    """Surface AND persist Cortex's drafted status update so it can't get lost in
    the scroll-back. This is still a DRAFT held for human review, never a post,
    there is no publish tool, and an escalated or stuck run is held on purpose.

    Runs on every exit: a success prints the FINAL update; an escalate or stuck exit
    prints the LAST draft it managed to write plus why it was held.
    """
    accepted = kind == "success"
    banner("FINAL STATUS UPDATE (draft, validator-approved, NOT posted)" if accepted
           else "LAST DRAFT (held, NOT posted, escalated to a human: needs your call)"
           if kind == "escalate"
           else "LAST DRAFT (held, NOT posted, run STUCK and gave up)")
    if draft.strip():
        print(draft.rstrip())
    else:
        print("(Cortex stopped before it produced a draft, nothing to show.)")
    if not accepted:
        print(f"\nWhy it was held: {reason}")

    if draft.strip():
        OUTPUT_DIR.mkdir(exist_ok=True)
        out = OUTPUT_DIR / f"status-update-{which}.md"
        state = "accepted by validator" if accepted else f"HELD, {kind}"
        out.write_text(
            f"<!-- Cortex draft, {state}; NOT posted. Run cost ~ ${cost:.4f}. -->\n"
            f"<!-- {reason} -->\n\n{draft.rstrip()}\n", encoding="utf-8")
        print(f"\nSaved draft -> {out.relative_to(Path(__file__).parent)}  "
              f"(for your review, nothing was posted)")


def run(which: str = "happy", *, force: bool = False, force_reason: str = "") -> None:
    task = tools.get_task(which)
    if "error" in task:
        print(task)
        return

    # Double-run protection (Loop Spec §1), checked before any API spend.
    project_id = project_id_from(task["body"])
    state = load_state(project_id)
    today = date.today().isoformat()
    if force:
        state["force_log"].append({"who": os.environ.get("USER") or getpass.getuser(),
                                   "why": force_reason,
                                   "when": datetime.now().isoformat(timespec="seconds")})
        save_state(state)
        print(f"--force by {state['force_log'][-1]['who']}: {force_reason}")
    elif state["marker"] == today:
        banner(f"SKIPPED, {project_id} already ran today ({today}). Nothing drafted or "
               f"queued. Use --force --reason \"...\" for a fresh run.")
        return

    client = OpenAI()
    bounds = Bounds()
    tools.reset_run()   # the story cap counts per run, across calls
    verdict_log: list[dict] = []   # every critic verdict, logged on every exit
    signals: list[str] = preauth_signals(task["body"], "brief")   # signal only

    def finish(kind: str, reason: str, draft: str) -> None:
        """Every exit goes through here (Loop Spec §3).
        success / escalate: the run worked, so write today's marker LAST.
        stuck: the run broke, so no marker; a retry or --force can still finish.
        stuck also rolls back: an unreviewed write in a trusted queue is still a
        write, so a broken run leaves 0 stories queued (escalate keeps them for HITL)."""
        withdrawn: list[str] = []
        if kind == "stuck":
            withdrawn = tools.withdraw_run()
            reason += (f"; {len(withdrawn)} queued stories withdrawn (simulated, stories "
                       f"only live in the run output)")
        emit_deliverable(which, draft, kind=kind, reason=reason, cost=bounds.cost)
        if signals:
            banner("FLAG FOR YOUR REVIEW: possible pre-authorization claim (signal only, "
                   "it authorizes nothing, only your approval mints a write token)")
            print("\n".join(f"- {s}" for s in signals))
        state["run_log"].append({"date": today, "outcome": kind, "reason": reason,
                                 "cost_usd": round(bounds.cost, 4),
                                 "verdicts": verdict_log,
                                 "preauth_signals": signals,
                                 "stories_withdrawn": withdrawn})
        if kind in ("stuck", "escalate"):
            ping(f"{project_id} {kind.upper()}: {reason}")
        if kind in ("success", "escalate"):
            state["marker"] = today
        save_state(state)

    banner(f"CORTEX RUN, fixture: task-{which}, project {project_id}  "
           f"(auto-queue cap {MAX_QUEUE_ITEMS} items)")
    print(task["body"])

    def halt_killed(where: str, draft: str) -> None:
        """Halt + roll back (finish() withdraws the queued stories), hold the draft, ping."""
        reason = (f"kill switch tripped {where}; "
                  f"no JIT tokens outstanding (post_team_update not built)")
        banner(f"KILLED, {reason}. Run cost ≈ ${bounds.cost:.4f}")
        finish("stuck", reason, draft)

    # Kill switch and daily cap are checked before any API spend.
    if kill_switch_on():
        halt_killed("before start", "")
        return

    if bounds.over_daily_cap():
        reason = (f"daily cap ${DAILY_CAP_USD} already spent today "
                  f"(${bounds.spent_before:.4f}), refusing to start")
        banner(f"STUCK, {reason}.")
        finish("stuck", reason, "")
        return

    messages = [
        {"role": "system", "content": CORTEX_SYSTEM},
        {"role": "user", "content": f"PM task brief:\n\n{task['body']}"},
    ]
    source_log: list[str] = [task["body"]]
    revisions = 0
    last_draft = ""
    tool_fail_streaks: dict[str, int] = {}   # stuck trigger 1, per tool
    no_progress_streak = 0    # stuck trigger 4
    seen_calls: set[str] = set()
    failed_calls: set[str] = set()   # a retry of a failed call is progress, not a circle
    pulled: set[str] = set()         # tools that returned data, for REQUIRED_SOURCES

    for step in range(1, MAX_ITERATIONS + 1):
        if kill_switch_on():
            halt_killed(f"at step {step}", last_draft)
            return
        if bounds.over_cap():
            reason = f"cost cap ${COST_CAP_USD} hit at ${bounds.cost:.4f}"
            banner(f"STUCK, {reason}. Halting.")
            finish("stuck", reason, last_draft)
            return
        if bounds.over_daily_cap():
            reason = (f"daily cap ${DAILY_CAP_USD} hit at "
                      f"${bounds.spent_before + bounds.cost:.4f} today")
            banner(f"STUCK, {reason}. Halting.")
            finish("stuck", reason, last_draft)
            return
        if bounds.timed_out():
            reason = f"timeout ({TIMEOUT_S:.0f}s) reached"
            banner(f"STUCK, {reason}. Halting. Run cost ≈ ${bounds.cost:.4f}")
            finish("stuck", reason, last_draft)
            return

        # Each request only gets the run's remaining time, no SDK retries, so a hung
        # call can't stretch the run past TIMEOUT_S.
        try:
            resp = client.with_options(timeout=bounds.remaining_s(), max_retries=0) \
                .chat.completions.create(model=MODEL, messages=messages, tools=TOOL_SCHEMAS)
        except APITimeoutError:
            reason = f"timeout ({TIMEOUT_S:.0f}s) reached during a model call"
            banner(f"STUCK, {reason}. Halting. Run cost ≈ ${bounds.cost:.4f}")
            finish("stuck", reason, last_draft)
            return
        bounds.add(resp.usage)
        msg = resp.choices[0].message

        if msg.tool_calls:
            messages.append(msg)
            made_new_call = False
            for call in msg.tool_calls:
                if kill_switch_on():
                    halt_killed(f"before a tool call at step {step}", last_draft)
                    return
                fn = call.function.name
                args = json.loads(call.function.arguments or "{}")
                key = f"{fn}:{json.dumps(args, sort_keys=True)}"
                # Retries are still capped by MAX_TOOL_FAILS and MAX_ITERATIONS.
                made_new_call = (made_new_call or key not in seen_calls
                                 or key in failed_calls)
                seen_calls.add(key)
                result = tools.TOOLS[fn](**args)
                # Per tool: another tool succeeding must not hide one source failing.
                tool_fail_streaks[fn] = (tool_fail_streaks.get(fn, 0) + 1
                                         if "error" in result else 0)
                if "error" in result:
                    failed_calls.add(key)
                else:
                    failed_calls.discard(key)
                    pulled.add(fn)
                source_log.append(f"{fn}({args}) -> {json.dumps(result)}")
                signals.extend(s for s in preauth_signals(json.dumps(result), fn)
                               if s not in signals)
                print(f"\n[step {step}] TOOL {fn}({args})")
                print(f"          -> {json.dumps(result)[:300]}")
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": json.dumps(result)})
            no_progress_streak = 0 if made_new_call else no_progress_streak + 1
            failing = [t for t, n in tool_fail_streaks.items() if n >= MAX_TOOL_FAILS]
            if failing:
                reason = (f"{failing[0]} failed {tool_fail_streaks[failing[0]]}x in a row "
                          f"(data can't be pulled)")
                banner(f"STUCK, {reason}. Halting.")
                finish("stuck", reason, last_draft)
                return
            if no_progress_streak >= MAX_NO_PROGRESS:
                reason = f"no progress for {no_progress_streak} iterations (only repeated tool calls)"
                banner(f"STUCK, {reason}. Halting.")
                finish("stuck", reason, last_draft)
                return
            continue

        # No tool calls => Cortex produced a proposed output. Validate it.
        proposed = msg.content or ""
        no_progress_streak = no_progress_streak + 1 if proposed == last_draft else 0
        last_draft = proposed
        print(f"\n[step {step}] PROPOSED OUTPUT:\n{proposed}")
        if no_progress_streak >= MAX_NO_PROGRESS:
            reason = f"no progress for {no_progress_streak} iterations (same output repeated)"
            banner(f"STUCK, {reason}. Halting.")
            finish("stuck", reason, last_draft)
            return

        if kill_switch_on():
            halt_killed(f"before the critic call at step {step}", last_draft)
            return
        banner("CRITIC, independent validation")
        try:
            verdict = review(client.with_options(timeout=max(bounds.remaining_s(), 0.1),
                                                 max_retries=0),
                             MODEL, proposed, "\n".join(source_log))
        except APITimeoutError:
            reason = f"timeout ({TIMEOUT_S:.0f}s) reached during the critic call"
            banner(f"STUCK, {reason}. Halting. Run cost ≈ ${bounds.cost:.4f}")
            finish("stuck", reason, last_draft)
            return
        # Estimate critic spend too.
        bounds.charge(verdict["_usage"]["prompt"], verdict["_usage"]["completion"])
        shown = {k: v for k, v in verdict.items() if k != "_usage"}
        verdict_log.append(shown)
        print(json.dumps(shown, indent=2))

        if verdict["verdict"] == "pass":
            escalation = escalation_line(proposed)
            if escalation:
                why = re.sub(r"^\**\s*ESCALATE:\**\s*", "", escalation, flags=re.IGNORECASE)
                reason = "Cortex escalated: " + why[:200]
                banner(f"ESCALATE, handed to a human. Nothing posted, no commitments "
                       f"made. Run cost ≈ ${bounds.cost:.4f}")
                finish("escalate", reason, proposed)
                return
            # Escalate trigger 2: a status color change is the human's call (M1 #4).
            color = proposed_status(proposed)
            prior = last_approved_status(project_id)
            if color is None:
                reason = "draft has no STATUS line, so the status color check can't run"
                banner(f"ESCALATE, {reason}. Draft saved, needs your call.")
                finish("escalate", reason, proposed)
                return
            if prior and color != prior[0]:
                reason = (f"status would change {prior[0]} -> {color} vs last approved "
                          f"update ({prior[1]}); your call (M1 #4)")
                banner(f"ESCALATE, {reason}. Draft saved, needs your call.")
                finish("escalate", reason, proposed)
                return
            missing = [t for t in REQUIRED_SOURCES if t not in pulled]
            if missing:
                reason = (f"required source {', '.join(missing)} never returned data, so "
                          f"the draft can't be grounded (M4 withheld-source rule)")
                banner(f"ESCALATE, {reason}. Draft saved, needs your call.")
                finish("escalate", reason, proposed)
                return
            banner(f"HITL CHECKPOINT, status update + any proposed stories queued for "
                   f"your review. Nothing posted, no commitments made. "
                   f"Run cost ≈ ${bounds.cost:.4f}")
            note = f"; status {color} matches last approved ({prior[1]})" if prior else ""
            finish("success", "validator passed" + note, proposed)
            return

        if fail_action(verdict.get("failed_checks")) == "block":
            checks = ", ".join(sorted(BLOCK_CHECKS & set(verdict["failed_checks"])))
            reason = (f"critic BLOCKED on check {checks} (Above risk, not revised): "
                      + "; ".join(verdict.get("reasons", []))[:300])
            banner(f"BLOCKED by critic on check {checks}. Nothing sent back to Cortex; "
                   f"escalating to a human. Run cost ≈ ${bounds.cost:.4f}")
            finish("escalate", reason, proposed)
            return

        if revisions >= MAX_REVISIONS:
            reason = f"validator rejected {MAX_REVISIONS}x (revision cap)"
            banner(f"REVISION CAP hit ({MAX_REVISIONS}). Escalating to a human "
                   f"instead of looping. Run cost ≈ ${bounds.cost:.4f}")
            finish("escalate", reason, last_draft)
            return

        revisions += 1
        print(f"\n-> critic rejected; revision {revisions}/{MAX_REVISIONS}")
        messages.append(msg)
        messages.append({"role": "user", "content":
                         "A validator rejected that for these reasons: "
                         f"{verdict['reasons']}. Fix it or escalate."})

    reason = f"max iterations ({MAX_ITERATIONS}) reached without finishing"
    banner(f"STUCK, {reason}. Halting. Run cost ≈ ${bounds.cost:.4f}")
    finish("stuck", reason, last_draft)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Cortex once.")
    parser.add_argument("which", nargs="?", default="happy",
                        help="task fixture: happy, missing-data, jailbreak")
    parser.add_argument("--force", action="store_true",
                        help="human-only: ignore today's marker (logged with who and why)")
    parser.add_argument("--reason", default="", help="why you are forcing a run")
    cli = parser.parse_args()
    if cli.force and not cli.reason.strip():
        parser.error('--force requires --reason "..." (logged with who and when)')
    run(cli.which, force=cli.force, force_reason=cli.reason.strip())
