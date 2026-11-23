# Plan T-001: remove superseded console panel code

From intent T-001. Base: main @ 88770ee. Status: accepted by Sahidul Shaikh (in session, 2026-11-24).

## Evidence
`Factory.register` stores panels in a plain object
(`scripts/ui/factory.js:20`), so a second registration of the same route
replaces the first. Scripts load in the order listed in
`scripts/ui/factory.html:39-48`, with `panels.js` last.

| Dead registration | Replaced by |
|---|---|
| `builds.js:39` builds/specs | `inputs.js:24` |
| `builds.js:594` builds/evaluation | `panels.js:22` |
| `chat.js:58` runs/routing | `panels.js:126` |
| `runs.js:188` runs/reliability | `panels.js:211` |
| `secure_demo.js:15` secures/swarm | `panels.js:283` |
| `improves.js:44` improves/tokenomics | `panels.js:415` |
| `improve_demo.js:24` improves/harness | `panels.js:480` |

Plus `fleetTable` (`runs.js:31`), defined and never referenced.

## Files that change
`scripts/ui/builds.js`, `runs.js`, `chat.js`, `secure_demo.js`,
`improves.js`, `improve_demo.js`. Nothing else.

## Order of work
1. Snapshot the rendered text of all 17 panels and the JS error count.
2. Delete the seven dead registrations and `fleetTable`.
3. Delete any helper that only those blocks used, each confirmed by search
   before removal. Keep anything another file uses (for example the sample
   loader `panels.js` borrows from `chat.js`).
4. Snapshot again and compare.
5. Run the five checks.

## Risks
- A helper inside a dead block is used elsewhere. Mitigation: search each
  name across `scripts/ui/` before deleting; the snapshot diff catches misses.
- A file becomes empty or near-empty. Then delete the file and its `<script>`
  tag rather than keep a shell. Decided per file and stated in the PR.

## Proof
- Rendered text of all 17 panels identical before and after.
- 0 JavaScript errors across the sweep.
- Five checks pass locally; both CI checks green on the PR.
