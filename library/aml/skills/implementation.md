# Skill: implementing a detection rule to a fixed contract

Use when a rule is specified and an interface is fixed.

## Procedure

1. Read the contract before writing anything: parameter names, defaults, output
   keys, and the exact types. The caller cannot be changed to suit you.
2. Resolve every **boundary** explicitly before coding. Inclusive or exclusive at
   each end; what a value exactly on the limit does; whether a window of N days
   spans N or N+1 calendar days.
3. Apply filters in the order the rule states. A direction filter that runs after
   an occurrence count gives a different answer from one that runs before.
4. Return the documented keys in every path, including the not-detected path.
   Partial results still carry their counts.
5. Keep to the standard library unless the contract says otherwise.

## What good looks like

- Every default in the signature matches the specification
- The not-detected return has the same shape as the detected return
- A reader can map each clause of the rule to a line of code

## Common failures

- Off-by-one on the window: reporting an end date past the last qualifying item
- Exclusive upper bound where the specification says inclusive
- Rounding applied at the wrong point, or not at all
- Sorting that is not stable, so references come back in an unpredictable order
