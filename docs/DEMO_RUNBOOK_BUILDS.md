# Demo runbook - AI builds AI

How to operate the pillar console in front of an audience. Every number in here
was measured on this machine; where a figure varies between runs it says so.

This covers the **AI builds AI** pillar. The other three have their own runbooks:
[Runs](DEMO_RUNBOOK_RUNS.md), [Secures](DEMO_RUNBOOK_SECURES.md) and
[Improves](DEMO_RUNBOOK_IMPROVES.md). All four are now in this console - see
[Running the other pillars](#running-the-other-pillars).

**Before the console.** [USE_CASE.md](USE_CASE.md) is the problem, the data and
what we are claiming - read it first if you have not presented this before.
[ARCHITECTURE.md](ARCHITECTURE.md) is how the product is put together, for the
engineer in the room who asks.

---

## 1. Before the room arrives

### Start the server

```
cd "C:\Users\sahidul.i.shaikh\OneDrive - Accenture\Documents\Project\AI_For_AI"
uv run python scripts/serve_factory.py
```

Leave that terminal running. Open **<http://localhost:8765>**.

> Open the URL, never the HTML file. Served from disk the API is cross-origin and
> every live control goes dead.

### If the port is stuck

`Ctrl+C` does not always release it, and `pkill` does not work on Windows. In a
PowerShell window:

```powershell
Get-NetTCPConnection -LocalPort 8765 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

Run it twice if the first pass reports the port still held, then start the
server again.

### Pre-flight, two minutes

1. Top right of the console reads **live** with a green dot. Grey means the
   server is not answering - restart it.
2. Go to **06 Evaluation**, press **run the acceptance suite**. It must say
   `20 passed, 0 failed`. This is the single best check that the repo is in a
   demonstrable state.
3. Go to **05 Graphs**. It must show 12 stages, 15 dependencies, 4 gates.
4. Have VS Code open on the repo, with the Explorer showing
   `artifacts/builds/aml-alert-investigator/`. You will be switching to it.

### Arrange your windows

Browser on the left two thirds, VS Code on the right third. Several beats show
a file on disk changing while the console streams - that only lands if both are
visible at once. A second monitor is better if you have one.

### What it costs to run the whole thing

About **$0.70 of Claude Code** if you run every live beat once, nearly all of it
in the loop. There is no Bedrock spend in this pillar.

---

## 2. Where you actually run a stage

This is the question to be clear on before you start. There are **three**
places, and they do different things.

| What you want to run | Where | How long | Cost |
|---|---|---|---|
| **Stage 0** - read the requirements and extract the brief | **01 Specs** -> *re-read the intent* | 12s | $0.05 |
| **Any of the eleven document stages** (value contract, spec, architecture, ...) | **02 Context** -> pick the stage -> *assemble* -> *run this stage live* | 45-90s | ~$0.06 |
| **The code stage** (stage 6, implementation) | **04 Loops** -> *run the implementation stage* | 90s-7min | $0.09-0.51 |

The code stage is deliberately **not** runnable from Context - press it there and
the console tells you to go to Loops, because that is where the attempt-by-attempt
table lives.

### Running a document stage, step by step

1. Go to **02 Context**.
2. Choose the stage in the dropdown - `1. Value contract` is the natural one to
   show first.
3. Press **assemble**. The prompt appears with a breakdown of what it is made of.
   Nothing has been sent yet and nothing has been spent. Say that out loud.
4. Press **open the artifact in VS Code**. The file it is about to write comes up
   in the editor.
5. Press **run this stage live**.
6. Expect **20 to 40 seconds of silence**. This is Claude Code starting up and it
   is unavoidable. Use it - read the prompt breakdown aloud, or point at the
   required headings in the status line.
7. The status flips to *first token after 26s; the file on disk is growing now*.
   Switch to VS Code. The file fills in.
8. When it finishes you get the evaluator verdict. For the value contract:
   `all 4 sections and 0 identifiers present`, PASS, plus a line saying the stage
   is gated and nothing downstream runs until a human approves.

Measured on the value contract with sonnet: **47.9s** total, 26s of it startup,
5,426 characters, **$0.0590**.

> Running a stage **overwrites** the document on disk. That is the point, and all
> twelve currently regenerate to a passing state - but see
> [If a live run leaves you worse off](#if-a-live-run-leaves-you-worse-off).

---

## 3. The run of show

Six disciplines, roughly 20 minutes if you show all of them, and they work in
order. The chips across the top are the navigation; `all disciplines` on the
right of any panel takes you back to the grid.

### Open on the use case, not the console

Two minutes, before anything is on screen. The full version is in
[USE_CASE.md](USE_CASE.md); the spoken shape is four beats:

1. **The problem.** A bank's transaction monitoring raises alerts. Each one
   goes to a human who reads the transactions and writes down a view. Most are
   false positives - salaries, trading rhythms, settlement cheques - and the
   contract prices that work at **GBP 17.00 an alert**. Tuning the rules down
   is not the answer, because the regulator is not interested in a cheaper
   control that catches less.
2. **The data is real.** 35 alerts out of a live extract, 828 transaction
   rows, 25 parties, 25 filed reports, and 28 detection rules lifted out of a
   677-page Actimize solution guide with the page numbers attached. Every
   alert in the extract escalated, so we added 35 synthetic alerts a competent
   investigator would close - otherwise an agent could score full marks by
   escalating everything.
3. **What we built.** An alert investigator that recommends close, escalate or
   insufficient information, and cites the transactions it relied on. Three
   boundaries are in the code, not on a slide: it can never file or close
   anything, a human reviews every escalation, and nothing it writes may
   disclose that a party is under suspicion.
4. **What we are claiming.** Not accuracy - there has been no re-baseline since
   the rule catalogue changed. What we are claiming is that the thing was
   built, run, attacked and improved by AI, in front of you, with the
   measurement visible each time.

Then open the console.

### Open on the landing page

`http://localhost:8765` shows the pillar hero and the ring. Thirty seconds:
four pillars, this is the first, six disciplines under it, every one backed by
something in the repo. Press **Explore capabilities**.

### 01 Specs - "who decided it was AML?"

The question this answers: a person did. The panel is a text box, so you can
write or paste the requirement in the room.

1. Press **load what is on disk**. `PRD.md`, 6,248 characters, written by hand -
   the only human-authored input in the entire build.
2. Optionally edit it, or paste a different requirement over the top, then press
   **save it**. The previous requirement is kept in `PRD.md.bak`, so a paste is
   always reversible.
3. Press **stage 0: read it**. Claude Code reads the document and proposes a
   structured brief - product, domain, who raised it, and the constraints it
   found.
4. Press **approve the brief**. Say clearly: *a model proposed this, a person
   approved it, and the approval is the control.*

> Paste something materially different and the brief changes with it. That is
> the point worth making: nothing downstream is hardcoded to anti-money
> laundering.

### 02 Context - what the model is actually sent

1. Stage already on `2. Specification and threat model`. Press **assemble**.
2. 12,750 characters, broken into: standing preamble and approved brief 2,713,
   this stage's instruction 741, **skills attached 3,248**, what earlier stages
   produced 6,048.
3. The point: context is *composed*, not accumulated. A stage cannot see what it
   does not depend on. And it costs nothing to inspect - no model was called.
4. Optional: tick **withhold the rule detail**, switch to `6. Implementation`,
   assemble again. The requirements block is replaced by a thin contract. This
   sets up the Loops beat.
5. If you want a live document stage here, follow
   [Running a document stage](#running-a-document-stage-step-by-step) above.

### 03 Skills - the compounding asset

1. 13 skill files, 15,675 characters, all 13 attached to a stage.
2. Click **threat-modelling** in the list. 2,006 characters - and scroll to the
   threat library: injection through attacker-controlled free text, tipping off
   under 31 U.S.C. 5318(g)(2), excessive agency, threshold inference.
3. Click **implementation**. It warns about the window off-by-one and the
   exclusive upper bound - *the two defects models actually produced here.*
4. The line to land: the code is specific to this product, the way of working is
   not. These files are what the next build inherits.

### 04 Loops - goal, act, verify, iterate

**Timing.** Each attempt is a headless Claude Code call, 60-80 seconds on
haiku, which is the default in the picker. The loop settles in **two
attempts**: the first comes back 19 of 20, the acceptance suite names the one
it got wrong, the second passes. Across eight consecutive measured runs,
**attempt 1 failed every time** and seven of the eight closed on attempt 2;
92-152 seconds, $0.010-$0.018. Budget **two minutes** and have something to
say while it runs.

**Why attempt 1 reliably fails, and why that is honest.** Transactions arrive
as `YYYYMMDD`. The case management system the detector feeds takes ISO-8601, so
`window_start` and `window_end` come back as `YYYY-MM-DD`. That is a real
integration convention and it is nowhere in the handicapped brief - it lives in
the acceptance suite, which is exactly where conventions like it live in
practice. No model can infer it, so every first attempt echoes the input format
and fails one check. Hand the same stage the full requirements, where the
convention is written down, and it passes 20/20 on the first attempt - measured
three times out of three. **The failure is caused by the missing information,
not by the model.**

Two attempts rather than three because the feedback now carries two things the
next attempt cannot work without: the pass count (*19 of 20 already pass,
change only what failed*) and **the code it wrote last time**. Before that, the
turn was the original brief plus the pytest output - the module it was being
asked to correct was not in it, so it rewrote from memory and sometimes
produced a different, worse one. Worth saying out loud: the two corrections
that made this loop converge were both changes to what the verifier tells the
builder, not to the builder.

**If the room is tight on time**, run the stage once before they arrive. The
third card on the panel, *the last loop recorded on this machine*, fills in
from that run and shows every attempt with its timing - the same story, in ten
seconds, with the live button still there if you want it.


**Read [the measured record](#the-loop-converges-in-two-and-attempt-1-always-fails)
before you run this.** It is the longest beat on the pillar.

1. Walk the four steps at the top.
2. Leave **withhold the rule detail** ticked. Say the handicap out loud: the
   signature and output keys go over, the output conventions the downstream
   system expects do not, and neither do the boundary, window and direction
   semantics do not. The first attempt has to guess.
3. Press **run the implementation stage**.
4. Attempt 1 appears, then after ~2 minutes its acceptance result. Expect a
   failure - typically `18 passed, 1 failed`.
5. Attempt 2 appears marked *carrying the failure back*. The pytest output was
   not summarised for the model, it was handed to it.
6. The verdict closes the beat either way: PASS if it converged, or BLOCKED after
   three attempts, which is the gate doing its job.
7. The card at the bottom replays the last loop recorded on this machine, so
   even if you skip the live run there is something real to show.

### 05 Graphs - enforced, not drawn

1. 12 stages, 15 dependencies, 4 gates, 4 forks, 3 joins.
2. Click **Model risk**. It waits for evaluation design, security review *and*
   code review. That is the interesting shape - evidence being assembled before a
   regulated document can be written.
3. Click **Implementation**. Marked CODE, and verified by an acceptance suite
   rather than by headings.
4. The line: the orchestrator raises rather than carrying on. A stage whose
   upstream has not passed does not start.

### 06 Evaluation - nothing marks its own homework

Two independent demonstrations. Both edit a real file and both run the real
check against whatever is on disk at that moment.

**The code.** The file path is printed on the panel:
`artifacts/builds/aml-alert-investigator/src/detector.py`. Open it in an editor
and change `upper_bound: float = 9999.99` to `9000.0` - do this in front of the
room, in whatever editor you like. Then press **run the tests**:

```
15 passed, 4 failed
```

and the four that failed are **marked in red in the list of nineteen below**:

```
01  three qualifying credits in window detect
02  refs are in date order whatever the input order
04  two qualifying credits do not reach the threshold
09  upper bound is inclusive
```

That is the point worth making: moving one number by a thousand pounds breaks
four specific, named promises, and the suite says which. Put it back, run them
again, and all nineteen pass.

**The document.** Same idea against `spec.md` - rename the heading containing
THREAT MODEL, by hand or with the button on that card, press **re-read the
document**, and the gate reports `required section missing: THREAT MODEL`.

Put both back before the next run-through.

### Close

Press **Next: AI runs AI** at the bottom. In the new console that pillar is not
built yet; switch to `/console` for it.

---

## 4. The tamper demos, exactly

These are the highest-value thirty seconds in the pillar, so use the edits below
rather than improvising - several plausible-looking tampers **pass**, which is
embarrassing live. See [the trap](#the-tamper-trap).

### Document tamper - recommended

File: `artifacts/builds/aml-alert-investigator/spec.md`

Search the file for the heading containing **THREAT MODEL** and rename the
words, leaving any numbering alone:

```
## 5. THREAT MODEL       ->   ## 5. Security notes
```

> Do not trust a line number here. The stage numbers its own headings, so
> re-running stage 2 can move `## THREAT MODEL` to `## 5. THREAT MODEL` or
> renumber it again. Search for the words, not the line.

Then in **06 Evaluation**, stage `2. Specification and threat model`, press
**re-evaluate**:

```
BLOCKED   required section missing: THREAT MODEL
```

Undo the rename, press re-evaluate again:

```
PASS      all 2 sections and 2 identifiers present
```

Alternative, if you would rather tamper with the value contract: in
`contract.md`, rename the heading containing `QUALITY FLOOR` to
`## Minimum standards`.

### Code tamper - recommended

File: `artifacts/builds/aml-alert-investigator/src/detector.py` - find the
`upper_bound` default in the `detect_structuring` signature

```python
upper_bound: float = 9999.99     ->     upper_bound: float = 9000.0
```

Then **run the acceptance suite**:

| Edit | Result |
|---|---|
| `upper_bound` 9999.99 -> 9000.0 | **15 passed, 4 failed** |
| `occurrences` 3 -> 4 | 12 passed, 7 failed |
| `lower_bound` 8000.0 -> 8001.0 | 18 passed, 1 failed |
| `window_days` 14 -> 13 | 18 passed, 1 failed |

`occurrences` is the most dramatic if you want the biggest number. `upper_bound`
is the most explicable - it is a regulatory boundary, moved by one band.

Restore the value and run it again to get back to `20 passed, 0 failed`.

### The tamper trap

Renaming **`## TELEMETRY`** in `contract.md` **does not block**, and neither does
deleting the line. The word appears in three headings in that document, and the
evaluator only needs the marker to appear in one of them. An older guide
recommended this edit; it no longer works.

The rule: only tamper with a heading whose marker word appears **once** in the
document. Verified single-hit markers are `THREAT MODEL` and
`ACCEPTANCE CRITERIA` in `spec.md`, and `BASELINE` and `QUALITY FLOOR` in
`contract.md`. Every other marker needs you to rename several headings before it
trips, which is not a demo.

---

## 5. Honest caveats, and what to say if asked

### The loop converges in two, and attempt 1 always fails

Eight consecutive runs on haiku with the handicap on, after the feedback began
carrying the previous attempt's own code back:

| Attempt 1 | Attempt 2 | Attempt 3 | Total |
|---|---|---|---|
| 18/20 | **PASS** | | 124s, $0.013 |
| 19/20 | **PASS** | | 114s, $0.012 |
| collection error | 19/20 | **PASS** | 153s, $0.018 |
| 19/20 | **PASS** | | 115s, $0.013 |
| 19/20 | **PASS** | | 103s, $0.011 |
| 19/20 | **PASS** | | 108s, $0.012 |
| 8/20 | **PASS** | | 152s, $0.017 |
| 19/20 | **PASS** | | 92s, $0.010 |

**Attempt 1 failed 8 times out of 8.** Seven of the eight closed on attempt 2.
The one that took three produced a file pytest could not even collect on its
first try - a bad generation rather than a wrong answer.

So you can say "watch it fail, then watch the loop fix it" and expect to be
right. What you cannot promise is the exact failure: usually it is the one
withheld convention, occasionally haiku also makes a mess of something else.
If it runs to a third attempt, or the gate refuses at the limit, that is the
mechanism working - a fixed attempt limit exists precisely because iteration is
not monotonic.

If you need a guaranteed clean result, untick the handicap: with the full
requirements the stage passes 20/20 on the first attempt in about 70 seconds,
measured three times out of three. You lose the failure, which is most of the
point.

### Where this build is weaker than it looks

Worth having ready, because a sharp audience gets there:

- **The twelve stages produce documents plus one module.** The running agent in
  `aml/run/` was written by hand, not emitted by the factory. Say so plainly.
- **The generated detector is never imported by the running agent.** The factory
  writes it and 20 tests prove it, and nothing consumes it yet. Wiring it in as a
  deterministic pre-filter would be better design than leaving a testable rule to
  a model.
- **The stages make no tool calls.** They are text generation with a verified
  output, not agents with filesystem access. The loop around the code stage is
  the agentic part.
- **The oracle has a gap.** Widening the window by one day in `detector.py`
  (`timedelta(days=window_days - 1)` -> `days=window_days`) still passes 20/20.
  The suite pins the lower edge of the window tightly and the upper edge loosely.
  If someone probes the oracle's completeness, concede it - and note that the
  suite catching four of five threshold mutations is the measurable claim, not
  that it is complete.
- **Claude Code's own Write tool was refused in headless mode.** The server tees
  the token stream to disk instead, which is why the file grows smoothly on
  screen. The write path is ours, not the model's.

### What the two model estates are

Asked twice before, so be ready. **Claude Code on the subscription builds** -
that is this entire pillar. **Amazon Bedrock runs** - that is the next pillar.
They are different estates and the costs are not comparable. There is no Claude
on Bedrock on this AWS account because it has no payment instrument, so the
Marketplace subscription cannot complete.

---

## 6. Recovery

### If a live run leaves you worse off

Every artifact is backed up at
`artifacts/builds/aml-alert-investigator/.backup/`. To restore everything:

```
cd "C:\Users\sahidul.i.shaikh\OneDrive - Accenture\Documents\Project\AI_For_AI\artifacts\builds\aml-alert-investigator"
cp .backup/*.md .
cp .backup/src/detector.py src/
cp .backup/tests/test_detector.py tests/
```

Then confirm in the console: **06 Evaluation** -> run the acceptance suite ->
`20 passed, 0 failed`.

The backup was taken with all 11 documents passing and the detector at 20/20.
Refresh it after any run you want to keep:

```
cp *.md .backup/ && cp -r src tests .backup/
```

### Common failures

| Symptom | Cause | Fix |
|---|---|---|
| Top right says **replay only** | Server not answering | Restart it; check the port |
| Every live button dead | Page opened as a file, not over HTTP | Go to `http://localhost:8765` |
| *could not start - is a run already going?* | One run per stage at a time | Wait for it, or restart the server |
| *could not reach the editor* | `code` not on PATH | VS Code -> Command Palette -> *Shell Command: Install 'code' command in PATH* |
| Stage produces nothing for 40s | Normal Claude Code startup | Wait. Fill with the prompt breakdown |
| *the acceptance suite did not run* | pytest missing from the venv | `uv pip install pytest`, then run with `uv run --no-sync` |
| Acceptance suite reports a stale result | Python bytecode cache | Delete `artifacts/builds/aml-alert-investigator/src/__pycache__` |

### Verify the whole repo is sound

```
uv run python checks/aml_check_00_foundation.py
uv run python checks/aml_check_04_build.py
```

All five `aml_check_0*.py` currently pass.

---

## 7. Running the other pillars

All four pillars are now in this console. The previous single-page console is
still served and unchanged as a fallback:

**<http://localhost:8765>**

Same server, so you do not have to start anything else - but it is a different
page with its own tabs, and switching between the two mid-demo is visible. If you
are presenting all four pillars today, the cleanest sequence is:

1. Builds - the six disciplines above.
2. Runs - four disciplines, [runbook](DEMO_RUNBOOK_RUNS.md).
3. Secures - three disciplines, [runbook](DEMO_RUNBOOK_SECURES.md).
4. Improves - four disciplines, [runbook](DEMO_RUNBOOK_IMPROVES.md).

You should not need `/console` at all now. It remains as a fallback if the
factory server will not start.

`DEMO_GUIDE.md` is the presenter guide for those three tabs. Its figures are
hand-maintained and predate this work; re-read the artifacts before quoting any
number from it.
