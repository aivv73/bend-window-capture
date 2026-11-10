import Base
import ./capture.bend as C

# Verification consumer: only public Base and capture-library operations.
type Mode is Data:
  Pixels{}
  Recover{}
  Events{}

def continued(ok: Bool, next: IO(Unit)) -> IO(Unit):
  match ok:
    case True{}:
      next
    case False{}:
      IO.die(Unit, 1, "Expected one g byte on the verification terminal")

def gate_result(next: IO(Unit), result: Result<&1, &1, U32 & String, String>) -> IO(Unit):
  match result:
    case Done{value}:
      continued(String.eq(value, "g"), next)
    case Fail{(code, message)}:
      IO.die(Unit, code, message)

def gate_read(next: IO(Unit), pair: File & Result<&1, &1, U32 & String, String>) -> IO(Unit):
  (file, result) = pair
  IO.bind(Unit, Unit, File.close(file), u => gate_result(next, result))

def gate(next: IO(Unit)) -> IO(Unit):
  do IO<Unit>:
    file : File <- IO.try(File, File.open("/dev/stdin", "r"))
    pair : File & Result<&1, &1, U32 & String, String> <- File.read(file, 1)
    gate_read(next, pair)

def show_pixels(xs: List<U32>) -> String:
  match xs:
    case Nil{}:
      ""
    case Con{value, rest}:
      U32.show(value) ++ " " ++ show_pixels(rest)

def array_report(width: U32, height: U32, sized: Array<U32> & U32) -> IO(Unit):
  (pixels, capacity) = sized
  IO.print("PIXELS " ++ U32.show(width) ++ " " ++ U32.show(height)
    ++ " " ++ U32.show(capacity) ++ " " ++ show_pixels(Array.to_list(~U32, pixels)))

def pixel_report(result: Result<&1, &1, U32 & String, C.Capture>) -> IO(Unit):
  match result:
    case Done{C.Capture{width, height, pixels}}:
      array_report(width, height, Array.size(U32, pixels))
    case Fail{(code, message)}:
      IO.die(Unit, code, message)

def close(window: Window) -> IO(Unit):
  IO.bind(Unit, Unit, Window.close(window), u => IO.print("CLOSED"))

def recovered(code: U32, window: Window) -> IO(Unit):
  IO.bind(Unit, Unit, IO.print("RECOVERED " ++ U32.show(code)), u => gate(close(window)))

def recover_result(window: Window, result: Result<&1, &1, U32 & String, C.Capture>) -> IO(Unit):
  match result:
    case Fail{(code, message)}:
      IO.bind(Window, Unit, Window.set_title(window, "BWC recovered"), recovered(code))
    case Done{capture}:
      IO.bind(Unit, Unit, close(window), u => IO.die(Unit, 1, "Expected an unsuitable-window failure"))

def has_close(events: List<Event>) -> Bool:
  match events:
    case Nil{}:
      False{}
    case Con{Close{}, rest}:
      True{}
    case Con{other, rest}:
      has_close(rest)

def close_word(found: Bool) -> String:
  match found:
    case True{}:
      "true"
    case False{}:
      "false"

def event_report(found: Bool, result: Result<&1, &1, U32 & String, C.Capture>) -> IO(Unit):
  match result:
    case Done{capture}:
      IO.print("CAPTURE_DONE CLOSE_EVENT " ++ close_word(found))
    case Fail{(code, message)}:
      IO.die(Unit, code, message)

def event_frame(result: Result<&1, &1, U32 & String, C.Capture>, frame: Window & Image & List<Event>) -> IO(Unit):
  (window, image, events) = frame
  IO.bind(Unit, Unit, close(window), u => event_report(has_close(events), result))

def captured(mode: Mode, pair: Window & Result<&1, &1, U32 & String, C.Capture>) -> IO(Unit):
  match mode:
    case Pixels{}:
      (window, result) = pair
      IO.bind(Unit, Unit, IO.print("CAPTURED"), u =>
        gate(IO.bind(Unit, Unit, close(window), v => pixel_report(result))))
    case Recover{}:
      (window, result) = pair
      recover_result(window, result)
    case Events{}:
      (window, result) = pair
      IO.bind(Window & Image & List<Event>, Unit,
        Window.frame(window, Pix{1193046}), event_frame(result))

def capture(mode: Mode, window: Window) -> IO(Unit):
  IO.bind(Window & Result<&1, &1, U32 & String, C.Capture>, Unit,
    C.Window.capture(window), captured(mode))

def redrawn(frame: Window & Image & List<Event>) -> IO(Unit):
  (window, image, events) = frame
  capture(Pixels{}, window)

def begin(mode: Mode, window: Window) -> IO(Unit):
  match mode:
    case Pixels{}:
      IO.bind(Window & Image & List<Event>, Unit,
        Window.frame(window, Pix{1193046}), redrawn)
    case Recover{}:
      capture(Recover{}, window)
    case Events{}:
      capture(Events{}, window)

def framed(mode: Mode, frame: Window & Image & List<Event>) -> IO(Unit):
  (window, image, events) = frame
  IO.bind(Unit, Unit, IO.print("READY"), u => gate(begin(mode, window)))

def opened(mode: Mode, result: Result<&1, &1, U32 & String, Window>) -> IO(Unit):
  match result:
    case Fail{(code, message)}:
      IO.die(Unit, code, message)
    case Done{window}:
      IO.bind(Window & Image & List<Event>, Unit,
        Window.frame(window, Pix{1193046}), framed(mode))

def run(mode: Mode) -> IO(Unit):
  IO.bind(Result<&1, &1, U32 & String, Window>, Unit,
    Window.open("BWC live probe", 64, 64), opened(mode))
