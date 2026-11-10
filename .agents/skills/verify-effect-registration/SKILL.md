---
name: verify-effect-registration
description: Verify capture effect registration when changing the C constructor, JavaScript module registration, foreign imports, or unsupported-backend return.
---

A ready capture module has its handler registered. Otherwise callers cannot receive a capture result or the supported ENOTSUP failure.

From the repository root, run:

```sh
python3 verification/verify.py effect-registration
```

This checks the finite TLA+ model and executes the covered source with controlled external effects. Read every TLA+ result with `/statechart`, using `verification/models/EffectRegistration.tla`, its adjacent `.cfg`, and `verification/views/EffectRegistration.mjs`. Keep statechart work in a new scratch directory outside the repository.

Coverage: `capture.c`: `window_capture_use` and dispatch into `window_capture_run`. `capture.js`: module-level `io_eff` and `window_capture`. `capture.bend`: native and JS imports.

Last confirmed source commit: `86394a5b7762a7188d32e7c9e8fbb85baa42dbde`.
File hashes and the coverage record are in [source-map.json](../../../verification/source-map.json). Exact assumptions, tool requirements, atomicity, and source-test boundaries are in [verification scope](../../../verification/SCOPE.md).

Bounds: One initialization and one dispatch for supported native, unsupported native, or JavaScript. The Bend runtime owns the registry. Source checks run real native dispatch, force the existing C fallback branch, and run JS fallback with Linux, macOS, and no process object.

To prove the check can fail, run:

```sh
python3 verification/verify.py effect-registration --mutations
```

Mutation witnesses: ReadyHasHandler and UnsupportedReturnsENOTSUP; broken sources omit JavaScript registration or return EIO from the C fallback.
The command mutates actual source in scratch copies, requires the corresponding model invariant to fail, and rechecks the unchanged originals. It never edits production code.

When a check fails, replay the counterexample against the covered source. Fix the model only if its behavior differs from the code. Preserve genuine findings and report them without changing product code unless requested.

When covered files drift, inspect their diff from the recorded commit and review the model and source harness together. If a behavior change is intended, update both before rerunning. After correspondence review, run the same command with `--sync-reviewed` to advance hashes and this skill's commit line only after checks pass. Do not use that flag solely to silence drift. Use `/maintain-formal-verification-skill` for a later audit.
