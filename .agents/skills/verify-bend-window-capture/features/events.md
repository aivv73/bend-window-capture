# Keep queued window events

Capture pixels without losing a queued window-close request, then observe that event through the normal next frame.

## Sub-features

- `events-queue` queues the X11 window-close protocol message before capture.
- `events-preserved` exposes `Close{}` from the next public `Window.frame` call.
- `events-capture` still captures successfully and closes the returned window.

## How to get to it (user POV)

- Draw a window with `Window.frame`.
- While the window has a pending close request, call `C.Window.capture`.
- Obtain the next frame's event list and handle the retained `Close{}` event before closing the window.

## Driving it with control.py

Preconditions:

- Launch and Doctor pass. The consumer pauses after drawing, before capture.
- The private X11 server supports the standard `WM_PROTOCOLS` and `WM_DELETE_WINDOW` client-message route used by the window.

- **Queue the close request.** Run `"$bwc_control" drive --run-dir "$bwc_run_dir" --feature events`. The driver finds `BWC live probe` after `READY`, sends the normal `WM_DELETE_WINDOW` message, and synchronizes that connection before releasing capture.
- **Capture and read events.** The driver types `g`; the consumer calls capture, then calls `Window.frame` using the returned window and checks its event list.
- **Proof.** Require stdout `READY`, `CLOSED`, and `CAPTURE_DONE CLOSE_EVENT true`, in that order, plus exit 0. Retain the queued-close action report, the pre-capture screenshot, and the empty post-close window list.

## Gotchas

- The close message requests closure; it does not destroy the drawable directly. Destroying the window would test a different failure path.
- The event must be queued before capture starts. A fixed sleep or sending it after the next frame does not prove preservation across capture.
- This journey proves the standard queued close event on Xvfb. Pointer, keyboard, focus, and physical window-manager input paths remain separate coverage.
