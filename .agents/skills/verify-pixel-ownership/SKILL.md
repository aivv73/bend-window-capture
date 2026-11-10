---
name: verify-pixel-ownership
description: Verify image cleanup and independent pixel storage when changing capture allocation, zero padding, the copy loop, destruction, array packing, or post-close reads.
---

Release acquired XImages and return an independent, complete pixel array with zero padding. Otherwise capture leaks memory or exposes stale data.

From the repository root, run:

```sh
python3 verification/verify.py pixel-ownership
```

This checks the finite TLA+ model and executes the covered source with controlled external effects. Read every TLA+ result with `/statechart`, using `verification/models/PixelOwnership.tla`, its adjacent `.cfg`, and `verification/views/PixelOwnership.mjs`. Keep statechart work in a new scratch directory outside the repository.

Coverage: `capture.c`: image acquisition, failure cleanup, depth loop, `heap_alloc`, `memset`, pixel copy, `XDestroyImage`, and `Capture` construction. `capture.bend`: array contract. `examples/capture.bend`: reads after close.

Last confirmed source commit: `86394a5b7762a7188d32e7c9e8fbb85baa42dbde`.
File hashes and the coverage record are in [source-map.json](../../../verification/source-map.json). Exact assumptions, tool requirements, atomicity, and source-test boundaries are in [verification scope](../../../verification/SCOPE.md).

Bounds: Logical pixel counts 1, 3, 4, and 5 and capacities through 8. Acquisition or later failure and one pixel per copy action. Runtime allocation succeeds. This is not a proof of C RGB arithmetic for every input.

To prove the check can fail, run:

```sh
python3 verification/verify.py pixel-ownership --mutations
```

Mutation witnesses: PaddingZeroAndOwned and AllImagesReleased; broken sources omit zeroing or omit failure-path image destruction. Source-only mutations corrupt row placement and the red channel to check the executable pixel oracle.
The command mutates actual source in scratch copies, requires the corresponding model invariant to fail, and rechecks the unchanged originals. It never edits production code.

When a check fails, replay the counterexample against the covered source. Fix the model only if its behavior differs from the code. Preserve genuine findings and report them without changing product code unless requested.

When covered files drift, inspect their diff from the recorded commit and review the model and source harness together. If a behavior change is intended, update both before rerunning. After correspondence review, run the same command with `--sync-reviewed` to advance hashes and this skill's commit line only after checks pass. Do not use that flag solely to silence drift. Use `/maintain-formal-verification-skill` for a later audit.
