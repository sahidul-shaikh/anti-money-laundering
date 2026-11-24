# AI Engineering Factory — AML Alert Investigator

A four-pillar demonstration that an AI estate can be **built, run, secured and
improved by AI**, under governance a regulator would accept, proved against one
real product: an AML alert investigator.

This folder is **self-contained**. Everything needed to run and extend the
system is here; nothing outside it is required.

## Quick start

```bash
uv sync
uv run python scripts/serve_factory.py     # http://localhost:8765
```

All four pillars and all 18 panels are enabled.

```bash
for f in checks/aml_check_0*.py; do uv run python "$f"; done
```

Five checks, each printing `ALL CHECKS PASS`.

## Where to start reading

**[`START_HERE.md`](START_HERE.md)** — then `brief/01` through `brief/07`.

| | |
|---|---|
| [`START_HERE.md`](START_HERE.md) | Orientation and reading order |
| [`INITIAL_PROMPT.md`](INITIAL_PROMPT.md) | The prompt to kick off a new session |
| [`CLAUDE.md`](CLAUDE.md) | Conventions, invariants and known pitfalls |
| [`brief/`](brief/) | Seven briefing notes: what this is, the use case, how it is built, what exists, how to run it, what to build next, and the pitfalls |
| [`design/`](design/) | 26 documents: the production design for this product |
| [`docs/`](docs/) | Presenter runbooks, use case, architecture, repo map |

## What is in here

```
aml/           the investigator and the build factory
scripts/       the console server, its UI, and the batch scripts
library/aml/   13 reusable skills, 19 pattern assets, 28 extracted rules
checks/        five pillar checks and the withheld acceptance suite
artifacts/     the 70-alert corpus, recorded runs, the generated detector
design/        requirements, HLD, LLD, data model, DDL, API, security,
               model risk, test, operations, delivery plan, SDLC method
docs/          runbooks and reference
AntiMoneyLaundering/   the source spreadsheets
```

## Three things to know before you touch it

1. **The data is real.** `AntiMoneyLaundering/Alert_Final_table.xlsx` is an
   extract of genuine transaction-monitoring alerts with named individuals,
   dates of birth, occupations and incomes. Treat it as confidential.
2. **The agent recommends; a human decides.** It cannot close an alert, file a
   report or write to a party record — the capability is unregisterable, not
   merely ungranted. Preserve that.
3. **Every figure is measured.** Nothing in the console is estimated, and there
   is deliberately **no accuracy claim** — see `brief/04`.
