---
name: verify-bend-window-capture
description: Drive the real bend-window-capture library and documented CLI example on isolated Linux X11 displays when verifying pixels, geometry, failure ownership, or queued events.
---

The primary surface is the Bend library: open a window, draw, call `C.Window.capture`, and consume the returned window and result. The documented example and check script are CLI entry points. This skill exercises the unmodified native bridge against a real X11 server. The six other project skills cover bounded formal models and controlled-boundary tests.

Read the [feature index](features/README.md) and the matching feature file before a drive. JavaScript and non-Linux backend behavior remain outside this initial live map.

## Launch

Run from the repository root on Linux. Required tools are Bend **2.0.40**, Clang, Python 3, X11 development headers and libraries, `xauth`, `xkbcomp`, and Xvfb. Read `bend guide` before changing the Bend consumers. `LAWS.bend` records the ownership and native obligations.

The helper uses `XVFB_BIN` when set, then `Xvfb` on PATH, then the user-cache binary at `~/.cache/bend-window-capture-live/usr/bin/Xvfb`. On an Arch-family x86_64 host, provision the cache without sudo using:

```sh
./.agents/skills/verify-bend-window-capture/scripts/control.py setup-xvfb
```

This downloads the package selected by the configured pacman repositories, verifies its SHA-256 against their local metadata, and extracts only Xvfb into the user cache. It does not install a system package. Other hosts can install Xvfb with their package manager or set `XVFB_BIN` to an executable. Missing shared libraries or XKB data remain unmet prerequisites; do not substitute a mock server.

Prepare a fresh run:

```sh
bwc_control="$PWD/.agents/skills/verify-bend-window-capture/scripts/control.py"
bwc_run_dir="$PWD/build/live-verification/$(date +%Y%m%d-%H%M%S)-$$"
"$bwc_control" launch --run-dir "$bwc_run_dir"
```

Require `READY` followed by the chosen evidence directory. Launch checks the existing Bend proof, compiles the actual example, three public-API consumers, and the X11 driver. It records source and binary fingerprints in `build.json`. No application instance stays running after launch. There are no migrations, seed accounts, or service ports.

This is a short-lived CLI/library workflow. Each drive gets a fresh raw PTY and a fresh authenticated 800×600×24 Xvfb server. Drives run serially within one prepared run. Concurrent runs need distinct evidence directories; their builds, displays, authentication, and PTYs are separate. The helper never attaches to the user's `DISPLAY`.

Teardown is the Cleanup command below. Use it after failed launch or drive attempts too. An existing evidence directory is never reused for launch.

## Doctor

Run this read-only build check before the first drive and whenever anything looks wrong:

```sh
"$bwc_control" doctor --run-dir "$bwc_run_dir"
```

Require `healthy: true`, Bend 2.0.40, matching source and binary hashes, and zero active owned instances. Each drive repeats this check and then health-checks its fresh display: the server PID must match its X11 lock, its screen must be 800×600×24 TrueColor, and its window list must be empty.

A changed source file or compiled driver invalidates the prepared build. Preserve the evidence, run Cleanup, and launch into a new directory. A failed drive records a display doctor result when the server is still available, then destroys that display. The next drive starts from a new, health-checked instance. Do not reuse a failed desktop state.

## Drive

Use one mapped feature per drive. The native example has two working entry points:

```sh
"$bwc_control" drive --run-dir "$bwc_run_dir" --feature example --entry binary
"$bwc_control" drive --run-dir "$bwc_run_dir" --feature example --entry check
```

Exercise the remaining library features with:

```sh
"$bwc_control" drive --run-dir "$bwc_run_dir" --feature pixels
"$bwc_control" drive --run-dir "$bwc_run_dir" --feature recoverable-failure
"$bwc_control" drive --run-dir "$bwc_run_dir" --feature events
```

Require exit code 0 and `PASS` with a per-drive evidence directory. The example command must print `64x64 16711680 65280 255 16777215`; the check-script entry prints its existing PASS line.

