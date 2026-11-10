# Handle an unsuitable window and retain ownership

Capture an unmapped window, receive EAGAIN beside the same usable window, and close that returned owner explicitly.

## Sub-features

- `failure-eagain` rejects a window that is not viewable.
- `failure-owner` keeps the returned window usable for `Window.set_title`.
- `failure-close` closes the returned window after handling the error.

## How to get to it (user POV)

- Call `C.Window.capture(window)` when the client window is unsuitable for capture.
- Match the result while retaining the returned window beside it.
- Handle the error, use the returned window if needed, then close it.

## Driving it with control.py

Preconditions:

- Launch and Doctor pass. The real window is alive before it is hidden.
- The private server allows the driver to unmap the client window.

- **Make capture unsuitable.** Run `"$bwc_control" drive --run-dir "$bwc_run_dir" --feature recoverable-failure`. After `READY`, the driver unmaps `BWC live probe` and verifies its map state independently.
- **Handle failure.** The driver types `g`. Require `RECOVERED 11`, where 11 is Linux EAGAIN. The consumer changes the returned window's title through the public API.
- **Verify ownership.** Require `returned-window.stdout.txt` to identify the same X11 window ID as `window-before.stdout.txt`, found by the title `BWC recovered` and still unmapped. The independent lookup must succeed before the driver permits close.
- **Close.** The driver types the second `g`. Require `CLOSED`, exit 0, and an empty post-close window list. The full stdout sequence is `READY`, `RECOVERED 11`, `CLOSED`.

## Gotchas

- An unmapped live window is different from a destroyed drawable. This journey does not prove that an ENOENT result leaves the X11 drawable alive.
- EAGAIN does not trigger an automatic retry. The caller decides how to proceed.
- The errno value 11 applies to this Linux drive. Do not generalize it to every platform.
- Do not hide a window from the user's desktop. The driver operates only on its owned display.
