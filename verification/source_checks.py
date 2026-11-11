"""Run actual project code with controlled external effects, never editing the checkout."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ("capture.bend", "capture.c", "capture.js", "examples/capture.bend", "scripts/check.sh")
MUTATIONS = {
    "window-lifecycle": ("examples/capture.bend",
        "IO.bind(Unit, Unit, Window.close(window), u => captured(result))", "captured(result)"),
    "capture-transaction": ("capture.c", "after.width != attrs.width", "false"),
    "x11-error-trap": ("capture.c", "  XSetErrorHandler(trap.previous);", "  /* restore removed */"),
    "pixel-ownership": ("capture.c",
        "  memset(e.mem + pixels, 0, (1ULL << words) * sizeof(u64));", "  /* zeroing removed */"),
    "effect-registration": ("capture.js", "io_eff(CID(Window.capture), window_capture);",
        "/* registration removed */"),
    "check-runner": ("scripts/check.sh", "trap 'rm -rf \"$build_dir\"' EXIT", "# cleanup removed"),
    "x11-first-error": ("capture.c", "if (trap->error == 0)", "if (true)"),
    "pixel-release": ("capture.c", "    if (image != NULL) {\n      XDestroyImage(image);\n    }",
        "    /* error-path image release removed */"),
    "pixel-row-order": ("capture.c", "(u64)y * attrs.width + x)", "x)"),
    "pixel-channel": ("capture.c", "window_capture_channel(pixel, image->red_mask) << 16",
        "window_capture_channel(pixel, image->red_mask) << 8"),
    "x11-drain-order": ("capture.c", "    XSync(dpy, False);",
        "    XSync(dpy, False);\n    XSync(dpy, False);"),
    "native-unsupported": ("capture.c", "  return io_tup(e, f[0], io_fail(e, ENOTSUP,",
        "  return io_tup(e, f[0], io_fail(e, EIO,"),
}
EXTRA_EDITS = {
    "x11-drain-order": ("  XSync(dpy, False);\n  XSetErrorHandler(trap.previous);",
        "  XSetErrorHandler(trap.previous);"),
}


def run(args, **kwargs):
    return subprocess.run(args, text=True, capture_output=True, timeout=90, **kwargs)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def replace_once(source, old, new):
    require(source.count(old) == 1, f"source seam changed; review model correspondence: {old}")
    return source.replace(old, new, 1)


def replace_body(source, name, body):
    start = source.index(f"Term {name}(")
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    # These runtime bodies have no brace characters inside string literals.
    while depth:
        if source[end] == "{":
            depth += 1
        elif source[end] == "}":
            depth -= 1
        end += 1
    return source[:opening + 1] + "\n" + body + "\n}" + source[end:]


def scratch_copy(dest, mutation):
    for name in FILES:
        path = dest / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, path)
    if mutation:
        name, before, after = MUTATIONS[mutation]
        path = dest / name
        path.write_text(replace_once(path.read_text(), before, after))
        if mutation in EXTRA_EDITS:
            before, after = EXTRA_EDITS[mutation]
            path.write_text(replace_once(path.read_text(), before, after))


ERRORS = {
    "pending": 2, "query": 5, "dimensions": 22, "hidden": 11,
    "offscreen": 11, "root": 11, "translate": 11, "overflow": 75,
    "visual": 95, "read": 5, "mask-zero": 95, "mask-overlap": 95,
    "mask-holes": 95, "after-query": 11, "changed-width": 11,
    "changed-height": 11, "unmapped-after": 11, "late-match": 11,
    "late-value": 22, "late-drawable": 2, "late-other": 5,
    "local-and-protocol": 2, "two-errors": 22,
}


def native(dest, area, unsupported=False):
    require(shutil.which("bend") and shutil.which("clang"), "install Bend 2.0.40 and Clang")
    version = run(["bend", "version"])
    require(version.returncode == 0 and version.stdout.strip() == "bend 2.0.40",
            "native instrumentation requires Bend 2.0.40; revalidate after compiler changes")
    compiled = run(["bend", "examples/capture.bend", "-o", str(dest / "program.c")], cwd=dest)
    require(compiled.returncode == 0, f"Bend compilation failed: {compiled.stdout}{compiled.stderr}")
    source = (dest / "program.c").read_text()
    support = (ROOT / "verification/native-support.c").read_text()
    source = replace_once(source, "Term window_open_run(", support + "\nTerm window_open_run(")
    error_setup = "\n".join(f'if (v_case("{case}")) v_expected = {code};'
                            for case, code in ERRORS.items())
    source = replace_body(source, "window_open_run", r'''
  fprintf(stderr, "VERIFY:OPEN\n");
  if (v_case("open-fail")) return io_fail(e, EIO, "controlled open failure");
  BendWin* win = calloc(1, sizeof(BendWin));
  v_display = calloc(1, sizeof(*v_display));
  v_display->request = 10;
  v_display->last_request_read = 5;
  v_handler = v_previous;
  v_visual.class = v_case("visual") ? PseudoColor : TrueColor;
  if (v_case("small") || v_case("grid")) {
    v_width = atoi(getenv("VERIFY_WIDTH")); v_height = v_case("grid") ? 2 : 1;
  }
  win->dpy = (Display*)v_display;
  win->win = 100;
  v_open = 1;
''' + error_setup + r'''
  return io_done(e, io_hand((intptr_t)win));
''')
    source = replace_body(source, "window_frame_run", r'''
  v_require(v_open && !v_closed, "frame requires an owned window");
  v_framed = 1;
  return io_tup(e, f[0], io_tup(e, f[1], term_pak(CID_Nil, 0)));
''')
    source = replace_body(source, "window_close_run", r'''
  v_require(v_open && !v_closed, "window closes exactly once");
  v_require(f[0] == v_owner, "close consumes the returned Window token");
  free(v_display);
  free((void*)(uintptr_t)io_hand_v(f[0]));
  v_closed = 1;
  v_open = 0;
  for (u64 i = 0; i < v_capacity; i++)
    v_require(*blk_ptr(e.mem, v_buffer, i) == v_saved[i], "pixels survive Window.close");
  fprintf(stderr, "VERIFY:CLOSE\n");
  return term_pak(CID_Unit, 0);
''')
    # Observe real application report ordering; retain the original printing body.
    source = replace_once(source, "Term io_print_run(Env e, Term* f, IoWork* w) {",
        'Term io_print_run(Env e, Term* f, IoWork* w) {\n'
        '  v_require(v_closed, "report follows Window.close");')
    start = source.index("Term window_capture_run(")
    end = source.index("static void __attribute__((constructor)) window_capture_use", start)
    bridge = source[start:end]
    bridge = replace_once(bridge, "Term window_capture_run(", "Term v_capture_impl(")
    for original, substitute in {
        "XSetErrorHandler": "v_set_handler", "XSync": "v_sync",
        "XGetWindowAttributes": "v_attributes", "XTranslateCoordinates": "v_translate",
        "XGetImage": "v_get_image", "XGetPixel": "v_get_pixel",
        "XDestroyImage": "v_destroy_image",
    }.items():
        bridge = bridge.replace(original + "(", substitute + "(")
    bridge = replace_once(bridge, "u64 pixels = heap_alloc(e, words);",
                          "u64 pixels = v_allocate_pixels(e, words);")
    wrapper = (ROOT / "verification/native-wrapper.c").read_text()
    if unsupported:
        bridge = replace_once(bridge, "#if defined(__linux__) && !defined(__OBJC__)", "#if 0")
        wrapper = r'''
Term window_capture_run(Env e, Term* f, IoWork* work) {
  v_owner = f[0];
  Term pair = v_capture_impl(e, f, work);
  u64 at = term_peek(e.mem, pair);
  v_require(e.mem[at] == v_owner, "unsupported native backend returns the original Window token");
  Term result = e.mem[at + 1];
  v_require(term_aux(result) == CID_Fail, "unsupported native backend returns Fail");
  Term error = e.mem[term_peek(e.mem, result)];
  v_require(e.mem[term_peek(e.mem, error)] == ENOTSUP,
            "unsupported native backend returns ENOTSUP");
  v_require(v_images == 0 && v_syncs == 0, "unsupported backend performs no X11 capture");
  return pair;
}
'''
    source = source[:start] + bridge + wrapper + source[end:]
    (dest / "program.c").write_text(source)
    compiled = run(["clang", "-O1", "-pthread", str(dest / "program.c"),
                    "-o", str(dest / "program"), "-lX11", "-lm", "-ldl"])
    require(compiled.returncode == 0, f"Clang failed: {compiled.stderr[-4000:]}")
    cases = ["success", "hidden", "open-fail"] if area == "window-lifecycle" else ["success"]
    if unsupported:
        cases = ["unsupported"]
    if area in {"capture-transaction", "x11-error-trap", "pixel-ownership"}:
        cases += list(ERRORS) + ["unrelated"]
    samples = [(case, 64) for case in cases]
    if area == "pixel-ownership":
        samples += [("small", count) for count in (1, 3, 4, 5)] + [("grid", 3)]
    for case, width in samples:
        result = run([str(dest / "program"), "+RTS", "--threads", "1"],
                     env={**os.environ, "VERIFY_CASE": case, "VERIFY_WIDTH": str(width)})
        expected = 95 if unsupported else 5 if case == "open-fail" else ERRORS.get(case, 0)
        require(result.returncode == expected,
                f"{case}: exit {result.returncode}, expected {expected}: {result.stdout}{result.stderr}")
        require(case == "open-fail" or "VERIFY:CLOSE" in result.stderr,
                f"{case}: capture outcome was reported without closing the window")
        if expected == 0 and case not in {"small", "grid"}:
            require(result.stdout.strip() == "64x64 16711680 65280 255 16777215",
                    f"{case}: example prints incorrect dimensions or corner pixels: {result.stdout}")
    return len(samples)


def javascript(dest):
    script = r'''
const fs = require("node:fs"), vm = require("node:vm"), assert = require("node:assert/strict");
for (const platform of ["linux", "darwin", undefined]) {
  const handlers = [];
  const context = { Window: {capture: "capture"}, Fail: "Fail", CID: x => x,
    io_tup: (a, b) => [a, b], io_eff: (id, fn) => handlers.push([id, fn]) };
  if (platform) context.process = { platform };
  vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"), context);
  assert.equal(handlers.length, 1, "module evaluation registers one capture handler");
  assert.equal(handlers[0][0], "capture");
  const owner = {};
  const pair = handlers[0][1](owner);
  assert.equal(pair[0], owner, "unsupported backend preserves Window identity");
  assert.equal(pair[1].$, "Fail");
  assert.equal(pair[1].error[0], platform === "darwin" ? 45 : 95);
}
'''
    result = run(["node", "-e", script, str(dest / "capture.js")])
    require(result.returncode == 0, f"JavaScript effect lifecycle failed: {result.stderr}")
    return 3


def check_runner(dest):
    bin_dir = dest / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "bend"
    stub.write_text('''#!/usr/bin/env python3
import os, pathlib, sys
case = os.environ["VERIFY_CASE"]
if sys.argv[1] == "PROOF.bend":
    sys.exit(7 if case == "proof" else 0)
if case == "compile":
    sys.exit(8)
out = pathlib.Path(sys.argv[sys.argv.index("-o") + 1])
out.write_text("#!/bin/sh\\n" + ("exit 9\\n" if case == "run" else
    "echo wrong\\n" if case == "compare" else
    "echo '64x64 16711680 65280 255 16777215'\\n"))
out.chmod(0o755)
''')
    stub.chmod(0o755)
    for case in ("proof", "compile", "run", "compare", "success"):
        tmp = dest / f"temporary-{case}"
        tmp.mkdir()
        result = run(["bash", str(dest / "scripts/check.sh")], env={**os.environ,
            "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
            "TMPDIR": str(tmp), "VERIFY_CASE": case})
        require((result.returncode == 0) == (case == "success"),
                f"{case}: checker returned wrong status: {result.stdout}{result.stderr}")
        require(not list(tmp.iterdir()), f"{case}: checker leaked its temporary build directory")
    return 5


def check(area, mutation=False):
    with tempfile.TemporaryDirectory(prefix="capture-source-check-") as directory:
        dest = Path(directory)
        scratch_copy(dest, (area if mutation is True else mutation) or None)
        if area == "check-runner":
            return check_runner(dest)
        count = javascript(dest) if area == "effect-registration" else 0
        count += native(dest, area)
        if area == "effect-registration":
            count += native(dest, area, unsupported=True)
        return count