The source-only command `bend examples/capture.bend` is not a usable X11 entry point with this compiler: it reports `Window.open: no display` and exits 95 (ENOTSUP), including on a healthy private display. The README now builds a native binary first. To reproduce this known limitation, use `drive --run-dir "$bwc_run_dir" --feature example --entry bend`; the helper must report FAIL and preserve the nonzero exit, not relabel it a successful capture. Cleanup that run afterward.

The consumer programs use only public `Window`, `File`, and capture-library operations. They print `READY` after drawing and wait for one `g` byte on their terminal. The driver finds their window by the exact title `BWC live probe` on the owned display. It changes server-side geometry or visibility, or queues the normal `WM_DELETE_WINDOW` message, before releasing capture. The pixel consumer redraws after resizing and pauses at `CAPTURED` for an independent screenshot; a second `g` permits close and array reads. Failure recovery uses the returned window to change its title to `BWC recovered`, waits for a second `g`, and then closes it.

These are real captures and real window operations. There is no dry-run or mock mode. Only optional dependency provisioning uses the network. No browser, external account, or shared desktop is involved.

## Evidence

Evidence stays under the exact `$bwc_run_dir` chosen at launch. Each drive creates a unique feature-and-entry subdirectory containing:

- `command.json`, `stdout.txt`, `stderr.txt`, and `result.json` for the action, visible output, and exit code.
- `actions.json` for the sequence of window actions and observed results.
- `display.json`, `display-doctor.json`, `xvfb.log`, and `display-cleanup.json` for instance identity, prerequisites, and teardown.
- Independent X11 geometry, screenshot, and post-close window-list reports. Consumers also retain `window-before.png`; the pixel drive adds pre-redraw `window-resized.png` and post-capture `window-captured.png`.
- `failure-doctor.json` when a failed drive leaves the server available for a read-only check.

Prove the action and its resulting state. A final screen alone is insufficient. The pixel drive compares the external screenshot with the returned array and checks the padding and dimensions after `Window.close`. Failure recovery requires the independently observed renamed window. Every successful drive requires an empty X11 window list after the consumer exits. A model pass is not a substitute for these live observations.

The verified environment is a headless Xvfb server without a window manager. The harness creates its screen, a private authentication file, and a fresh PTY. A user's graphical session supplies its own display, credentials, positioning, and window manager instead. Physical display capture, window-manager interactions, focus behavior, obscuration, and other operating systems stay unverified by this skill.

## Cleanup

Every drive stops its own consumer and Xvfb server in `finally` and removes that drive's authentication and scratch state. Shutdown gives the process group up to two seconds to exit before escalation. A retained X11 lock or socket makes the drive fail and is recorded in `display-cleanup.json`. At the end of the run, including after failures, execute:

```sh
"$bwc_control" cleanup --run-dir "$bwc_run_dir"
```

Require `CLEAN`. Cleanup uses stored process identities, never process-name matching. It removes only the marked private build directory and owned processes. After owned writers finish, it snapshots retained evidence, removes scratch, and compares the resulting snapshot. Scratch is excluded even when nested inside the run directory. It writes `cleanup.json` with the baseline hashes and the actual comparison result. Confirm `scratch_removed: true`, `evidence_preserved: true`, and the feature's `result.json` and transcript still exist. Cleanup is idempotent.

After full Cleanup, that run has no prepared binaries. Keep its evidence and launch into a new directory before any later drive.

## Helpers

`scripts/control.py` is executable. Its complete public command surface is `setup-xvfb`, `launch --run-dir`, `doctor --run-dir`, `drive --run-dir --feature [--entry]`, and `cleanup --run-dir`; invocations appear above. Use `--help` on a command for its accepted choices.

`scripts/x11.c` is the source of the compiled X11 observer and driver. The coordinator invokes its `doctor`, `find TITLE`, `snapshot TITLE FILE.ppm`, `resize TITLE W H`, `hide TITLE`, and `close-event TITLE` commands with the private display credentials. Do not run it against a shared display. The `.bend` files in `assets/` are verification consumers copied beside the unchanged library in scratch storage at launch.

Use `/maintain-verification-skill` to audit this feature map after the app changes. Use `/maintain-formal-verification-skill` for the separate TLA+ models.
