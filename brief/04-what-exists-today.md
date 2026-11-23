# 04 — What exists today

An honest inventory. **Proven** means measured on this machine and
reproducible. Read this before you believe anything a panel says.

---

## Proven

| Capability | Evidence |
|---|---|
| Evidence-gated routing with escalation | Measured on the recorded baseline: cheap tier returned no citable evidence on 12 of 61 clean alerts, and was wrong on 67% of those against a 22% base rate |
| Deterministic groundedness | Pure function, unit tested, no model involved |
| Untrusted-data envelope, paired A/B probes | Same alert, same model, same payload; defended vs exploited measured per probe |
| Ungrantable destructive scopes | Raises at registration; the service does not start if violated |
| Versioned rule catalogue with page citations | 28 rules, 4 detection models, extracted from the 677-page Solution Guide |
| Ledger with cost per outcome | Every call and outcome written once; all figures computed from it |
| Failure clustering, paired sign test, refusing gate | The gate has refused a real cost-saving change for losing recall |
| The build loop fails then passes | **Attempt 1 failed 8 times out of 8**; 7 of 8 closed on attempt 2; 92–152 s, $0.010–$0.018 |
| The handicap, not the model, causes that failure | Same stage with the full requirements passes 20/20 first time, 3 of 3 |
| Prompt-cache probe | `amazon.nova-lite-v1:0` wrote 540 tokens and read 540 back; both serving models refuse with `AccessDeniedException` |
| Console integrity | 17 panels, 0 JS errors; all five checks pass — re-verified from this folder |

## Partial

| Capability | What is missing |
|---|---|
| `run_id` as the universal join key | Present for model calls; **absent for security probes and evaluation runs**, which write to separate artifact files. The "one spine, four pillars" claim is not yet queryable |
| Tokenomics | The lever is real and measured, but unavailable: both serving models refuse prompt caching, and the one that caches is the one the quality gate rejected |
| Consolidation | The data supports it — 6 of 25 real cases carry 2–4 alerts — but `case_id` is a string on the alert, not an entity |

## Not built

| Capability | Note |
|---|---|
| **Case as an entity** | Alerts and cases are many-to-many in reality; we collapse them |
| **Evidence capture with hashing and snapshots** | Citations are checked against the alert in memory; nothing is captured, hashed or retained |
| **Decision, actor and override records** | *"A human reviews every escalation"* is true operationally but **recorded nowhere**. No field says who decided |
| **Outcome / adjudication / label separation** | The label trap in `brief/02` is described in the design and not implemented |
| Counterparty and relationship data | Two of six scenarios cannot really be reasoned about |
| Asset / release / deployment registry | Config changes are approved by the gate but not versioned or hashed |
| Report drafting and versioning | Deliberately — the agent never files |

---

## No accuracy claim

**There has been no 70-alert re-baseline since the rule catalogue changed.**
Do not quote an accuracy or recall figure from this system. The defensible
numbers are the per-model quality figures in the fleet (3/8, 6/8, 8/8
escalation recall, measured 2026-11-09) — and they are a small sample.

This is not modesty. Quoting a number that cannot be reproduced is the one
thing that would discredit the whole demonstration.

---

## Known defects and open threads

| # | Item |
|---|---|
| 1 | **`PRD.md` §5.2 contradicts the implementation.** The PRD says a human reviews every escalation *and every close*; the system reviews only escalations. The saving case depends on which is true. Unresolved, and tracked as ISS-001 in `design/22-raid-log.md` |
| 2 | Dead code: superseded panels in `builds.js` / `runs.js` / `secures.js` / `improves.js`; `fleetTable` in `runs.js` |
| 3 | The schema in `design/11-database-schema.sql` is syntax-checked but **never applied to a live PostgreSQL instance** (ISS-007) |
| 4 | Two probes (P-09, P-10) are **declared but deliberately not executed** — the panel says so. Keep it that way |
| 5 | Stage 2 (detector as a tool) and Stage 3 (semantic retrieval) of the agent roadmap are unbuilt |
| 6 | `pyproject.toml` in the parent repo declares `packages = ["factory"]` but the package is `aml/` — **already corrected in this folder** |

---

## The repository is not under version control

The parent repository has **zero commits and no remote**. Everything built so
far exists only as working-tree files.

This matters for you in two ways:

1. There is no history to consult. The design documents and these briefs are
   the record.
2. **It is the first thing worth fixing**, and it is part of your brief — see
   `brief/06`. `design/24-ai-native-sdlc-method.md` asserts that "the commit
   history is the audit trail" in a repository that has never been committed
   to. Closing that gap is the natural first move.
