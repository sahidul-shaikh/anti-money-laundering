# START HERE

You are picking up a working system, not a blank page. This folder is
self-contained: everything you need runs from here, and nothing outside it is
required.

**Read this file, then `brief/01` through `brief/07`, then start the console
and look at it before you change anything.**

---

## What this is in one paragraph

An **AI Engineering Factory** demonstration built around a single real use
case: an **AML alert investigator** that reads a transaction-monitoring alert
and recommends escalate / close / insufficient-information, with evidence. The
demonstration proves four pillars — **AI builds AI, AI runs AI, AI secures AI,
AI improves AI** — against that one product, with 18 live panels. Every panel
makes a real call against a real model and shows what it cost and whether it
was right. Nothing is mocked.

## What you are here to do

Extend it. Specifically, the **Builds pillar** should grow a real software
delivery spine: task creation, commits, pull requests, CI/CD and GitHub
workflow, so the factory does not merely *describe* governed delivery but
*performs* it. `brief/06-extension-brief.md` is the detailed statement of that
work, and `design/24-ai-native-sdlc-method.md` is the blueprint it should be
built against.

You are expected to think freshly. The existing build is evidence of what
works, not a constraint on what comes next.

---

## Read in this order

| # | File | Why |
|---|---|---|
| 1 | `brief/01-what-we-are-building.md` | The four pillars, the 18 disciplines, the argument |
| 2 | `brief/02-the-aml-use-case.md` | The problem, the real data, the value contract |
| 3 | `brief/03-how-it-is-built.md` | Module map and the path of one alert |
| 4 | `brief/04-what-exists-today.md` | **Honest inventory — proven, partial, not built** |
| 5 | `brief/05-running-it.md` | Start the console; run the checks; the live panels |
| 6 | `brief/06-extension-brief.md` | **What to build next** |
| 7 | `brief/07-conventions-and-pitfalls.md` | Hard-won operational knowledge; read before debugging anything |

Then, as needed:

| Need | Read |
|---|---|
| The product's target architecture | `design/05-high-level-design.md`, `design/10-data-model.md` |
| Why a thing is the way it is | `design/06-architecture-decision-records.md` (18 ADRs) |
| **The delivery method you are extending into** | `design/24-ai-native-sdlc-method.md` |
| How to present a pillar | `docs/DEMO_RUNBOOK_*.md` |
| What is in the repo | `docs/REPO_MAP.md` |

Do not read all 26 design documents up front. They are the target design for a
production build, not required context for extending the demonstration.

---

## First thing to run

```bash
uv sync                                  # once
uv run python scripts/serve_factory.py   # then open http://localhost:8765
```

All four pillars and all 18 panels are enabled. Verified working from this
folder: **18 panels, 0 JavaScript errors, all five checks passing.**

```bash
for f in checks/aml_check_0*.py; do uv run python "$f"; done
```

---

## Three things that are true and easy to get wrong

1. **The data is real.** `AntiMoneyLaundering/Alert_Final_table.xlsx` is an
   extract of genuine transaction-monitoring alerts with named individuals,
   dates of birth, occupations and incomes. Treat it as confidential. Do not
   send it anywhere, do not commit it to a public remote, do not put party
   names in logs.

2. **The honesty discipline is the product.** Every figure shown is measured on
   this machine and reconciles to one ledger. If you add a panel, it must
   measure something real or say plainly that it does not. A number nobody can
   reproduce is worse than no number.

3. **The agent recommends; a human decides.** It cannot close an alert, file a
   report or write to a party record — not by permission, but because the
   capability is unregisterable. Preserve that property in anything you add.

---

## What is deliberately not here

| Absent | Why |
|---|---|
| The AP-invoice and supplier-contract demos | Superseded; this is AML only |
| `Actimize AML SAM 8.5.0 Solution Guide.pdf` (8 MB, confidential) | Already extracted into `library/aml/rules.json`; not needed at runtime |
| `node_modules/`, `.venv/` | Rebuilt by `uv sync` / `npm install` |
| Decks and slide renders | Not needed to extend the system |
| `artifacts/live/*.events.jsonl` | Write-only stream logs, 1.8 MB, never read back |
