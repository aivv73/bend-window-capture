# bend-window-capture

Capture a Bend-owned X11 window's client pixels into an affine RGB array.

Source code and issues: [aivv73/bend-window-capture on GitHub](https://github.com/aivv73/bend-window-capture).

Validated with Bend 2.0.40 on Linux with X11. Other native backends and JavaScript return `ENOTSUP`.
The bridge uses Bend runtime internals, so revalidate it after compiler updates.

## Run the example

Install [Bend 2.0.40](https://github.com/bendlang/bend/releases/tag/v2.0.40), Clang, and the X11 development headers.
On Debian or Ubuntu, install the native dependencies with `sudo apt-get install clang libx11-dev`.
Run this from a graphical X11 session with `DISPLAY` set:

```sh
git clone https://github.com/aivv73/bend-window-capture.git
cd bend-window-capture
mkdir -p build
bend examples/capture.bend -o build/capture
./build/capture
```

Build a native binary for X11 window effects. With Bend 2.0.40, running
`bend examples/capture.bend` directly reports `Window.open: no display` and
returns `ENOTSUP`, even when an X11 display is available.

The example draws four colored quadrants, captures them, closes the window, and prints its dimensions and corner pixels:

```text
64x64 16711680 65280 255 16777215
```

## Use the library

Import the published [BendHub package](https://hub.bend-lang.com/n/bend-window-capture):

```python
import Base
import bend-window-capture@0.1.0.4/capture.bend as C
```

For a local copy, keep `capture.bend`, `capture.c`, and `capture.js` together and import the module from your application:

```python
import Base
import ./capture.bend as C
```

Call `C.Window.capture(window)` to get this IO action:

```python
IO(Window & Result<&1, &1, U32 & String, C.Capture>)
```

Use `IO.bind` to receive the window alongside the `Result`. You retain ownership on success and failure.

The result contains either `Done{C.Capture{width, height, pixels}}` or `Fail{(code, message)}`.
See [the example](examples/capture.bend) for a complete program that closes the window before inspecting the result.

Pixels use `0x00RRGGBB` and run left to right, top to bottom. The logical pixel count is `width * height`.
Array capacity rounds up to the next power of two, with zero padding.
Dimensions reflect the actual client geometry at capture time.
The pixel array remains valid after the window closes.

The window must be viewable, fully on-screen, and unobscured for reliable pixels.
Capture synchronizes pending output without discarding queued events.
Errors include `EAGAIN` for unsuitable geometry or a window that changes during readback, and `ENOTSUP` for unsupported visuals or backends.

## Check the project

```sh
bend PROOF.bend
./scripts/check.sh
```

For a headless Linux check, install `xvfb` and `xauth`, then run:

```sh
xvfb-run -a ./scripts/check.sh
```

`LAWS.bend` records the ownership contract and native requirements.
`PROOF.bend` proves the structural ownership rule for returning a window beside either result.
Compiling the integration example also checks the library's types. The proof does not verify the foreign C implementation.
The integration check verifies actual dimensions, RGB quadrant positions, row order, and pixel access after closing the window.
Live checks on private Xvfb displays also verify resized dimensions, zero padding,
pixels after close, ownership after an `EAGAIN` failure, and a queued close event.
These checks do not cover every error path, physical displays, window-manager behavior, or other operating systems' ABIs.
Window effects use shared Xlib state and run on Bend's IO thread.

Six project-local skills model the window lifecycle, capture transaction, X11 error trap,
pixel ownership, effect registration, and check runner. Run `python3 -B verification/verify.py all`
to check their bounded TLA+ models and source behavior. Add `--mutations` to exercise the
broken variants. See the [verification results and flow diagrams](verification/RESULTS.md)
for skill links, prerequisites, bounds, and evidence. These checks supplement the Bend
ownership proof and the live X11 integration check.

The [live verification skill](.agents/skills/verify-bend-window-capture/SKILL.md)
and its [feature map](.agents/skills/verify-bend-window-capture/features/README.md)
drive the native example and public library API on private X11 servers, with
evidence retained after cleanup.

On pushes and pull requests, CI runs the ownership proof and native smoke check,
the tooling regressions, all six model/source suites with twelve source mutations,
and all five live drives. Cleanup runs even after failure. CI retains live evidence
and contract results in the `capture-verification` artifact for seven days.
The artifact includes the verifier log even when a failure prevents JSON results.

## Source and license

Imported from [bend-window-capture 0.1.0.0 on BendHub](https://hub.bend-lang.com/n/bend-window-capture),
package `0xfdc8da256837fef81553ec8530fb7431`.
The bridge derives from [bendlang/bend at b3a0a2c](https://github.com/bendlang/bend/commit/b3a0a2c58024681913a75fe4f303530e4527f3a4).

Licensed under [Apache-2.0](LICENSE). The original source attribution and license are preserved.
