# Intent T-009: deliver on pass, show delivery as it happens, and a home screen

Author: Sahidul Shaikh. Route: a person's idea (first demonstrations). Status: accepted.

## Problem
1. After the loop passed, a presenter had to press "deliver" by hand.
2. Commit and Pull request never pulsed: they sat idle and then turned green.
3. The console opened on the first pillar's page. There was no screen with
   all four pillars together, as on slide 1 of the AI-for-AI wireframe deck.

## Proposed outcome
1. A passing implementation run is delivered automatically to the one task
   that accepts factory deliveries.
2. The rail shows Commit, then Pull request, running while the delivery does
   that work, and a refused delivery in red with its reason.
3. A home screen, after slide 1: headline, featured use case, and the four
   pillars around the factory; clicking a pillar opens it.

## Constraints
- The factory still stops at the merge gate: no auto-approve, no auto-merge.
- A refused run is never delivered; a refused delivery is shown, not hidden.
- No button on the home screen leads to a page that does not exist.

## Acceptance condition
A live run delivered with no button pressed, the rail showing each step; a
refused run left undelivered; the home screen navigating to every pillar.

## Open questions
None.
