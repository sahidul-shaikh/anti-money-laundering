# 07 — Conventions and pitfalls

Hard-won operational knowledge. Reading this will save you several hours.

---

## Code style

From the operator's standing instructions, and they are enforced in review:

- **Be simple. Work incrementally.** Small steps, validated before moving on.
- Do not overengineer. Do not program defensively. Exception handlers only
  where they earn their place.
- **Identify the root cause before fixing.** Reproduce it, prove it, then fix
  it. Do not apply workarounds.
- `uv` is the package manager. Always `uv run …`, never bare `python`. Always
  `uv add …`, never `pip install`.
- Short modules, short functions, clear names. Docstrings yes; running
  commentary no.
- **No emojis anywhere** — not in code, not in print statements, not in logs.

---

## Platform pitfalls

### Windows and the shell

- PowerShell is the primary shell; a Bash tool is also available, and each
  takes its own syntax. In PowerShell 5.1 there is no `&&`, no ternary, no
  `??`.
- **Never round-trip a source file through PowerShell `Get-Content` /
  `Set-Content`.** It re-encodes: UTF-8 is read as ANSI and written back
  double-encoded, so `→` becomes `â†'`. This corrupted a generator in the
  previous session. Use Python or the editing tools.
- Bash heredocs mangle backslashes. For anything with escapes, write a script
  file instead of inlining it.
- `PYTHONIOENCODING=utf-8` is needed for arrow characters in console output.
- `NODE_PATH="$PWD/node_modules"` is needed for the deck generators.

### OneDrive

The parent repository sits on a OneDrive-synced path, and it causes real
failures:

- `uv` hardlinking fails with *"the cloud operation cannot be performed on a
  file with incompatible hardlinks."* Workaround: `$env:UV_LINK_MODE = "copy"`.
- A file open in another application (PowerPoint, Excel) cannot be read at all,
  not even with shared-read access.
- **Do not let OneDrive sync `.git/`.** Move the repository to a local path
  before putting it under version control.

### uv

- `uv sync` once per folder. `uv run --no-sync` afterwards for speed.
- If `VIRTUAL_ENV` points at a different folder's environment, uv warns and
  ignores it. Clear it when working in this folder.
- `uv run --no-project --with <pkg> python script.py` for one-off tools such as
  Playwright, which is deliberately not a project dependency.

---

## Working on the console

- The panel host element is **`#dpanel`**, not `#view`.
- Panel routes use full names: `threat-modelling`, `runtime-defense`,
  `failure-mining`, `value-engineering`. A short form renders an **empty panel
  with no error**, which looks exactly like a broken panel. This cost time in
  the previous session.
- Restart the server for changes to `serve_factory.py` or anything in `aml/`.
  Browser reload is enough for `scripts/ui/`.
- After any UI change, sweep all 17 panels for JavaScript errors before
  declaring it done.

---

## Working on the build loop

- Each attempt is a headless Claude Code call, 60–80 s on haiku, which is the
  default in the picker.
- **Do not "optimise" the loop by passing `--tools "" --setting-sources ""`.**
  It was tried, measured faster per attempt, and reverted — it changed what the
  stage inherits and the operator asked for it back.
- The loop's two load-bearing details are in the feedback, not the builder:
  it carries **the code the previous attempt wrote** and **the pass count**.
  Remove either and attempt 2 starts trading one failure for another.
- The handicap that makes attempt 1 fail is a single output convention held in
  the acceptance suite and absent from the brief. Keep it in exactly one test
  with a scoping assertion message, or the model reads it as "reformat
  everything" and breaks twelve other checks.

---

## Measurement discipline

This is the part that makes the demonstration credible, and the easiest to
erode.

- **Every figure shown must be measured on this machine and reconcile to the
  ledger.** No estimates presented as measurements.
- **Declared is not tested.** Two probes (P-09, P-10) are declared and
  deliberately not executed, and the panel says so. Do not quietly promote
  them.
- **No accuracy claim** — there has been no re-baseline since the rule
  catalogue changed.
- When something cannot be done, say so and say why. The Tokenomics panel is
  the model for this: the saving is real, it is measured, and **we cannot have
  it**, because both serving models refuse prompt caching and the one that
  caches is the one the quality gate rejected. That is a better panel than a
  fabricated saving.

---

## Security and data handling

- `AntiMoneyLaundering/Alert_Final_table.xlsx` holds **real named individuals**
  with dates of birth, occupations and incomes. Do not send it to any external
  service, do not commit it to a remote, do not put party names in logs.
- The Actimize Solution Guide is marked PRODUCT CONFIDENTIAL. It is not in this
  folder; the rules extracted from it are, in `library/aml/rules.json`, with
  page citations.
- **Do not read `~/.aws/credentials` or `~/.aws/config`.** They are configured
  and working. If you need to confirm identity, call the AWS API.
- The pen-testing work targets our own demonstration system and is authorised
  and defensive. One payload is a tipping-off bait that attempts to induce a
  disclosure which would be a criminal offence in production — it exists to
  prove the control holds, and the code comments say so. Keep that framing.

---

## Tone of the artefacts

The runbooks, panels and documents share a voice worth matching: plain, exact,
and willing to say what did not work. Figures carry their provenance. Caveats
appear next to the claim they qualify, not in a footnote. Where the system is
weaker than it looks, the document says so before an audience asks.

That is not stylistic preference. It is the reason a sceptical room believes
the parts that are strong.
