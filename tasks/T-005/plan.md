# Plan T-005: the console never shows "Not wired yet" for a panel that exists

From intent T-005. Base: main @ 1427d73. Status: accepted by Sahidul Shaikh
(in session, 2026-11-24; asked to proceed without a separate review).

## Cause
`factory.js` called `boot()` as soon as it loaded. `boot()` awaits
`/api/pillars` and then renders the route. Panels register from scripts
loaded after `factory.js`; if one of them had not executed by the time the
fetch resolved, the route rendered with no panel registered and stayed on
"Not wired yet".

## Change
Start `boot()` on `DOMContentLoaded`, which fires only after every
parser-inserted script has run.

## Proof
| Test | main | this branch |
|---|---|---|
| Cold loads, normal speed (builds/delivery, builds/specs) | 0 of 30 | 0 of 20 |
| Cold loads, `delivery.js` delayed 1.5 s (builds/delivery) | **5 of 5 fail** | 0 of 5 |
| Cold loads, `inputs.js` delayed 1.5 s (builds/specs) | **5 of 5 fail** | 0 of 5 |
| All 18 panels, rendered text | - | identical to main, 0 JS errors |

At normal local speed the race rarely shows, which is why it appeared once in
T-001 and not in 30 tries here. Delaying one late script, as a slow network
would, reproduces it every time.
