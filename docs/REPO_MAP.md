# Where things are

```
aml/            the AML Alert Investigator itself
  corpus/       the 70 alerts, loaded and rendered
  llm/          the fleet, Bedrock, the router
  run/          prompts, the rule catalogue lookup, routing policy, chat, scoring
  security/     the untrusted-data envelope, payloads, probes, scopes
  improve/      clusters, the sign test, the gate, tokenomics
  build/        the twelve-stage factory that produced the product
  core/         the ledger

scripts/        run_baseline, run_attacks, run_improve, run_build,
                build_rule_catalogue, write_demo_inputs, serve_factory
  ui/           the console - one module per pillar, panels.js last

library/
  aml/          18 build assets and 13 skills
  pillars.json  the console's copy, one line per discipline
  rules.json    28 Actimize rules extracted from the Solution Guide

checks/         aml_check_00..04 plus the withheld acceptance suite
artifacts/      corpus, recorded runs, generated build, demo paste files
design/         AMLI-* the conventional HLD/LLD set: requirements, ADRs,
                DFDs, data model, DDL, API, security, model risk, test,
                operations, traceability, RAID, the delivery plan and the
                AI-native SDLC method (how the programme itself would run)

docs/           USE_CASE.md      the problem and what we built
                ARCHITECTURE.md  the product, module by module
                DEMO_RUNBOOK_*   one per pillar, how to present it
                DISCIPLINE_REFERENCE.md, PILLAR_CONSOLE.md
decks/          the process and architecture slides, and the wireframes
                scripts/build_process_deck.js  -> AML_Process_And_Architecture
                scripts/build_pattern_deck.js  -> AI_for_AI_Pattern_And_Specs
AntiMoneyLaundering/   the source workbook and the Solution Guide

legacy/         the AP-invoice and supplier-contract demo, the hackathon
                folder, the superseded single-page console, and the checks
                that only exercised them. Nothing here is loaded by the AML
                console.
```

## Running it

```
uv run python scripts/serve_factory.py
```

Then <http://localhost:8765>. There is no second console any more - the four
pillars are all in this one.
