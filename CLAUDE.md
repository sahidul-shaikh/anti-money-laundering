# AI Engineering Factory — AML Alert Investigator

A four-pillar demonstration (AI builds / runs / secures / improves AI) built
around one real product: an AML alert investigator that reads a
transaction-monitoring alert and recommends escalate / close /
insufficient-information, with evidence.

**New here? Read `START_HERE.md`, then `brief/01` … `brief/07`.**

## Commands

```bash
uv sync                                       # once
git config core.hooksPath .githooks           # once per clone: pre-push refuses real customer data
AML_SYNTHETIC_ONLY=1 uv run python checks/aml_check_00_foundation.py   # how CI runs: synthetic data only
uv run python scripts/serve_factory.py        # console on http://localhost:8765
for f in checks/aml_check_0*.py; do uv run python "$f"; done   # all five must print ALL CHECKS PASS
uv run --no-project --with playwright python <script>          # Playwright is NOT a project dep
```

Restart the server after changing `scripts/serve_factory.py` or anything in
`aml/`. A browser reload is enough for `scripts/ui/`.

## Architecture

```
aml/corpus    the 70 alerts: load, synthesise, render
aml/run       config, prompts, rules, routing, engine, verdict, telemetry, chat
aml/llm       fleet, Bedrock, router          (the ONLY place we call a model)
aml/security  envelope, payloads, probes, scopes, emission guard
aml/improve   contract, bands, mining, optimise, tokenomics
aml/build     the twelve-stage factory and the act-verify-iterate loop
aml/core      the ledger — single source of every figure
scripts/ui    the console; panel host element is #dpanel
library/aml   13 reusable skills, 19 pattern assets, rules.json (28 rules)
checks/       five pillar checks + the withheld acceptance suite (the oracle)
design/       26 documents: the production design for this product
```

Dependency direction: everything may use `core`; `corpus` and `llm` know
nothing of `run`; `improve` sits on top.

## Conventions

- Be simple. Work incrementally — small steps, validated before moving on.
- Do not overengineer. Do not program defensively.
- **Find the root cause before fixing.** Reproduce, prove, then fix. No
  workarounds.
- `uv` always: `uv run …`, never bare `python`; `uv add …`, never `pip install`.
- Short modules, short functions, clear names. Docstrings yes, commentary no.
- **No emojis** in code, prints or logs.

## Invariants — do not break these

1. The agent recommends; a human decides. Destructive scopes
   (`alert.close`, `sar.file`, `party.write`, …) are **unregisterable**, not
   merely ungranted — `aml/security/tools.py`.
2. Nothing the agent writes reaches a customer — `aml/security/emit.py`.
3. Attacker-controlled text (`transaction.reference_text`) is data, never
   instruction. Always rendered inside the envelope — `aml/security/envelope.py`.
4. Groundedness is **computed, never judged by a model** — `aml/run/verdict.py`.
5. One ledger. Every figure is derived from it; nothing is asserted twice.
6. The rendered alert carries **no label and no rationale** — `aml/corpus/render.py`.
7. "Declared" is not "tested". Probes P-09 and P-10 are declared and
   deliberately not executed. Keep it that way.

## Measurement discipline

Every number shown must be measured on this machine and reconcile to the
ledger. **There is no accuracy claim** — no 70-alert re-baseline since the rule
catalogue changed. When something cannot be done, say so and say why; the
Tokenomics panel is the model for this.

## Things Claude gets wrong here

- Panel routes are the long names: `threat-modelling`, `runtime-defense`,
  `failure-mining`, `value-engineering`. A short form renders an **empty panel
  with no error**.
- Never round-trip a source file through PowerShell `Get-Content` /
  `Set-Content` — it double-encodes UTF-8 and corrupts the file.
- Set `$env:UV_LINK_MODE = "copy"` on this machine; OneDrive breaks hardlinks.
- Do not pass `--tools ""` / `--setting-sources ""` to the build loop. Tried,
  measured, reverted at the operator's request.
- The build loop's feedback must carry **both** the previous attempt's code and
  the pass count. Remove either and attempt 2 regresses.
- Bash heredocs mangle backslashes — write a script file instead.

## Data handling

`AntiMoneyLaundering/Alert_Final_table.xlsx` holds **real named individuals**
with dates of birth, occupations and incomes. Do not send it to any external
service, do not commit it to a remote, do not log party names.

**Do not read `~/.aws/credentials` or `~/.aws/config`.** They are configured
and working; use the AWS API to confirm identity.

Pen-testing targets our own demonstration system and is authorised and
defensive.
