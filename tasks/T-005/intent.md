# Intent T-005: the console never shows "Not wired yet" for a panel that exists

Author: Sahidul Shaikh. Route: a finding (T-001 snapshot comparison). Status: accepted.

## Problem
On a cold first load, a panel that exists can show "Not wired yet. This
discipline has no panel in the console yet." Seen once on builds/specs during
T-001. In a demonstration it looks exactly like a broken panel.

## Proposed outcome
The first route always renders its real panel, however slowly the page's
scripts arrive.

## Affected users and systems
`scripts/ui/factory.js` only.

## Constraints
No change to what any panel shows.

## Acceptance condition
Reproduce the failure on demand, then show it gone, with every panel's text
unchanged.

## Open questions
None.
