import Base

# Structural ownership rule: the same affine window can be returned beside
# either outcome without inspecting or consuming that outcome.
# The native implementation is outside the formal proof boundary.
law return_window:
  for -A: Type
  for window: Window
  for result: Result<&1, &1, U32 & String, A>
  Window & Result<&1, &1, U32 & String, A>

# Native obligations, checked by integration tests rather than formal proofs:
# - Report actual client dimensions and top-left, row-major 0x00RRGGBB pixels.
# - Round Array capacity up to a power of two and zero its padding.
# - Keep captured pixels usable after Window.close.
# - Synchronize output without discarding queued events.
# - Return ENOTSUP on unsupported backends.
# Window operations share Xlib state and must stay on the IO thread.
