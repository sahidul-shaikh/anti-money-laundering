# Value Contract — AML Alert Investigator

## BASELINE

GBP 17.00 per alert, fully loaded, covering one Level-1 analyst spending 20 to 40 minutes per alert to assemble evidence, decide disposition, and write a rationale. This is measured across the current transaction-monitoring estate, which fires several thousand alerts a day, over 95% of which close with no further action. The baseline is the cost of the status quo: every alert gets one full manual review regardless of how likely it is to be a true positive.

## TARGET

GBP 12.00 per alert — a reduction of GBP 5.00 (29%) against the GBP 17.00 baseline. The saving is realised by the agent assembling evidence and drafting a disposition so the analyst reviews a recommendation instead of starting from nothing, cutting analyst handling time per alert. The target is measured on the same unit as the baseline (GBP per alert, fully loaded) so the two numbers can be subtracted directly; it is not a blended or estate-wide figure.

## QUALITY FLOOR

The floor is independent of the cost target: a cheaper alert that fails any of these is not a win and must not ship.

- **Recall on alerts that should escalate: minimum 90%.** This is the number that matters most because the cost of a false negative (a missed escalation) is a missed suspicious activity, not an inefficiency — it carries regulatory and criminal exposure, unlike a false positive, which only costs analyst time. Recall is measured as (true escalations correctly recommended) / (all alerts whose final, human-adjudicated disposition was escalate), kept separate from overall accuracy so the asymmetry between the two error types is never hidden in a single blended number.
- **Overall disposition accuracy: minimum 85%.** Measured as agent-recommended disposition matching the human-adjudicated final disposition, across all six in-scope scenarios, on a labelled sample independent of the recall calculation above.
- **Citation integrity: 100%, zero tolerance.** Every claim the agent makes must cite a transaction reference that exists in the alert it was given. A citation that does not resolve to data present in that alert is a defect, not a stylistic issue, and blocks release of that disposition — this is checked per alert, not sampled.
- **SAR confidentiality: zero disclosure events, enforced by construction.** Disclosure that a party is under a suspicious activity report is a criminal offence under 31 U.S.C. 5318(g)(2). This cannot be a trained-in behaviour or an instruction the model is asked to follow — the agent's input and output schemas must have no field, path, or prompt surface through which a SAR-indicator or filing-status value can enter or leave. This is a model risk reviewer sign-off gate, not a metric that can be traded against cost or recall.
- **Human closure: 100%.** The agent never closes or escalates an alert itself. Every output is a recommendation; every escalation and every close is a human action. There is no autonomous-disposition code path to disable in production, by configuration, or under load.
- **Reproducibility: 100%.** Every disposition must be reconstructable after the fact from what was recorded alone — the alert payload, the Actimize AML-SAM rule parameters applied (e.g. AML-STR-CCE-INN-A-D01-DST: lower bound 8,000, upper bound 9,999.99 inclusive-exclusive per the out-of-scope-at-10,000.00 rule, 3 occurrences, 14-day inclusive window, credits only), and the rationale text. If a disposition cannot be replayed from the audit record, it is a build defect.

## TELEMETRY

- **Ingestion layer:** alert volume processed per day, broken out by the six in-scope scenarios, logged at intake from the case management feed (read-only; case management itself is out of scope for this build).
- **Evidence/citation layer:** an automated validator runs on every disposition before it reaches an analyst, cross-checking each cited transaction reference against the source alert's transaction list. Logged per alert as citation-pass or citation-fail. Target: 0 failures in production; any failure is routed as a blocking defect, not a quality-score deduction.
- **Disposition/outcome layer:** agent-recommended disposition vs. the analyst's final action, captured at the point the analyst acts, aggregated weekly into a confusion matrix yielding recall and accuracy as defined under QUALITY FLOOR (tracked separately, never blended).
- **Cost layer:** analyst time-on-alert from case management timestamps (open to disposition-accepted), converted to GBP per alert using the same fully-loaded rate used to establish the GBP 17.00 baseline, so BASELINE and TARGET stay comparable over time.
- **Confidentiality gate:** a build-time and release-gate architecture check (schema review, not a runtime sample) confirming no SAR-indicator or filing-status field is reachable from alert input through to agent output or rationale text. Signed off by the model risk reviewer before each release, re-run on every schema or prompt change.
- **Reproducibility log:** every disposition's audit record (alert snapshot, rule parameters applied, rationale, model/prompt version) is stored and periodically replayed on a sample to confirm the recorded disposition is regenerated identically.

**Sign-off:** this contract is signed by the model risk reviewer (quality floor and confidentiality gate) and the Level-1 operations owner (baseline, target, and cost telemetry) before any production deployment.