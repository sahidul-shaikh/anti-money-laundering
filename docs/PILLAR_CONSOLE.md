# AI Engineering Factory console

A pillar-and-discipline console in Accenture brand. One page per pillar, one
panel per discipline, every panel backed by something real in this repo.

To operate it in front of an audience, see **[DEMO_RUNBOOK_BUILDS.md](DEMO_RUNBOOK_BUILDS.md)** -
the run of show, where each stage is launched from, the verified tamper demos,
and recovery.

## Run it

```
uv run python scripts/serve_factory.py
```

`/console` and is unchanged.

Routes are deep-linkable, so you can jump straight to a discipline:

```
#/builds              the pillar landing page
#/builds/skills       one discipline
```

## AI builds AI - the six disciplines

| # | Discipline | What the presenter does | What it proves |
|---|---|---|---|
| 01 | Specs | **show the requirements**, then **re-read the intent** (live, ~13s, ~$0.02), then **approve** | A person wrote the requirement. Stage 0 extracts a brief from it; the approval is the control. |
| 02 | Context | pick a stage, press **assemble** | The exact characters a stage is sent, broken down by part. Costs nothing, calls no model. |
| 03 | Skills | click through the thirteen files | Procedural knowledge is a file on disk, attached to the stages that declare it. |
| 04 | Loops | tick **withhold the rule detail**, press **run** (2-7 min, ~$0.50) | Goal, act, verify, iterate against an oracle the model never sees. |
| 05 | Graphs | click a node, especially **Model risk** | Twelve stages, fifteen dependencies, four gates, three joins - enforced by the orchestrator. |
| 06 | Evaluation | **re-evaluate** a document after renaming a heading; **run the acceptance suite** after editing the detector | Nothing marks its own homework. |

The honest caveat for 04: with the rule detail withheld the loop does **not**
reliably converge. Measured outcomes so far are 2 attempts then pass, and 3
attempts then blocked. Both are true demonstrations - the second one shows the
gate refusing - but do not promise the room that attempt 2 will pass.

## Files

```
library/pillars.json      the pillar and discipline definitions - the copy lives here
scripts/ui/factory.html   the shell
scripts/ui/factory.css    Accenture tokens, then generic components
scripts/ui/factory.js     nav, strip, hero, ring, grid, hash router, panel registry
scripts/ui/builds.js      the six panels for AI builds AI
```

## Adding the next pillar

1. Fill in that pillar's `disciplines` in `library/pillars.json` - each needs
   `id`, `n`, `title`, `claim`, `proof`, `mode`, `evidence`, `watch_for` - and
   set `"status": "live"` so the nav enables it.
2. Add `scripts/ui/<pillar>.js` with one `F.register("<pillar>", "<discipline>", fn)`
   per discipline. The function is handed a host element and may be async.
3. Add the script tag to `scripts/ui/factory.html`.

No shell changes, no CSS changes. The shell reads the definition and the panels
supply the evidence.

### Server endpoints the panels use

| Endpoint | Returns |
|---|---|
| `GET /api/pillars` | the pillar definitions |
| `GET /api/state` | the twelve stages, the approved brief, the PRD path |
| `GET /api/prd` | the requirements document |
| `GET /api/prompt/<stage>?withhold=0\|1` | the assembled prompt, skills inlined |
| `GET /api/skills` | the skill files, with which stages attach them |
| `GET /api/oracle` | the acceptance suite, named test by test |
| `GET /api/lastrun/<stage>` | the readable trace of the last live run |
| `POST /api/run/<stage>` | start a live run; stream it from `/api/stream/<stage>` |
| `POST /api/evaluate/<stage>` | re-check a document, or run the suite for a code stage |
| `POST /api/extract`, `POST /api/brief` | stage 0 extraction and approval |
| `POST /api/open/<stage>` | bring the artifact up in VS Code |

Every live run now also writes `artifacts/live/<stage>.run.json` - the attempts,
the test results and the verdict - which is what the Loops panel replays.
