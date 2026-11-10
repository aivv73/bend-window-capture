---
name: verify-window-lifecycle
description: Verify the example window lifecycle when changing its IO continuations, capture ownership signature, close order, or result reporting.
---

Report success and failure only after closing the returned Window. Skipping close leaks the window.

From the repository root, run:

```sh
python3 verification/verify.py window-lifecycle
```

This checks the finite TLA+ model and executes the covered source with controlled external effects. Read every TLA+ result with `/statechart`, using `verification/models/WindowLifecycle.tla`, its adjacent `.cfg`, and `verification/views/WindowLifecycle.mjs`. Keep statechart work in a new scratch directory outside the repository.

Coverage: `examples/capture.bend`: `main`, `opened`, `capture_frame`, `close_and_report`, `captured`, and `report`. `capture.bend`: `Window.capture` ownership signature.

Last confirmed source commit: `86394a5b7762a7188d32e7c9e8fbb85baa42dbde`.
File hashes and the coverage record are in [source-map.json](../../../verification/source-map.json). Exact assumptions, tool requirements, atomicity, and source-test boundaries are in [verification scope](../../../verification/SCOPE.md).

Bounds: One open attempt, one frame, capture Done or Fail, one close. Open failure owns no window. Bend continuations are the transition boundaries.

To prove the check can fail, run:

```sh
python3 verification/verify.py window-lifecycle --mutations
```

Mutation witnesses: ReportAfterClose; the broken source omits `Window.close` and the compiled example reports while the window remains open.
The command mutates actual source in scratch copies, requires the corresponding model invariant to fail, and rechecks the unchanged originals. It never edits production code.

When a check fails, replay the counterexample against the covered source. Fix the model only if its behavior differs from the code. Preserve genuine findings and report them without changing product code unless requested.

When covered files drift, inspect their diff from the recorded commit and review the model and source harness together. If a behavior change is intended, update both before rerunning. Commit reviewed changes to covered source files first; sync refuses source bytes that differ from HEAD. After correspondence review, run the same command with `--sync-reviewed` to advance hashes and this skill's commit line only after checks pass. Do not use that flag solely to silence drift. Use `/maintain-formal-verification-skill` for a later audit.
