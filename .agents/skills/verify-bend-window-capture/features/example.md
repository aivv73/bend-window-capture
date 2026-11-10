# Capture the documented quadrants

Run the example to draw red, green, blue, and white quadrants, capture their corner pixels, close the window, and print the result.

## Sub-features

- `example-binary` runs the compiled native example.
- `example-check` runs the existing project check script, including its ownership proof and exact output comparison.
- `example-close` leaves no window after reporting pixels.

## How to get to it (user POV)

- Compile `examples/capture.bend` with `bend examples/capture.bend -o capture`, then run the binary.
- Run `./scripts/check.sh` with a usable X11 display.

## Driving it with control.py

Preconditions:

- Launch and Doctor pass with the pinned compiler and real X11 prerequisites.
- No application instance is shared between commands.

- **Compiled example.** Run `"$bwc_control" drive --run-dir "$bwc_run_dir" --feature example --entry binary`. Require exit 0 and the exact stdout line `64x64 16711680 65280 255 16777215`.
- **Project check.** Run `"$bwc_control" drive --run-dir "$bwc_run_dir" --feature example --entry check`. Require `ALL PROOFS CHECK` and `PASS: dimensions, RGB quadrants, row order, and pixels after close`.
- **Proof.** In each printed evidence directory, require `result.json` with `passed: true`, the real command and output files, and `window-after.stdout.txt` containing an empty `windows` list. Retain both native entry-point results.

## Gotchas

- The example exits too quickly to rely on a screenshot of its open window. Its user-facing proof is the printed capture values, read after close, plus the independent post-exit window list.
- `bend examples/capture.bend` without `-o` is an unsupported window route on this compiler. It was attempted on the healthy private display and exited 95 with `Window.open: no display`. The README now compiles first. The diagnostic command `"$bwc_control" drive --run-dir "$bwc_run_dir" --feature example --entry bend` retains a FAIL result; do not count it as successful capture or silently accept its error.
- A shared desktop can position or obscure the window and produce EAGAIN. The helper uses an isolated authenticated Xvfb server without a window manager.
- The headless path does not establish behavior under the user's compositor or on another native backend.
