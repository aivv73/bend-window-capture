# bend-window-capture live verification map

Read this index before driving the native library. These four files are the maintained recipes for the initial live map.

## Baseline preconditions

- Launch with the parent skill's commands from a fresh evidence directory.
- Require Bend 2.0.40, Clang, Python 3, X11 headers and libraries, Xvfb, `xauth`, and XKB support.
- Require the build doctor to pass. Every drive also checks its private empty TrueColor display.
- Use `$bwc_control` and `$bwc_run_dir` from the Launch section.
- Drive serially within a run. Each command creates a new PTY and X11 server; no feature depends on an earlier drive's window.

## Driving conventions

- Invoke the helper through the commands in each feature file.
- Use exact window titles on the private display, not coordinates or windows from the user's desktop.
- Require exit code 0 and the feature's observable output. A skipped, unreachable, or failed command is not a pass.
- Preserve the per-drive evidence path printed by the helper.
- After failure, the helper tears down that display. Run Doctor again before the next drive. If the build is stale, clean up and launch a fresh run.

## Proof and skip reporting

- CLI proof includes the argv, stdout, stderr, and exit code.
- Consumer proof includes the action sequence, external geometry and screenshots, reported capture result, and empty post-close window list.
- Report every entry point attempted. Passing the prepared binary does not verify the check-script entry or make the unsupported source-only command work.
- Report missing OS, compiler, X11, authentication, or server prerequisites with the attempted command. Do not substitute controlled-boundary tests.
- Cleanup removes scratch state and processes while preserving evidence and its hashes in `cleanup.json`.

## Features

- [Capture the documented quadrants](example.md): the prepared native binary and project check script, with the unsupported source-only route recorded as a limitation.
- [Read pixels after a geometry change and window closure](pixels.md): actual dimensions, RGB storage, power-of-two capacity, and zero padding.
- [Handle an unsuitable window and retain ownership](recoverable-failure.md): EAGAIN, a usable returned window, and explicit close.
- [Keep queued window events](events.md): a close request remains observable after capture.

The native library on Linux/X11 is this seed map's scope. JavaScript and other native backends return ENOTSUP but require separate platform journeys. The existing formal-verification skills cover their modeled or controlled-boundary behavior.
