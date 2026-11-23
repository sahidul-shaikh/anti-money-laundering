# 06 — Extension brief: what to build next

## The gap, stated plainly

The Builds pillar proves that AI can **generate** governed artefacts: twelve
stages, each gated, each inheriting reusable skills, with an act-verify-iterate
loop that genuinely fails and genuinely recovers.

What it does not yet do is **deliver**. There is no task, no branch, no commit,
no pull request, no pipeline, no merge gate. The factory describes governed
delivery; it does not perform it.

That gap is sharper than it sounds, because `design/24-ai-native-sdlc-method.md`
already asserts the principle the system does not yet honour:

> Every stage commits an artifact the next stage can read. Together, the
> intent, the spec, the plan, the diff and the review findings are the audit
> trail.

**The repository has zero commits.** We claim the commit history is the audit
trail, in a repository that has never been committed to. Closing that is the
first and most honest thing to build.

---

## What to build

Five capabilities. They compose, and each is demonstrable on its own.

### 1. Version control, properly

Make the repository real before anything else depends on it.

- Initial commit on `main`, with a `.gitignore` that **excludes the source
  data** (`AntiMoneyLaundering/`), the derived `artifacts/corpus.json`,
  `.venv/`, `node_modules/` and render output. Git history is effectively
  permanent; a mistake here is hard to undo.
- Short-lived **feature branches**, not long-lived stage branches.
- `CODEOWNERS` plus branch protection: no direct push to `main`.

> **Caution before you start:** the repository sits on a OneDrive-synced path.
> OneDrive syncing `.git/` can corrupt the index and loose objects. Move it to
> a local path first, or exclude `.git` from sync. We hit OneDrive-related
> filesystem errors in the previous session — the symptom was
> *"the cloud operation cannot be performed on a file with incompatible
> hardlinks"*.

### 2. Task creation

A task is the unit the factory works on and the thing a human approves.

- A task has an identifier, an intent, an acceptance condition, a status and an
  owner. It is the Plan-stage artifact of the SDLC method.
- Created from three routes, exactly as `design/24` §3 describes: a person's
  idea, a finding from the Improves pillar's failure mining, or a breached
  control band.
- Two sources of truth are available: the repository (markdown under
  `intent/`) or an issue tracker. **Pick one and link the other.** For the
  demonstration the repository is almost certainly right; Jira belongs to the
  real programme, where `DEP-013` in `design/22-raid-log.md` already names the
  decision.
- Make the Improves → Builds edge real: a cluster produces a proposal today,
  and a proposal should be able to **open a task**.

### 3. Commit

Each stage ends by committing its artifact.

- The twelve-stage factory already writes to `artifacts/builds/…`. Make it
  commit, with a message naming the stage, the task and the model that produced
  it.
- Every generated artefact gets a provenance trailer: stage, model identifier,
  prompt hash, cost, and the run it came from. This is the `ai_run` spine
  (ADR-008) reaching into git.
- **This closes the "partial" item in `brief/04`**: today `run_id` ties model
  calls together but not security probes or evaluation runs. A commit trailer
  carrying `run_id` is the cheapest way to make the four pillars one record.

### 4. Pull request and review

- The factory opens a PR rather than writing to `main`.
- Review passes driven by a `REVIEW.md` at the repository root, divided into
  the passes that matter here: bugs, security, and **compliance against the
  spec and the plan**.
- **Human approval is required to merge.** Preserve the separation of duties:
  the agent that wrote the code must have no way to approve it. With one human
  this is a self-review gate rather than four-eyes, and the panel should say so
  rather than overclaiming.

### 5. CI/CD and GitHub workflow

- A workflow that runs on every PR: the five `checks/aml_check_0*.py`, the
  acceptance suite, and a panel sweep for JavaScript errors.
- **The adversarial suite as a required check.** This is the strongest idea
  available: a security regression visibly blocks a merge. It gives the Secures
  pillar a second home, in the tool the audience's own engineers use.
- An **agent-eval suite** gated on changes to `CLAUDE.md`, `.claude/skills/**`
  and `.claude/hooks/**` — the configuration that steers the agent deserves the
  regression testing the code gets. `design/18-test-strategy.md` §13 specifies
  it.
- Hooks as deterministic guardrails, per `design/24` §4: a skill makes a
  violation rare, a hook makes it close to impossible. Any control that appears
  as an attestation needs the hook, not just the skill.

---

## How this should show up in the console

The pillars are panels. New capability should be visible, live, and measured —
or it is not finished.

| Panel | Shows |
|---|---|
| Builds / **Tasks** (new) | The task list, where each came from, its status, and the artifact chain it has produced so far |
| Builds / Loops (extend) | After the loop passes, the commit it produced and the PR it opened |
| Builds / **Delivery** (new) | The pipeline for a PR: checks, their results, the merge gate, who approved |
| Secures / Swarm (extend) | The adversarial suite as a *required check* on a PR, with a regression visibly blocking a merge |
| Improves / Failure mining (extend) | A cluster producing a task, closing the loop back to Plan |

The demonstrable arc, end to end, is one sentence worth being able to show:

> A production deviation breaches a band → a task is created → the factory
> plans and implements it → the acceptance suite fails, then passes → a commit
> carries its provenance → a PR opens with review findings → the adversarial
> suite runs as a required check → a human approves → it merges.

That is the AI-native SDLC loop, performed rather than described.

---

## Constraints that must survive

Non-negotiable. Anything you build has to keep these true.

| # | Constraint | Where enforced today |
|---|---|---|
| 1 | The agent recommends; a human decides | `aml/security/tools.py` — unregisterable scopes |
| 2 | Nothing the agent writes reaches a customer | `aml/security/emit.py` |
| 3 | Attacker-controlled text is data, never instruction | `aml/security/envelope.py` |
| 4 | Groundedness is computed, never judged by a model | `aml/run/verdict.py` |
| 5 | Nothing is asserted twice — one ledger, all figures derived | `aml/core/ledger.py` |
| 6 | Declared is not the same as tested | The Secures panel says which is which |
| 7 | No accuracy claim without a re-baseline | `brief/04` |

**The agent may act up to the merge gate and not past it.** That is the same
boundary as "recommends but never files", applied to delivery — and it is the
reason this extension strengthens the governance story rather than diluting it.

---

## Suggested order

1. Git, `.gitignore`, initial commit, branch protection. *Nothing else is safe
   until this exists.*
2. Tasks as artifacts, with the Improves → task edge.
3. Commit with provenance trailers carrying `run_id`.
4. PR creation plus `REVIEW.md` passes.
5. CI with the five checks, then the adversarial suite as a required check.
6. The two new panels, and the extensions to Loops, Swarm and Failure mining.

Build (1) and prove it before designing (2). The value of this work is that it
is real, and the fastest way to lose that is to mock the parts that are
awkward.
