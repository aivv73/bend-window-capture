---
name: verify-capture-transaction
description: Verify capture acceptance when changing X11 geometry checks, readback phases, supported-backend behavior, or capture result handling.
---

Return Done only after the readback passes the geometry recheck. Otherwise changed client dimensions can be accepted as a valid snapshot.

From the repository root, run:

```sh
python3 verification/verify.py capture-transaction
```

This checks the finite TLA+ model and executes the covered source with controlled external effects. Read every TLA+ result with `/statechart`, using `verification/models/CaptureTransaction.tla`, its adjacent `.cfg`, and `verification/views/CaptureTransaction.mjs`. Keep statechart work in a new scratch directory outside the repository.

Coverage: `capture.c`: `window_capture_run`, from initial `XSync` through geometry checks, `XGetImage`, the `after` query, and final error handling. `capture.bend`: `Window.capture` contract.

Last confirmed source commit: `86394a5b7762a7188d32e7c9e8fbb85baa42dbde`.
File hashes and the coverage record are in [source-map.json](../../../verification/source-map.json). Exact assumptions, tool requirements, atomicity, and source-test boundaries are in [verification scope](../../../verification/SCOPE.md).

Bounds: One attempt with all local error classes, stable or changed readback, final protocol errors, and the unsupported backend. Eligibility folds several queries into an outcome and does not make X11 requests atomic.

To prove the check can fail, run:

```sh
python3 verification/verify.py capture-transaction --mutations
```

Mutation witnesses: OnlyValidatedCaptureSucceeds; the broken source removes the width-change guard and accepts a changed-width snapshot.
The command mutates actual source in scratch copies, requires the corresponding model invariant to fail, and rechecks the unchanged originals. It never edits production code.

When a check fails, replay the counterexample against the covered source. Fix the model only if its behavior differs from the code. Preserve genuine findings and report them without changing product code unless requested.

When covered files drift, inspect their diff from the recorded commit and review the model and source harness together. If a behavior change is intended, update both before rerunning. Commit reviewed changes to covered source files first; sync refuses source bytes that differ from HEAD. After correspondence review, run the same command with `--sync-reviewed` to advance hashes and this skill's commit line only after checks pass. Do not use that flag solely to silence drift. Use `/maintain-formal-verification-skill` for a later audit.
