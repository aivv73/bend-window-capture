# Read pixels after geometry changes and window closure

Capture a window whose actual client size differs from its requested size, then read the returned pixels after closing it.

## Sub-features

- `pixels-actual-size` reports the current 3×2 geometry after a window requested at 64×64 is resized.
- `pixels-rgb` returns the six drawn pixels as `0x00123456` values.
- `pixels-padding` exposes capacity 8 with two zero padding slots.
- `pixels-independent` reads the array after `Window.close` completes.

## How to get to it (user POV)

- Import the local `capture.bend` module in a Bend program.
- Open a window, draw with `Window.frame`, and call `C.Window.capture`.
- Close the returned window and consume the `Capture` dimensions and affine pixel array.

## Driving it with control.py

Preconditions:

- Launch and Doctor pass. The `pixels` consumer uses the unchanged local library.
- The private X11 server permits an explicit geometry change without a window manager.

- **Draw.** Run `"$bwc_control" drive --run-dir "$bwc_run_dir" --feature pixels`. The consumer prints `READY` with a viewable 64×64 window named `BWC live probe`.
- **Resize, redraw, and capture.** The driver resizes that real client to 3×2 and types `g`. The consumer redraws through `Window.frame`, captures, and prints `CAPTURED`. The driver independently screenshots the captured client before permitting close.
- **Read after close.** Require stdout lines `READY`, `CAPTURED`, `CLOSED`, and `PIXELS 3 2 8 1193046 1193046 1193046 1193046 1193046 1193046 0 0`, in that order.
- **Proof.** Require the resize geometry report, the six-pixel `window-captured.png`, the exact array output, and the empty post-close window list in the printed evidence directory.

## Gotchas

- The consumer draws one solid color. Quadrant positions and nonuniform row order are covered by the example feature.
- X11 can clear client contents on resize. The consumer must redraw before claiming that the resized window contains the original solid image; the pre-redraw screenshot is retained separately.
- The capacity is 8 but the logical length is 6. Padding values are not client pixels.
- This explicit X11 resize is a geometry-contract test. A desktop window manager may honor fixed-size hints and refuse a user drag to 3×2; that desktop journey is not claimed here.
- Unobscured TrueColor pixels and sufficient screen bounds are prerequisites. A geometry failure must remain a failure.
