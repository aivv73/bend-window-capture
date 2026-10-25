# Read a Bend-owned X11 window's client pixels into an affine RGB array.
# Apache-2.0. Derived from bendlang/bend b3a0a2c58024681913a75fe4f303530e4527f3a4.
# Native bridge validated on Bend 2.0.39, Linux/X11. Other backends return ENOTSUP.
# Import bend-window-capture@0.1.0.0/capture.bend as C, then call C.Window.capture(window).
# The same affine owner returns outside Result on success and failure.
# Capture dimensions are the actual client dimensions at readback, not the requested size.
# Pixels are 0x00RRGGBB, top-left row-major. width * height is the logical length.
# Array capacity rounds up to a power of two. Padding is zero.
# Capture owns its pixels independently of the window and remains usable after close.
# The client must be viewable, fully on-screen, and unobscured for reliable pixel content.
# XSync completes prior output without discarding queued events.
# BendWin and Array packing are runtime internals. Revalidate after compiler updates.
# Source: https://github.com/bendlang/bend/commit/b3a0a2c58024681913a75fe4f303530e4527f3a4
import Base

type Capture is Type:
  Capture{width: U32, height: U32, pixels: Array<U32>}

def Window.capture(window: Window) ->
  IO(Window & Result<&1, &1, U32 & String, Capture>):
  import "./capture.c"
  import "./capture.js"
