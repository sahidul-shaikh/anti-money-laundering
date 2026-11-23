# Skill: writing a value contract

Use when a build is being funded and nobody has yet written down what success is.

## Procedure

1. State the **baseline** as a measured number with its unit of work, not an
   adjective. "GBP 17.00 per alert, one analyst review, every time" - not "costly".
2. State the **target** as a number against the same unit, so the two can be
   subtracted.
3. State the **quality floor** separately from the target. The floor is the level
   below which the thing must not be deployed at any price. Name the metric that
   carries it and say why that metric and not another.
4. State the **telemetry** that will prove realisation, naming the layer each
   measure sits at. A target with no telemetry is an aspiration.
5. State who signs it.

## What good looks like

- Every number has a unit and a source
- The floor is expressed so that a saving cannot be traded against it
- A reader can tell, from the contract alone, what evidence would settle an
  argument about whether the build worked

## Common failures

- Targets expressed as percentages with no denominator
- A single blended "accuracy" that hides the asymmetry between the two error types
- Telemetry listed as "dashboards"
