# Demo runbook - Delivery

How to show the factory delivering its own work, from a person's intent to a
merge a human approved. Every figure here was measured on this machine; where
it varies between runs it says so.

The one sentence the room should leave with:

> The agent did everything up to the merge gate, and could not pass it.

The other runbooks: [Builds](DEMO_RUNBOOK_BUILDS.md),
[Runs](DEMO_RUNBOOK_RUNS.md), [Secures](DEMO_RUNBOOK_SECURES.md),
[Improves](DEMO_RUNBOOK_IMPROVES.md).

---

## 1. Before the room arrives

### Start the server

```
cd C:\Users\sahidul.i.shaikh\Documents\Project_Local\Learning\anti-money-laundering
uv run python scripts/serve_factory.py
```

Open **<http://localhost:8765>**. If the port is held, see
[the Builds runbook](DEMO_RUNBOOK_BUILDS.md#if-the-port-is-stuck), and check
nothing else answers on 8765 before you start:

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen
```

Exactly one process, started from the folder above. A server left over from
another folder serves old code silently - this cost an hour once.

### Pre-flight, three minutes

| Check | How | Expect |
|---|---|---|
| Console live | top right | green **live** |
| Bot identity | `uv run python -c "from aml.build import bot; print(bot.whoami(bot.verified_token()))"` | `aml-factory-bot` |
| GitHub reachable | `gh auth status` | logged in |
| Delivery history | **AI builds AI → 07 Delivery** | every task's chain; T-001 shows *owner override*, the rest approved |
| Rail | right edge of every page | the current task's stations |
| main is green | latest merge on GitHub | both checks passed |

### Windows

Console on the left, GitHub on the right, signed in **as yourself** (not the
bot). You approve on GitHub during the demo.

---

## 2. The demonstration (about 8 minutes)

### Beat 0 - Home (30 s)

Open **<http://localhost:8765>**: the home screen, with the four pillars
around the factory. Pick **T-006** in the rail's selector (top right) so the
rail follows the demonstration task. Click **AI builds AI**.

### Beat 1 - The intent (30 s)

On the rail, click the text under **Intent** ("Sahidul Shaikh - accepted").
The intent opens in the console.

> One person wrote what they want in plain words. The factory works from this
> file and nothing else, and the file is in git with its author.

### Beat 2 - The plan, and the first human gate (about 1 minute)

**AI builds AI → 04 Loops.** Model `haiku`, **withhold the rule detail**
ticked. Press **draft a plan for this run**.

Rail: **Plan** pulses while Claude drafts (about 15 to 30 s, under a cent),
then turns amber, "waiting for a human". The plan appears in the panel; it can
also be opened from the rail.

> Nothing is built without a plan a person accepted. The plan was drafted from
> the intent and the same withheld contract the build gets, so it cannot give
> the answer away - notice it says where the contract is silent.

Press **accept plan - start the build**. Your GitHub login is recorded as the
person who accepted it, and travels with the delivered PR (`Plan-Accepted-By`
trailer and the plan file).

### Beat 2b - The build loop (about 2 minutes)

Accepting the plan starts it. Watch the rail: **Build loop** pulses,
"attempt 1 of 3".

> Part of the contract is withheld. The first attempt has to guess. A test
> suite it has never seen is about to tell it where it guessed wrong.

Attempt 1 fails (usually 19 of 20; the date format), then "attempt 2 of 3",
then 20 of 20.

| Measured since the T-003 fix (4 runs, rules withheld) | |
|---|---|
| Attempt 1 failed | 4 of 4 |
| Passed on attempt 2 | 3 of 4 |
| Refused after 3 attempts | 1 of 4 |
| Duration | 90 to 134 s |
| Cost (reported by Claude Code) | $0.009 to $0.019 |

**If the loop refuses** (it has, once in four): say so. That is the gate
working - nothing is delivered. Run it again, or show the recorded card at the
bottom of the Loops panel, which is a real fail-then-pass run.

### Beat 3 - Deliver (automatic, about 50 s)

Nothing to press. As soon as the loop passes, the factory delivers it to
T-006 - the only task whose intent accepts factory deliveries. Watch the rail:

| Rail | Measured |
|---|---|
| **Commit** pulses: "committing, scanning for real data, pushing" | about 40 s |
| **Pull request** pulses: "opening the pull request" | about 8 s |
| Both green, with the PR number | |

> The factory has its own GitHub identity, aml-factory-bot. It just committed
> the code with the run's provenance in the commit, checked nothing real had
> leaked into it, pushed a branch and opened a pull request. It cannot do the
> next step.

If the loop refused, nothing is delivered and the rail says so. If a
delivery itself is refused (shown in red on Commit, with the reason),
**07 Delivery → deliver latest passing run** retries it by hand.

Open the PR. Point at:
- **Author: aml-factory-bot.**
- **Files:** the detector, its tests, and the run record.
- **The commit trailers:** task, model, run ID, each attempt's result, cost.

### Beat 4 - CI (about 2 minutes)

Rail: **CI** pulses, "1 of 2 running". Pillar checks finish in about 15 to 20
s; the **attack suite** takes about 90 s because it fires real injection
payloads at a real model.

> The attack suite is a required check. A change that weakens the defences
> cannot merge. Beat 6 shows that happening.

### Beat 5 - The human decision (1 minute)

Rail: **Human approval** turns amber, "waiting for a human", with a clock
running from the moment CI went green.

> Everything up to here was the agent. This step is not.

On GitHub, as yourself: **Files changed → Review changes → Approve → Submit
review**, then **Merge pull request**.

Within a few seconds the rail shows **approved by** you and **merged by** you;
in 07 Delivery all eight stations of T-006 are green.

> There is no approve button in this console, and the bot cannot approve its
> own work - GitHub enforces that, for everyone including the repository
> owner.

### Beat 6 - A security regression is blocked (2 minutes)

Open the standing **"DEMO - do not merge: envelope removed"** PR.

> Someone simplified a function and removed the untrusted-data envelope.
> Every other check passes. The attack suite does not.

Show **attack suite: failed** and the merge box: **required check failing**.
Optional: press **Re-run jobs** and let it fail again live (about 90 s).

---

## 3. Questions you will get

**"Could the bot just approve its own PR?"** No. GitHub does not let an author
approve, and branch protection requires an approval and both checks on main,
enforced for administrators too.

**"What is the 'owner override' on T-001?"** The first task was merged by the
repository owner bypassing review, before protection applied to administrators.
The console shows it as an override rather than pretending it was approved.

**"Is CI testing real customer data?"** No. The real alert extract never leaves
this machine; CI runs the same checks on synthetic alerts
(`AML_SYNTHETIC_ONLY=1`). CI proves the controls work; it makes no accuracy
claim about real alerts.

**"What stops someone committing the real data?"** A pre-push hook scans every
commit for names, tax IDs, account numbers, dates of birth and transaction
references from the real workbook, and refuses the push. Delivery runs the same
scan itself before pushing.

**"What did this cost?"** Each loop run's cost is reported by Claude Code and
carried in the commit (`Cost-USD`). Interactive engineering sessions say "not
measured" rather than guessing.

---

## 4. When something goes wrong

| Symptom | Cause | Do |
|---|---|---|
| Rail: Build loop red, "refused, nothing to deliver" | The loop failed three attempts (seen live, 1 run in 4) | Run the loop again |
| Rail: Commit red, "delivery refused: ..." | Read the reason on the rail | Fix it, then **07 Delivery → deliver** to retry |
| "... was already delivered as ..." | That run already has a PR | Run the loop again for a new run |
| "does not accept factory deliveries" | Wrong task chosen | Use T-006 |
| Rail stays on the wrong task | Rail selector | Pick T-006 in the rail's selector |
| "token belongs to ..., not aml-factory-bot" | Wrong or missing token | Replace `%USERPROFILE%\.aml-factory-bot\token.txt` |
| Rail says "Delivery state unavailable" | `gh` not logged in or offline | `gh auth status` |
| A panel shows "Not wired yet" | Fixed in T-005; an old server | Restart from the folder above |
| CI red on the delivered PR | Read the failing check | Do not merge; the gate is doing its job |

---

## 5. Between demonstrations

Nothing to reset. Each run gets a new run ID and each delivery a new pull
request against T-006. Merging one updates the detector on main with a
reviewed, provenanced version.
