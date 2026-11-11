// Read and drive only the private X11 server selected by DISPLAY and XAUTHORITY.
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void fail(const char* text) { fprintf(stderr, "%s\n", text); exit(1); }
static Window* children(Display* d, Window root, unsigned int* count) {
  Window parent, actual, *out = NULL;
  if (!XQueryTree(d, root, &actual, &parent, &out, count)) fail("Cannot query X11 tree");
  return out;
}
static Window find(Display* d, Window root, const char* name) {
  unsigned int count;
  Window* list = children(d, root, &count);
  Window found = 0;
  for (unsigned int i = 0; i < count; i++) {
    char* title = NULL;
    if (XFetchName(d, list[i], &title) && title != NULL) {
      if (!strcmp(title, name)) found = list[i];
      XFree(title);
    }
  }
  if (list) XFree(list);
  return found;
}
static void geometry(Display* d, Window win) {
  XWindowAttributes attrs;
  if (!XGetWindowAttributes(d, win, &attrs)) fail("Cannot query window geometry");
  printf("{\"window\":%lu,\"width\":%d,\"height\":%d,\"map_state\":%d,\"depth\":%d}",
    win, attrs.width, attrs.height, attrs.map_state, attrs.depth);
}
static unsigned int channel(unsigned long value, unsigned long mask) {
  if (!mask) fail("Unsupported screenshot mask");
  value &= mask;
  while (!(mask & 1)) { mask >>= 1; value >>= 1; }
  return (value * 255 + mask / 2) / mask;
}
int main(int argc, char** argv) {
  if (argc < 2) fail("Usage: x11 doctor | find TITLE | resize TITLE W H | hide TITLE | close-event TITLE | snapshot TITLE FILE.ppm");
  Display* d = XOpenDisplay(NULL);
  if (!d) fail("Cannot connect to the private X11 display");
  int screen = DefaultScreen(d);
  Window root = RootWindow(d, screen);
  if (!strcmp(argv[1], "doctor")) {
    unsigned int count;
    Window* list = children(d, root, &count);
    printf("{\"width\":%d,\"height\":%d,\"depth\":%d,\"true_color\":%s,\"windows\":[",
      DisplayWidth(d, screen), DisplayHeight(d, screen), DefaultDepth(d, screen),
      DefaultVisual(d, screen)->class == TrueColor ? "true" : "false");
    for (unsigned int i = 0; i < count; i++) { if (i) printf(","); geometry(d, list[i]); }
    printf("]}\n");
    if (list) XFree(list);
    XCloseDisplay(d);
    return 0;
  }
  if (argc < 3) fail("A window title is required");
  Window win = find(d, root, argv[2]);
  if (!win) { XCloseDisplay(d); return 3; }
  if (!strcmp(argv[1], "resize")) {
    if (argc != 5 || atoi(argv[3]) <= 0 || atoi(argv[4]) <= 0) fail("Positive width and height required");
    XResizeWindow(d, win, atoi(argv[3]), atoi(argv[4]));
  } else if (!strcmp(argv[1], "hide")) {
    XUnmapWindow(d, win);
  } else if (!strcmp(argv[1], "close-event")) {
    XEvent event = {0};
    event.xclient.type = ClientMessage;
    event.xclient.window = win;
    event.xclient.message_type = XInternAtom(d, "WM_PROTOCOLS", False);
    event.xclient.format = 32;
    event.xclient.data.l[0] = XInternAtom(d, "WM_DELETE_WINDOW", False);
    event.xclient.data.l[1] = CurrentTime;
    if (!XSendEvent(d, win, False, NoEventMask, &event)) fail("Cannot send window close event");
  } else if (!strcmp(argv[1], "snapshot")) {
    if (argc != 4) fail("Screenshot path required");
    XWindowAttributes attrs;
    XGetWindowAttributes(d, win, &attrs);
    XImage* image = XGetImage(d, win, 0, 0, attrs.width, attrs.height, AllPlanes, ZPixmap);
    if (!image) fail("Cannot read screenshot");
    FILE* out = fopen(argv[3], "wb");
    if (!out) fail("Cannot write screenshot");
    fprintf(out, "P6\n%d %d\n255\n", attrs.width, attrs.height);
    for (int y = 0; y < attrs.height; y++) for (int x = 0; x < attrs.width; x++) {
      unsigned long pixel = XGetPixel(image, x, y);
      fputc(channel(pixel, image->red_mask), out);
      fputc(channel(pixel, image->green_mask), out);
      fputc(channel(pixel, image->blue_mask), out);
    }
    fclose(out);
    XDestroyImage(image);
  } else if (strcmp(argv[1], "find")) fail("Unknown X11 action");
  XSync(d, False);
  geometry(d, win);
  printf("\n");
  XCloseDisplay(d);
  return 0;
}
