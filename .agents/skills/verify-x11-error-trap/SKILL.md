---
name: verify-x11-error-trap
description: Verify X11 error-handler lifetime and first-error behavior when changing the capture trap, callback filtering, synchronization, or restoration.
---

Restore the old handler before clearing context and preserve the first owned error. Otherwise subsequent X11 activity can access invalid context or return the wrong error.

From the repository root, run:

```sh
python3 verification/verify.py x11-error-trap
```

This checks the finite TLA+ model and executes the covered source with controlled external effects. Read every TLA+ result with `/statechart`, using `verification/models/X11ErrorTrap.tla`, its adjacent `.cfg`, and `verification/views/X11ErrorTrap.mjs`. Keep statechart work in a new scratch directory outside the repository.

Coverage: `capture.c`: `WindowCaptureTrap`, `window_capture_error`, and trap setup and teardown in `window_capture_run`. `LAWS.bend`: IO-thread restriction.

Last confirmed source commit: `86394a5b7762a7188d32e7c9e8fbb85baa42dbde`.
File hashes and the coverage record are in [source-map.json](../../../verification/source-map.json). Exact assumptions, tool requirements, atomicity, and source-test boundaries are in [verification scope](../../../verification/SCOPE.md).

Bounds: One serialized capture and at most two callbacks, each owned error 1 or 2, or unrelated. No nesting or arbitrary concurrent Xlib callers. Source checks also exercise display and request-serial filtering and require all fake requests to be drained before restoration. A source-only mutation moves the final synchronization before readback.

To prove the check can fail, run:

```sh
python3 verification/verify.py x11-error-trap --mutations
```

Mutation witnesses: RestoredHandler and FirstErrorWins; broken sources remove handler restoration or allow a second error to overwrite the first.
The command mutates actual source in scratch copies, requires the corresponding model invariant to fail, and rechecks the unchanged originals. It never edits production code.

When a check fails, replay the counterexample against the covered source. Fix the model only if its behavior differs from the code. Preserve genuine findings and report them without changing product code unless requested.

When covered files drift, inspect their diff from the recorded commit and review the model and source harness together. If a behavior change is intended, update both before rerunning. After correspondence review, run the same command with `--sync-reviewed` to advance hashes and this skill's commit line only after checks pass. Do not use that flag solely to silence drift. Use `/maintain-formal-verification-skill` for a later audit.
