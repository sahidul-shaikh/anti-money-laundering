# Plan T-007: a runbook for demonstrating delivery, and claims that match the record

From intent T-007. Base: main @ 1427d73. Status: accepted by Sahidul Shaikh
(in session, 2026-11-24; asked to proceed without a separate review).

## Files that change
- `docs/DEMO_RUNBOOK_DELIVERY.md` (new).
- `scripts/ui/builds.js`: "The first attempt cannot, and fails every time"
  becomes "The first attempt has to guess, so it is expected to fail; the
  record below shows what actually happened."

## Where the runbook's figures come from
The four withheld-rules runs since the T-003 fix in `artifacts/live/runs/`:
`053033Z`, `053219Z`, `053435Z`, `070341Z`. Attempt 1 failed in 4 of 4; 3 of
4 passed on attempt 2; 1 was refused after three; 89.8 to 134.1 s; $0.00921 to
$0.01878. CI timings from the PR check runs (pillar checks 13 to 19 s, attack
suite 86 to 93 s).

`docs/DEMO_RUNBOOK_BUILDS.md` line 203 ("attempt 1 failed every time ... seven
of the eight closed on attempt 2") describes its own eight measured runs and is
left as it is.

## Proof
18 panels, 0 JavaScript errors; the Loops panel shows the new sentence.
