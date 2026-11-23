# Initial prompt for the new session

Open a Claude Code session with this folder as the working directory, then
paste the prompt below.

---

## The prompt

```
This folder is a complete, working AI Engineering Factory demonstration built
around one real use case: an AML alert investigator. It is the only reference
you should use — everything you need is here, and nothing outside it applies.

Start by reading START_HERE.md, then brief/01 through brief/07 in order. Do
not read the design/ folder yet; brief/04 and brief/06 will tell you which of
those documents matter and when.

Before changing anything, prove the system works for you:

  uv sync
  uv run python scripts/serve_factory.py      # http://localhost:8765
  for f in checks/aml_check_0*.py; do uv run python "$f"; done

Open the console and look at all four pillars and all 17 panels. They are
enabled and working — 17 panels, 0 JavaScript errors, five checks passing,
verified before handover. If that is not what you find, stop and tell me before
going further.

Then I want to extend it, with fresh thinking rather than incremental tidying.
The focus is the Builds pillar, which today proves that AI can generate
governed artefacts but does not yet deliver them. There is no task, no branch,
no commit, no pull request, no pipeline, no merge gate. brief/06 is the full
brief; the short version is:

  1. Put the repository under version control properly, with a .gitignore that
     excludes the real alert data. Read the OneDrive caution in brief/06 first.
  2. Task creation as the Plan-stage artifact, including the edge where the
     Improves pillar's failure mining opens a task.
  3. Commits carrying provenance — stage, model, prompt hash, cost, run_id.
  4. Pull requests with review passes and a human merge gate.
  5. CI/CD in GitHub Actions, with the adversarial suite as a required check
     that can visibly block a merge.

The arc I want to be able to demonstrate end to end is:

  a production deviation breaches a band -> a task is created -> the factory
  plans and implements it -> the acceptance suite fails, then passes -> a
  commit carries its provenance -> a PR opens with review findings -> the
  adversarial suite runs as a required check -> a human approves -> it merges.

Constraints that must survive anything you build are listed in brief/06 and in
CLAUDE.md. The important one: the agent may act up to the merge gate and not
past it, which is the same boundary as "recommends but never files" applied to
delivery.

Work incrementally and prove each step before moving to the next. Do not mock
anything — the value of this system is that every number in it was measured.

Start by reading, then tell me what you have understood, where you think the
design in brief/06 is wrong or incomplete, and what you would do first. Do not
write any code until we have agreed the approach.
```

---

## Why the prompt is shaped this way

| Element | Purpose |
|---|---|
| "the only reference you should use" | Stops the session hunting for the parent repository or inventing context |
| Reading order, and *not* `design/` yet | 26 design documents would consume the context window before any work starts |
| "prove the system works for you" first | Establishes a known-good baseline. If something is broken on arrival, you want to know before changes are layered on top |
| The verified figures (17 panels, 0 errors, 5 checks) | Gives a concrete pass/fail, not a vague "check it works" |
| "fresh thinking rather than incremental tidying" | You asked for new work, not polish |
| The end-to-end arc | A single demonstrable sentence is a better target than a feature list |
| "Do not mock anything" | The one discipline that makes this demonstration credible |
| "Do not write any code until we have agreed the approach" | Keeps you in control of the first move, and surfaces disagreement with the brief while it is cheap |

## If you want a shorter kickoff

```
Read START_HERE.md and brief/01 through brief/07. Then start the console
(uv sync; uv run python scripts/serve_factory.py) and confirm all 17 panels
work. Then tell me what you would do first to deliver brief/06 — task
creation, commits, PRs and CI/CD in the Builds pillar. No code yet.
```
