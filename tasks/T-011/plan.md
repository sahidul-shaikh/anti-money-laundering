# Plan T-011: a light console in the Accenture palette

From intent T-011. Base: main @ b0fa760. Status: accepted by Sahidul Shaikh
(in session, 2026-11-25: light theme only, no toggle).

## Change
| File | Change |
|---|---|
| `scripts/ui/factory.css` | Token block becomes the light palette (page, ink, accent, panels, lines, darker status colours, code background); every hard-coded colour and glow below it points at a token; tints via `color-mix` |
| `scripts/ui/factory.js` | Home ring drawn with token colours |
| `scripts/ui/builds.js` | Stage graph and context bar drawn with token colours |
| `scripts/ui/panels.js`, `chat.js`, `inputs.js`, `runs.js` | Inline colours become tokens |
| `checks/aml_check_04_build.py` | No hex or rgba colour in the UI JavaScript |

## Proof
- Screenshots of the home screen, all 18 panels, the rail and the document
  viewer; 0 JavaScript errors.
- The new check passes, and so do the other checks.
