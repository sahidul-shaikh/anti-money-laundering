# 05 — Running it

## Setup

```bash
uv sync
```

Installs the project (editable) plus `boto3` and `openpyxl`. Python 3.12.

### Prerequisites already present on this machine

| Need | For | Check |
|---|---|---|
| AWS credentials with Bedrock access | Every live model call | `aws sts get-caller-identity` |
| `claude` on PATH | The Builds pillar runs headless Claude Code | `claude --version` |
| Node (optional) | Only the deck generators | `node --version` |

> **Do not read `~/.aws/credentials` or `~/.aws/config`.** They are configured
> and working. Use the AWS API if you need to confirm identity.

---

## Start the console

```bash
uv run python scripts/serve_factory.py
# → http://localhost:8765
```

Standard library only, binds `127.0.0.1:8765`. The landing page shows the four
pillars; **Explore capabilities** opens the discipline grid.

All 17 panels are enabled. Verified from this folder: **17 panels, 0 JavaScript
errors.**

### Routes

```
/factory#/builds/specs       /factory#/builds/context    /factory#/builds/skills
/factory#/builds/loops       /factory#/builds/graphs     /factory#/builds/evaluation
/factory#/runs/routing       /factory#/runs/reliability
/factory#/runs/observability /factory#/runs/finops
/factory#/secures/threat-modelling  /factory#/secures/runtime-defense
/factory#/secures/swarm
/factory#/improves/harness          /factory#/improves/tokenomics
/factory#/improves/failure-mining   /factory#/improves/value-engineering
```

Note the full names: `threat-modelling`, `runtime-defense`, `failure-mining`,
`value-engineering`. Short forms render an empty panel with no error.

---

## The checks

Five pillar checks, each printing `ALL CHECKS PASS` or failing loudly. Run them
before and after any change.

```bash
for f in checks/aml_check_0*.py; do uv run python "$f"; done
```

| Check | Covers |
|---|---|
| `aml_check_00_foundation.py` | Corpus integrity, labels, rendering excludes labels |
| `aml_check_01_run.py` | Routing, verdict parsing, grading, telemetry |
| `aml_check_02_secure.py` | Envelope, payloads, scopes, emission guard |
| `aml_check_03_improve.py` | Contract, bands, mining, gate |
| `aml_check_04_build.py` | The factory, the acceptance suite, the tamper demos |

`checks/acceptance/test_detector_contract.py` is the **oracle** — 20 tests the
build stage never sees. Treat it as a fixed contract. If generated code and the
suite disagree, the code is wrong.

---

## Live panels: cost and time

Every one of these makes real model calls and costs real money.

| Panel | Press | Takes | Costs |
|---|---|---|---|
| Builds / Loops | run the implementation stage | ~2 min, two attempts | $0.01–0.02 |
| Builds / other stages | run the stage | 60–120 s | ~$0.01 |
| Runs / Reliability | send | 20–40 s | pennies |
| Secures / Pen-testing | send both | ~30 s | pennies |
| Improves / Harness | walk through it | ~40 s | pennies |
| Improves / Tokenomics | run the cache probe | ~25 s | pennies |

**Builds / Loops is the one to run before an audience arrives.** It is the
longest beat, and the third card — *the last loop recorded on this machine* —
fills in from the previous run and tells the same story in ten seconds if you
are short of time.

---

## Batch scripts

Each writes its evidence to `artifacts/` so a claim can be checked later.

```bash
uv run python scripts/run_baseline.py        # whole corpus per serving tier — slow, ~15 min
uv run python scripts/run_attacks.py         # the swarm, envelope off then on
uv run python scripts/run_improve.py         # detect, mine, propose, evaluate, gate
uv run python scripts/run_build.py           # the twelve-stage factory end to end
uv run python scripts/build_rule_catalogue.py  # needs the Solution Guide PDF (not in this folder)
```

---

## Testing the UI

Playwright is **not** in the project environment. Run it standalone:

```bash
uv run --no-project --with playwright python your_script.py
```

A sweep script that drives all 17 panels and reports JS errors is the fastest
way to confirm you have not broken anything. The panel host element is
`#dpanel`.

---

## Restarting after a change

The server must be restarted to pick up changes to `scripts/serve_factory.py`
or anything in `aml/`. UI changes in `scripts/ui/` need only a browser reload.

```bash
# free the port, then restart
# (PowerShell) Get-NetTCPConnection -LocalPort 8765 -State Listen
```
