# Value Contract — AML Alert Investigator

## BASELINE

GBP 17.00 per alert, fully burdened Level-1 analyst cost, one review per alert, every time. This covers 20 to 40 minutes of analyst handling time per alert across the six in-scope scenarios (SAS10014, SAS10056, SAS10016, SAS10050, SAS10602, SAS10012), measured against current production alert volumes of several thousand alerts per day. Of this volume, greater than 95% currently close with no further action, meaning the baseline cost is overwhelmingly spent reaching a "no further action" outcome, not an escalation.

Source: stated analyst cost and handling time from the brief. No independent measurement has yet been taken of the per-scenario split of the 20-40 minute range; that split should be instrumented before the target is claimed as met (see TELEMETRY).

## TARGET

GBP 12.00 per alert, fully burdened cost, inclusive of:
- Agent inference and retrieval cost per alert
- Residual analyst review time for the agent's recommendation (not a full re-investigation)
- Any human-in-the-loop escalation or close time, which remains unavoidable by design (the agent may never close or escalate an alert by itself)

Saving claimed: GBP 5.00 per alert (29% of baseline), realized only on alerts where the quality floor below is met. A saving achieved by trading against the floor — for example, by suppressing escalations to cut review time — is not a valid realization of this target and must be rejected regardless of the cost number it produces.

## QUALITY FLOOR

Two metrics are tracked separately because they carry asymmetric risk. They are never to be blended into a single "accuracy" figure.

**Recall (binding constraint): minimum 90% of alerts that should escalate must be recommended for escalation by the agent.**
Why this metric: a missed escalation is a missed suspicious activity report, which is a regulatory and criminal-exposure failure, not a cost-efficiency failure. Recall is measured against a labeled holdout set per scenario (SAS10014, SAS10056, SAS10016, SAS10050, SAS10602, SAS10012), each tracked independently — an aggregate recall of 90% that hides a scenario running at 70% does not satisfy the floor. Below 90% recall on any single scenario, the agent must not be deployed for that scenario, regardless of overall cost savings achieved elsewhere.

**Accuracy: minimum 85% of all dispositions (escalate or no-further-action) must match the correct outcome.**
Why this metric, and why it is secondary to recall: accuracy captures the false-positive side (unnecessary escalations that waste analyst time) as well as true negatives correctly dispositioned. It is the efficiency floor, not the safety floor. A build that clears 85% accuracy but fails 90% recall still fails the contract.

**Non-negotiable, by-construction floors (pass/fail, not a percentage):**
- Zero instances of a cited transaction reference that does not exist in the alert's own data. One such citation is a defect, not a quality statistic — it is logged and blocks release, not averaged into an accuracy score.
- Zero instances of the agent disclosing, implying, or allowing an analyst-facing output to reveal that a party is or has been the subject of a SAR, per 31 U.S.C. 5318(g)(2). This must be enforced structurally (the agent has no access to SAR-filing status as an input, or SAR status is hard-excluded from any generated text) — not by instructing the model to withhold it.
- Zero instances of payment reference or remittance free text being treated as an instruction (e.g., altering the disposition logic because the free text asserts a reason, status, or request). Free text is evidence to be cited, never a directive to be obeyed.
- 100% of dispositions must be reproducible: re-running the agent against the same recorded alert data and the same AML-SAM detection parameters must yield the same disposition and the same cited evidence, every time.

## TELEMETRY

Telemetry is named by the layer it sits at, so that a gap in one layer cannot be covered by a strong number at another.

**Detection layer (Actimize AML-SAM):** no new telemetry — thresholds and occurrence logic (e.g., AML-STR-CCE-INN-A-D01-DST: 8,000-9,999.99 inclusive, 3 occurrences, 14-day window, credits only) are taken as given and logged per alert as the detection parameters in force at alert time, so a disposition can later be tied to the exact rule version that fired.

**Agent output layer, per alert:**
- Automated citation check: every transaction reference string in the agent's output is matched against the transaction set supplied in that alert's input payload. Any unmatched reference is logged as a blocking defect, counted separately from the accuracy metric, and reported as a raw count and a rate per 1,000 alerts.
- SAR-disclosure guard: automated scan of agent output for SAR-status tokens or inferable SAR language, run on 100% of outputs, zero-tolerance alerting (not sampled).
- Free-text handling check: flag any disposition where a change in recommendation correlates with remittance/reference free text content, for manual audit sampling.

**Disposition layer, per alert:**
- Logged triple of (alert input snapshot, detection parameters in force, agent disposition + evidence) sufficient to replay the alert and get an identical output — this is what proves the reproducibility floor, not a policy statement.
- Human reviewer outcome (escalate / close / override) logged against the agent's recommendation to compute recall and accuracy per scenario, refreshed weekly against a rolling labeled sample, with per-scenario breakouts for all six in-scope SAS codes.

**Cost layer, per alert:**
- Metered inference cost, retrieval cost, and timed analyst review minutes captured per alert and converted to GBP at the same fully-burdened rate used for the GBP 17.00 baseline, so the GBP 12.00 target is measured on a like-for-like basis rather than inference cost alone.
- Reported as a trailing 30-day average per scenario, not a one-time benchmark.

**Sign-off:** model risk reviewer signs off against the recall and accuracy floors and the two zero-tolerance guards (citation, SAR-disclosure) before production release; engineering owns the cost and reproducibility telemetry. Neither party signs off on the target cost alone without the floor evidence attached.