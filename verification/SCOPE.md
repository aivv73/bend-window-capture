# Verification scope

These models check the protocols in the existing code. They do not change product behavior.
Run `python3 verification/verify.py all` from the repository root.
Add `--mutations` to check the broken variants as well.
Run `python3 -B -m unittest discover -s tests -v` for download, shutdown, evidence-retention, and sync-baseline regressions. CI runs those checks alongside the live X11 integration example.

The runner requires Python 3, Node, Clang, X11 development headers, Bend 2.0.40, and Java 11 or newer.
It downloads TLC 1.7.4 into the user cache and verifies its pinned SHA-256.
Set `JAVA` to a Java binary and `TLA2TOOLS` to the pinned jar to supply those tools yourself.
The recorded run uses Temurin 21.0.8+9. Runtime binaries and checker work files stay outside the repository.

## Covered protocols

| Area | Rule and user harm | Model bound | Source correspondence |
| --- | --- | --- | --- |
| Window lifecycle | Report only after closing the returned window. Otherwise success or failure can leak a window. | One open attempt, one frame, both capture outcomes, one close. | `examples/capture.bend`: `main`, `opened`, `capture_frame`, `close_and_report`, `captured`, and `report`; `capture.bend`: ownership signature. |
| Capture transaction | A successful snapshot passes the post-readback geometry check. Otherwise changed dimensions can be presented as a valid capture. | One attempt, all local error classes, supported or unsupported backend, stable or changed readback, final protocol error classes. | `capture.c`: `window_capture_run`, especially initial `XSync`, guard sequence, the `after` query, and final error handling. |
| X11 error trap | Restore the previous handler before clearing the context, and preserve the first owned error. Otherwise later X11 activity can use invalid context or report the wrong failure. | One serialized capture and up to two callbacks, each owned error 1 or 2, or unrelated error. | `capture.c`: `WindowCaptureTrap`, `window_capture_error`, installation, final `XSync`, restoration, and context clearing. |
| Pixel ownership | Release every acquired image and return a complete independent array with zero padding. Otherwise capture can leak native memory or expose stale pixel data. | Logical pixel counts 1, 3, 4, and 5, capacities through 8, acquisition failure, failure after acquisition, one copy loop. | `capture.c`: image acquisition, error cleanup, depth calculation, allocation, `memset`, copy loop, destruction, and `Capture` construction. |
| Effect registration | A ready module has a registered capture handler. Otherwise calling the library fails before it can return a supported result or `ENOTSUP`. | One module initialization and one dispatch, supported native, unsupported native, or JavaScript. | `capture.c`: `window_capture_use`; `capture.js`: module-level `io_eff` and `window_capture`; `capture.bend`: foreign imports. |
| Check runner | Ordinary exit leaves no temporary build directory. Otherwise failed verification accumulates build files. | One proof, allocation, trap registration, compilation, execution, comparison, and ordinary exit. | `scripts/check.sh`: `set -euo pipefail`, `mktemp`, EXIT trap, compilation, execution, and comparison. CI only supplies prerequisites. |

Each model uses named actions and terminal stuttering actions. TLC explores the complete finite state space without a state constraint or symmetry reduction. These are safety checks. They do not prove termination or fairness of external operations.

## Abstraction and atomicity

Bend continuations define the window lifecycle's observation points. The C bridge runs synchronously on the IO thread. The models omit internal calculations that do not change a covered property.
Capture eligibility summarizes the geometry, bounds, visual, and capacity guards as one observable outcome. It does **not** assert that the underlying X11 requests are atomic.
The later geometry query samples stable or changed dimensions independently. External window changes and callbacks are represented by nondeterministic outcomes, rather than a claim that the server stops changing.
The trap model separates context publication, handler installation, callbacks, draining, restoration, and context clearing. Only one capture may run at a time.
The buffer model separates allocation, initialization, copying, destruction, and publication. Its pixel loop advances one logical pixel at a time.

## What the source checks establish

`source_checks.py` compiles the actual Bend example to C. It replaces the external window-open, frame, close, and X11 boundaries with controlled implementations.
The generated capture bridge, error callback, Bend continuations, heap allocator, array packing, and IO dispatcher remain executable production code.
An observing wrapper checks returned handle identity, error classification, handler restoration, cleanup, array capacity, padding, pixel order, and pixels after close.
The tests cover every local guard branch, representative protocol errors, two owned errors, three unrelated error sources, and small padded arrays.
They also check that every fake request is drained before the old handler is restored. Rectangular padded images and the full RGB quadrant image check the pixel oracle. They do not prove C behavior for every input. They also do not test real X11 rendering or server behavior.

JavaScript checks execute the unmodified module in a VM with the compiler's symbol and IO boundary conventions. They cover Linux, macOS, and no `process` object. A second native build forces only the capture function into its existing unsupported-backend preprocessor branch and checks `ENOTSUP` plus handle identity. This executes that branch on Linux; it does not validate another operating system's ABI.
Shell checks execute the actual check script with a controlled compiler and program. They cover proof, compile, execution, and comparison failures plus success.

`--mutations` makes isolated copies of the real source and removes a close, resize guard, handler restoration, first-error latch, array zeroing, image cleanup, registration, or EXIT trap.
Each source mutation must fail its behavioral witness. Additional source-only mutations corrupt row order or the red channel, or move the final synchronization before readback; these validate the source oracle without claiming an arithmetic or server proof. A corresponding broken model must violate the named invariant.
Compilation errors and unrelated failures do not count as catching a mutation. Fresh copies of the original code and model must pass afterward.

## Limits and maintenance

The ownership token can outlive the X11 drawable. Successful readback checks matching dimensions and viewability at two observations, not continuous stability or unobscured pixels.
The models assume serialized effects, valid Bend-owned handles, successful runtime allocation, normal Xlib callback lifetime, and ordinary process exit.
They exclude nested captures, arbitrary foreign Xlib threads, allocation failure, process termination between `mktemp` and trap installation, SIGKILL, C undefined behavior, and all-input RGB arithmetic proofs.
Pixel arithmetic is exercised by source tests. It is not a TLA+ proof of the C function.
A missing handler creates a dead end in the registration model. Bend's real handling of a missing effect is outside that model; a model deadlock is not a claim that the application hangs. The existing Bend proof covers structural ownership and remains a separate check.

`source-map.json` records covered file hashes and the source commit. The runner refuses a normal pass when those files drift.
After reviewing the code, model, and harness together, commit changes to covered source files before using `--sync-reviewed`. The command requires those files to match HEAD, pins that commit, and refuses metadata updates if source changes during verification. Passing checks then advance the selected coverage records and skill commit lines.
Never refresh a fingerprint merely to silence drift. Intended behavior changes require corresponding model changes. An unexpected counterexample remains a finding.
Read TLA+ results with `/statechart`. Use `/maintain-formal-verification-skill` when later changes need a correspondence audit.
