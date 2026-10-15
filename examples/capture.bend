import Base
import ../capture.bend as C

def print_pixels(width: U32, height: U32, tl: U32, tr: U32, bl: U32,
  last: Array<U32> & U32) -> IO(Unit):
  (pixels, br) = last
  IO.print(U32.show(width) ++ "x" ++ U32.show(height) ++ " "
    ++ U32.show(tl) ++ " " ++ U32.show(tr) ++ " "
    ++ U32.show(bl) ++ " " ++ U32.show(br))

def read_bottom(width: U32, height: U32, tl: U32, tr: U32,
  sample: Array<U32> & U32) -> IO(Unit):
  (pixels, bl) = sample
  print_pixels(width, height, tl, tr, bl, Array.get(U32, pixels, 4095))

def read_right(width: U32, height: U32, tl: U32,
  sample: Array<U32> & U32) -> IO(Unit):
  (pixels, tr) = sample
  read_bottom(width, height, tl, tr, Array.get(U32, pixels, 4032))

def read_left(width: U32, height: U32, sample: Array<U32> & U32) -> IO(Unit):
  (pixels, tl) = sample
  read_right(width, height, tl, Array.get(U32, pixels, 63))

def report(capture: C.Capture) -> IO(Unit):
  match capture:
    case C.Capture{width, height, pixels}:
      read_left(width, height, Array.get(U32, pixels, 0))

def captured(result: Result<&1, &1, U32 & String, C.Capture>) -> IO(Unit):
  match result:
    case Done{capture}:
      report(capture)
    case Fail{(code, message)}:
      IO.die(Unit, code, message)

def close_and_report(pair: Window & Result<&1, &1, U32 & String, C.Capture>) -> IO(Unit):
  (window, result) = pair
  IO.bind(Unit, Unit, Window.close(window), u => captured(result))

def capture_frame(frame: Window & Image & List<Event>) -> IO(Unit):
  (window, image, events) = frame
  IO.bind(Window & Result<&1, &1, U32 & String, C.Capture>, Unit,
    C.Window.capture(window), close_and_report)

def opened(result: Result<&1, &1, U32 & String, Window>) -> IO(Unit):
  match result:
    case Fail{(code, message)}:
      IO.die(Unit, code, message)
    case Done{window}:
      IO.bind(Window & Image & List<Event>, Unit,
        Window.frame(window,
          Qua{Pix{16711680}, Pix{65280}, Pix{255}, Pix{16777215}}),
        capture_frame)

def main() -> IO(Unit):
  IO.bind(Result<&1, &1, U32 & String, Window>, Unit,
    Window.open("Window capture", 64, 64), opened)
