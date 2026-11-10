/* Deterministic X11 boundary for the real Bend-generated program.
 * Inserted after BendWin and runtime helpers, before window_open_run.
 * No capture control flow or Bend allocation/packing helper is replaced. */
static int v_open, v_closed, v_framed, v_images, v_destroyed, v_syncs, v_queries;
static int v_forwarded, v_read, v_expected, v_width = 64, v_height = 64;
static Term v_owner;
static _XPrivDisplay v_display;
static Visual v_visual;
static XImage v_image;
static u32 v_saved[8192];
static u64 v_count, v_capacity, v_buffer;
static int (*v_handler)(Display*, XErrorEvent*);

static bool v_case(const char* name) {
  const char* value = getenv("VERIFY_CASE");
  return value != NULL && strcmp(value, name) == 0;
}
static void v_require(bool condition, const char* rule) {
  if (!condition) {
    fprintf(stderr, "VERIFY: %s\n", rule);
    exit(91);
  }
}
static int v_previous(Display* display, XErrorEvent* event) {
  v_forwarded++;
  return 0;
}
static int (*v_set_handler(int (*handler)(Display*, XErrorEvent*)))(Display*, XErrorEvent*) {
  if (handler == v_previous)
    v_require(v_display->last_request_read == v_display->request,
              "all capture requests are drained before handler restoration");
  int (*old)(Display*, XErrorEvent*) = v_handler;
  v_handler = handler;
  return old;
}
static void v_error(Display* display, unsigned long serial, int code) {
  XErrorEvent event = { .serial = serial, .error_code = code };
  v_handler(display, &event);
}
static int v_sync(Display* display, Bool discard) {
  v_require(discard == False, "queued events must not be discarded");
  v_syncs++;
  v_display->request += 4;
  unsigned long serial = v_display->request - 1;
  if (v_syncs == 1 && v_case("pending")) v_error(display, serial, BadWindow);
  if (v_syncs == 2) {
    if (v_case("late-match")) v_error(display, serial, BadMatch);
    if (v_case("late-value")) v_error(display, serial, BadValue);
    if (v_case("late-drawable")) v_error(display, serial, BadDrawable);
    if (v_case("late-other")) v_error(display, serial, BadAccess);
    if (v_case("local-and-protocol")) v_error(display, serial, BadWindow);
    if (v_case("two-errors")) {
      v_error(display, serial, BadValue);
      v_error(display, serial, BadWindow);
    }
    if (v_case("unrelated")) {
      v_error((Display*)(uintptr_t)1, serial, BadWindow);
      v_error(display, 0, BadWindow);
      v_error(display, NextRequest(display), BadWindow);
    }
  }
  v_display->last_request_read = v_display->request;
  return 0;
}
static Status v_attributes(Display* display, Window window, XWindowAttributes* attrs) {
  bool root = window == 1;
  if (!root) v_queries++;
  v_display->request++;
  memset(attrs, 0, sizeof(*attrs));
  attrs->width = root ? 200000 : v_width;
  attrs->height = root ? 200000 : v_height;
  attrs->map_state = IsViewable;
  attrs->root = 1;
  attrs->visual = &v_visual;
  if (!root && v_queries == 1) {
    if (v_case("query")) return 0;
    if (v_case("dimensions")) attrs->width = 0;
    if (v_case("hidden") || v_case("local-and-protocol")) attrs->map_state = IsUnmapped;
    if (v_case("overflow")) attrs->width = attrs->height = 65536;
  }
  if (root && v_case("root")) return 0;
  if (!root && v_queries == 2) {
    if (v_case("after-query")) return 0;
    if (v_case("changed-width")) attrs->width++;
    if (v_case("changed-height")) attrs->height++;
    if (v_case("unmapped-after")) attrs->map_state = IsUnmapped;
  }
  return 1;
}
static Bool v_translate(Display* d, Window a, Window b, int x, int y,
                        int* out_x, int* out_y, Window* child) {
  v_display->request++;
  *out_x = v_case("offscreen") ? -1 : 0;
  *out_y = 0;
  *child = 0;
  return !v_case("translate");
}
static XImage* v_get_image(Display* display, Drawable drawable, int x, int y,
                           unsigned int width, unsigned int height,
                           unsigned long planes, int format) {
  v_display->request++;
  if (v_case("read")) return NULL;
  v_require(v_images == 0, "only one temporary image");
  v_images++;
  v_image.width = width;
  v_image.height = height;
  v_image.red_mask = v_case("mask-zero") ? 0 : 0xff0000;
  v_image.green_mask = v_case("mask-overlap") ? 0xff0000 : 0xff00;
  v_image.blue_mask = v_case("mask-holes") ? 5 : 0xff;
  return &v_image;
}
static unsigned long v_get_pixel(XImage* image, int x, int y) {
  v_require(v_images == 1, "pixel read requires a live XImage");
  v_read++;
  if (v_case("small") || v_case("grid")) return (unsigned long)(y * v_width + x + 1);
  return y < v_height / 2 ? (x < v_width / 2 ? 0xff0000 : 0xff00)
                         : (x < v_width / 2 ? 0xff : 0xffffff);
}
static int v_destroy_image(XImage* image) {
  v_require(v_images == 1, "XImage is destroyed exactly once");
  v_images--;
  v_destroyed++;
  return 0;
}
static u64 v_allocate_pixels(Env e, u32 words) {
  u64 loc = heap_alloc(e, words);
  memset(e.mem + loc, 0xa5, (1ULL << words) * sizeof(u64));
  return loc;
}
