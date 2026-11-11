/* Observe the result without consuming it; the compiled Bend caller still runs. */
Term window_capture_run(Env e, Term* f, IoWork* work) {
  v_require(v_open && v_framed && !v_closed, "capture runs while the window is owned");
  v_owner = f[0];
  Term pair = v_capture_impl(e, f, work);
  u64 at = term_peek(e.mem, pair);
  v_require(e.mem[at] == v_owner, "capture returns the original Window token");
  v_require(v_syncs == 2, "both synchronization boundaries execute");
  v_require(v_handler == v_previous, "previous X11 error handler is restored");
  v_require(window_capture_trap == NULL, "stack-local trap context is cleared");
  v_require(v_images == 0, "temporary XImage is released before returning");
  v_require(!v_case("unrelated") || v_forwarded == 3, "unrelated errors are forwarded");
  Term result = e.mem[at + 1];
  if (v_expected != 0) {
    v_require(term_aux(result) == CID_Fail, "unsuitable readback returns Fail");
    Term error = e.mem[term_peek(e.mem, result)];
    v_require(e.mem[term_peek(e.mem, error)] == (u32)v_expected,
              "error mapping and first-error precedence");
  } else {
    v_require(term_aux(result) == CID_Done, "valid readback returns Done");
    Term capture = e.mem[term_peek(e.mem, result)];
    u64 out = term_peek(e.mem, capture);
    v_require(e.mem[out] == v_width && e.mem[out + 1] == v_height,
              "actual client dimensions are returned");
    Term array = e.mem[out + 2];
    v_buffer = term_peek(e.mem, array);
    v_count = (u64)v_width * v_height;
    v_capacity = 1ULL << blk_cls(array);
    v_require(v_capacity >= v_count && v_capacity < 2 * v_count,
              "array uses the next power-of-two capacity");
    v_require(v_read == v_count && v_destroyed == 1, "all pixels copied before image release");
    for (u64 i = 0; i < v_capacity; i++) {
      u32 actual = *blk_ptr(e.mem, v_buffer, i);
      v_saved[i] = actual;
      if (i >= v_count) v_require(actual == 0, "array padding is zero");
      else if (v_case("small") || v_case("grid"))
        v_require(actual == i + 1, "pixel order is top-left row-major");
      else {
        u64 x = i % v_width, y = i / v_width;
        u32 expected = y < v_height / 2 ? (x < v_width / 2 ? 0xff0000 : 0xff00)
                                       : (x < v_width / 2 ? 0xff : 0xffffff);
        v_require(actual == expected, "RGB quadrant positions and row order");
      }
    }
  }
  return pair;
}
