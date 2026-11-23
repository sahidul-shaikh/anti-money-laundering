# Intent T-001: remove superseded console panel code

Author: Sahidul Shaikh. Route: a person's idea (handoff brief/03). Status: accepted.

## Problem
Seven console panels are registered twice. The later registration wins, so
the earlier versions never run, but they still sit in the code. Anyone reading
`builds.js` or `runs.js` to change a panel may edit the copy that is never
shown. One helper (`fleetTable`) is defined and never called.

## Proposed outcome
Only the code that actually renders a panel remains. What the console shows
does not change at all.

## Affected users and systems
Console maintainers. Files under `scripts/ui/` only. No server, model or data
change.

## Constraints
- All 17 panels render exactly as before, with no JavaScript errors.
- The five pillar checks still pass.
- No behaviour change, so no new tests are needed; the proof is that nothing
  visible changed.

## Acceptance condition
Rendered text of every panel is identical before and after; 0 JavaScript
errors; CI green.

## Open questions
None.
