# Intent T-011: a light console in the Accenture palette

Author: Sahidul Shaikh. Route: a person's idea (demonstration review). Status: accepted.

## Problem
The console is dark: black page, purple glows. Accenture's own material is
white with black text and purple as the accent, and the demonstration should
look like it belongs next to it.

## Proposed outcome
- The console is light: white page, black text, light grey cards and lines,
  Accenture purple as the accent.
- The dark theme goes; there is no toggle.

## Constraints
- Accenture core palette only (#A100FF, #7500C0, #460073 and its tints).
- Text stays readable on white: purple text uses the darker core purple, and
  the status colours are darkened.
- Every panel, the rail, the document viewer and the home screen change
  together; no colour is left hard-coded outside the token block.

## Acceptance condition
All 18 panels, the rail, the document viewer and the home screen render light
with 0 JavaScript errors, and no hex or rgba colour remains in the UI
JavaScript.

## Open questions
None.
