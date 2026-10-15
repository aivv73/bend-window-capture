// SPDX-License-Identifier: Apache-2.0
// Extracted from bendlang/bend b3a0a2c58024681913a75fe4f303530e4527f3a4.
#ifdef CID(Window.capture)

#if defined(__linux__) && !defined(__OBJC__)

typedef struct {
  Display* dpy;
  unsigned long first;
  int (*previous)(Display*, XErrorEvent*);
  int error;
} WindowCaptureTrap;

// Window effects run on the IO thread; Xlib installs a process-wide handler.
static WindowCaptureTrap* window_capture_trap;

static int window_capture_error(Display* dpy, XErrorEvent* error) {
  WindowCaptureTrap* trap = window_capture_trap;
  if (dpy == trap->dpy && error->serial - trap->first
      < NextRequest(dpy) - trap->first) {
    if (trap->error == 0) {
      trap->error = error->error_code;
    }
    return 0;
  }
  return trap->previous(dpy, error);
}

static bool window_capture_mask(unsigned long mask) {
  if (mask == 0 || mask > UINT32_MAX) {
    return false;
  }
  while ((mask & 1) == 0) {
    mask >>= 1;
  }
  return (mask & (mask + 1)) == 0;
}

static u32 window_capture_channel(unsigned long pixel, unsigned long mask) {
  pixel &= mask;
  while ((mask & 1) == 0) {
    mask >>= 1;
    pixel >>= 1;
  }
  return ((u64)pixel * 255 + mask / 2) / mask;
}

#endif

Term window_capture_run(Env e, Term* f, IoWork* work) {
#if defined(__linux__) && !defined(__OBJC__)
  BendWin* win = (BendWin*)(intptr_t)io_hand_v(f[0]);
  Display* dpy = win->dpy;
  WindowCaptureTrap trap = { .dpy = dpy,
    .first = LastKnownRequestProcessed(dpy) + 1 };
  window_capture_trap = &trap;
  // The dedicated connection's pending output belongs to this owner too.
  trap.previous = XSetErrorHandler(window_capture_error);
  XImage* image = NULL;
  XWindowAttributes attrs, after, root;
  u32 code = 0;
  const char* why = NULL;
  u64 count = 0;
  do {
    XSync(dpy, False);
    if (trap.error != 0) {
      break;
    }
    if (!XGetWindowAttributes(dpy, win->win, &attrs)) {
      code = EIO;
      why = "Window.capture: cannot query client geometry";
      break;
    }
    if (attrs.width <= 0 || attrs.height <= 0) {
      code = EINVAL;
      why = "Window.capture: invalid client dimensions";
      break;
    }
    int x, y;
    Window child;
    if (attrs.map_state != IsViewable
        || !XGetWindowAttributes(dpy, attrs.root, &root)
        || !XTranslateCoordinates(dpy, win->win, attrs.root, 0, 0,
          &x, &y, &child)
        || x < 0 || y < 0 || (u64)x + attrs.width > root.width
        || (u64)y + attrs.height > root.height) {
      code = EAGAIN;
      why = "Window.capture: client must be viewable and fully on-screen";
      break;
    }
    count = (u64)attrs.width * attrs.height;
    if (count > (1ULL << 31)) {
      code = EOVERFLOW;
      why = "Window.capture: pixel count exceeds Array capacity";
      break;
    }
    if (attrs.visual->class != TrueColor) {
      code = ENOTSUP;
      why = "Window.capture: unsupported color visual";
      break;
    }
    image = XGetImage(dpy, win->win, 0, 0, attrs.width, attrs.height,
      AllPlanes, ZPixmap);
    if (image == NULL) {
      code = EIO;
      why = "Window.capture: cannot read client pixels";
      break;
    }
    unsigned long r = image->red_mask, g = image->green_mask,
      b = image->blue_mask;
    if (!window_capture_mask(r) || !window_capture_mask(g)
        || !window_capture_mask(b) || (r & g) || (r & b) || (g & b)) {
      code = ENOTSUP;
      why = "Window.capture: unsupported color masks";
      break;
    }
    if (!XGetWindowAttributes(dpy, win->win, &after)
        || after.width != attrs.width || after.height != attrs.height
        || after.map_state != IsViewable) {
      code = EAGAIN;
      why = "Window.capture: client changed during readback";
    }
  } while (false);
  XSync(dpy, False);
  XSetErrorHandler(trap.previous);
  window_capture_trap = NULL;
  if (trap.error != 0) {
    code = trap.error == BadWindow || trap.error == BadDrawable ? ENOENT
      : trap.error == BadMatch ? EAGAIN : trap.error == BadValue ? EINVAL : EIO;
    why = "Window.capture: X11 protocol error";
  }
  if (code != 0) {
    if (image != NULL) {
      XDestroyImage(image);
    }
    return io_tup(e, f[0], io_fail(e, code, why));
  }
  u32 depth = 0;
  while ((1ULL << depth) < count) {
    depth += 1;
  }
  u32 words = blk_wcls(false, depth);
  u64 pixels = heap_alloc(e, words);
  memset(e.mem + pixels, 0, (1ULL << words) * sizeof(u64));
  for (int y = 0; y < attrs.height; y += 1) {
    for (int x = 0; x < attrs.width; x += 1) {
      unsigned long pixel = XGetPixel(image, x, y);
      *blk_ptr(e.mem, pixels, (u64)y * attrs.width + x)
        = window_capture_channel(pixel, image->red_mask) << 16
        | window_capture_channel(pixel, image->green_mask) << 8
        | window_capture_channel(pixel, image->blue_mask);
    }
  }
  XDestroyImage(image);
  u64 out = heap_alloc(e, cls_fit(3));
  e.mem[out] = io_seal(e, (u32)attrs.width, CID(Capture));
  e.mem[out + 1] = io_seal(e, (u32)attrs.height, CID(Capture));
  e.mem[out + 2] = io_seal(e, term_buf(depth, pixels), CID(Capture));
  return io_tup(e, f[0], io_done(e, term_ctr(CID(Capture), out)));
#else
  return io_tup(e, f[0], io_fail(e, ENOTSUP,
    "Window.capture: client capture is unavailable on this backend"));
#endif
}

static void __attribute__((constructor)) window_capture_use(void) {
  io_eff(CID(Window.capture), window_capture_run);
}

#endif
