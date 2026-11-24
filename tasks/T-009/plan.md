# Plan T-009: deliver on pass, show delivery as it happens, and a home screen

From intent T-009. Base: main @ afc9fc9. Status: accepted by Sahidul Shaikh
(in session, 2026-11-24; one PR for all three, no separate review).

## Change
| File | Change |
|---|---|
| `aml/build/deliver.py` | `deliver(..., on_step=)` reports "commit" then "pr" |
| `scripts/serve_factory.py` | `DELIVERY` record of the delivery under way or refused; `deliver_tracked()` used by the button and by auto-delivery; a passing code run is delivered to `auto_task()` (the only accepted task with `Delivery: factory`); `/api/run` says where it will deliver |
| `aml/build/delivery_state.py` | Commit / Pull request stations from a delivery under way (running) or refused (failed, with the reason) |
| `scripts/ui/factory.js`, `factory.html`, `factory.css` | Home screen at `#/`; the brand links home |
| `scripts/ui/builds.js` | Loops says a passing run is being delivered, and where |
| `docs/DEMO_RUNBOOK_DELIVERY.md` | Beat 0 (home), Beat 3 automatic, fault table |
| `checks/aml_check_04_build.py` | Delivery steps shown, refusal shown, PR wins once it exists |

## Departures from slide 1
The slide's buttons "Start with the challenges" and "See the AML use case"
lead to pages the console does not have; they became "Start with AI builds
AI" and "Watch the factory deliver". Colours follow the console's theme.

## Proof
- Live run `164937Z` (rules withheld): refused after three attempts; rail
  showed Build loop failed, "refused, nothing to deliver"; nothing delivered.
  Its record is committed as evidence.
- Live run `165307Z`: passed on attempt 2, then with no button pressed the
  rail showed Commit running (41 s), Pull request running (8 s), PR #16 by
  aml-factory-bot, CI running.
- Home screen: secures tile opens `#/secures`; the brand returns home; 18
  panels, 0 JavaScript errors.
- Check 04: 4 new delivery-step checks; five checks pass.
