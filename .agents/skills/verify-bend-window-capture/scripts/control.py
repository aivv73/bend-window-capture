#!/usr/bin/env python3
"""Build and drive real bend-window-capture consumers on private X11 servers."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import pty
import secrets
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
import tty
import urllib.request
import uuid
import zlib

SKILL = Path(__file__).resolve().parents[1]
ROOT = SKILL.parents[2]
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "bend-window-capture-live"
EXPECTED = "64x64 16711680 65280 255 16777215"
TITLE = "BWC live probe"
FEATURES = ("example", "pixels", "recoverable-failure", "events")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def token(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
    except FileNotFoundError:
        return None


def stop(record):
    pid = record["pid"]
    current = token(pid)
    require(current is None or current == record["start"], f"PID {pid} was reused; refusing to signal it")
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 2
    while group_running(pid):
        if time.monotonic() >= deadline:
            current = token(pid)
            require(current is None or current == record["start"], f"PID {pid} was reused; refusing to signal it")
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                return
            kill_deadline = time.monotonic() + 1
            while group_running(pid) and time.monotonic() < kill_deadline:
                time.sleep(0.02)
            require(not group_running(pid), f"Owned process group {pid} did not stop")
            return
        time.sleep(0.02)


def group_running(pgid):
    for process in Path("/proc").iterdir():
        if not process.name.isdecimal():
            continue
        try:
            fields = (process / "stat").read_text().rsplit(")", 1)[1].split()
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if int(fields[2]) == pgid and fields[0] not in {"Z", "X"}:
            return True
    return False


class Run:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.state_path = self.directory / "session.json"
        self.state = json.loads(self.state_path.read_text())
        self.scratch = Path(self.state["scratch"])

    def private(self):
        require(self.scratch.name.startswith("bwc-live-"), "Unexpected scratch directory")
        require(self.scratch != self.directory and self.scratch not in self.directory.parents,
                "Cleanup would remove evidence")
        require((self.scratch / ".owner").read_text() == self.state["owner"], "Scratch ownership marker mismatch")

    def processes(self):
        path = self.scratch / "processes.json"
        return json.loads(path.read_text()) if path.exists() else []

    def spawn(self, args, **kwargs):
        self.private()
        process = subprocess.Popen(args, start_new_session=True, **kwargs)
        records = self.processes()
        record = {"pid": process.pid, "start": token(process.pid), "command": [str(arg) for arg in args]}
        records.append(record)
        save(self.scratch / "processes.json", records)
        return process, record

    def command(self, args, folder, name, env=None, cwd=None, timeout=45):
        process, record = self.spawn([str(arg) for arg in args], cwd=cwd or ROOT,
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            out, err = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            stop(record)
            out, err = process.communicate(timeout=5)
            (folder / f"{name}.stdout.txt").write_bytes(out)
            (folder / f"{name}.stderr.txt").write_bytes(err)
            raise RuntimeError(f"Timed out: {args}")
        finally:
            stop(record)
            if process.poll() is None:
                process.wait(timeout=5)
        (folder / f"{name}.stdout.txt").write_bytes(out)
        (folder / f"{name}.stderr.txt").write_bytes(err)
        save(folder / f"{name}.command.json", {"argv": [str(arg) for arg in args],
            "cwd": str(cwd or ROOT), "exit_code": process.returncode})
        require(process.returncode == 0, f"Command failed ({process.returncode}): {args}\n{err.decode(errors='replace')}")
        return out.decode()


def xvfb_path():
    path = os.environ.get("XVFB_BIN") or shutil.which("Xvfb") or str(CACHE / "usr/bin/Xvfb")
    require(Path(path).is_file() and os.access(path, os.X_OK),
        "Install Xvfb, set XVFB_BIN, or run this helper's setup-xvfb command on an Arch-family host")
    return str(Path(path).resolve())


def setup_xvfb():
    require(platform.machine() == "x86_64" and shutil.which("pacman"),
            "Automatic provisioning supports Arch-family x86_64 hosts; install Xvfb using your package manager")
    metadata = subprocess.check_output(["pacman", "-Sp", "--print-format", "%n %v %h %l", "xorg-server-xvfb"], text=True).strip().splitlines()
    package = next(line.split() for line in metadata if line.startswith("xorg-server-xvfb "))
    name, version, expected, url = package
    CACHE.mkdir(parents=True, exist_ok=True)
    archive = CACHE / url.rsplit("/", 1)[1]
    if not archive.exists() or sha(archive) != expected:
        with urllib.request.urlopen(url, timeout=45) as response:
            data = response.read()
        require(hashlib.sha256(data).hexdigest() == expected, "Xvfb package differs from configured repository's SHA-256")
        with tempfile.NamedTemporaryFile(dir=CACHE, prefix=f".{archive.name}.", delete=False) as download:
            partial = Path(download.name)
        try:
            partial.write_bytes(data)
            os.replace(partial, archive)
        finally:
            partial.unlink(missing_ok=True)
    subprocess.run(["tar", "--zstd", "-xf", str(archive), "-C", str(CACHE), "usr/bin/Xvfb"], check=True)
    save(CACHE / "package.json", {"package": name, "version": version, "sha256": expected, "url": url})
    print(xvfb_path())


def covered_files():
    files = [ROOT / name for name in ("capture.bend", "capture.c", "capture.js", "examples/capture.bend",
                                      "LAWS.bend", "PROOF.bend", "scripts/check.sh")]
    return files + sorted((SKILL / "assets").glob("*.bend")) + [SKILL / "scripts/x11.c"]


def launch(directory):
    directory = Path(directory).resolve()
    require(not directory.exists(), "Use a new run directory; existing evidence is never overwritten")
    directory.mkdir(parents=True)
    scratch = Path(tempfile.mkdtemp(prefix="bwc-live-"))
    owner = uuid.uuid4().hex
    (scratch / ".owner").write_text(owner)
    save(directory / "session.json", {"scratch": str(scratch), "owner": owner})
    run = Run(directory)
    try:
        require(sys.platform.startswith("linux"), "Live native capture requires Linux/X11")
        for tool in ("bend", "clang", "xauth"):
            require(shutil.which(tool), f"Missing {tool}")
        server = xvfb_path()
        version = run.command(["bend", "version"], directory, "bend-version").strip()
        require(version == "bend 2.0.40", "Revalidate the runtime bridge before using a different Bend compiler")
        run.command(["bend", "PROOF.bend"], directory, "proof")
        sources = scratch / "sources"
        binaries = scratch / "bin"
        sources.mkdir()
        binaries.mkdir()
        for file in (SKILL / "assets").glob("*.bend"):
            shutil.copy2(file, sources / file.name)
        for name in ("capture.bend", "capture.c", "capture.js"):
            shutil.copy2(ROOT / name, sources / name)
        run.command(["bend", ROOT / "examples/capture.bend", "-o", binaries / "example"], directory, "build-example")
        for name in ("pixels", "recover", "events"):
            run.command(["bend", sources / f"{name}.bend", "-o", binaries / name], directory, f"build-{name}")
        run.command(["clang", "-Wall", "-Wextra", "-O2", SKILL / "scripts/x11.c", "-o", binaries / "x11", "-lX11"], directory, "build-x11")
        save(directory / "build.json", {"bend": version, "xvfb": server, "xvfb_sha256": sha(Path(server)),
            "sources": {str(file.relative_to(ROOT)): sha(file) for file in covered_files()},
            "binaries": {file.name: sha(file) for file in sorted(binaries.iterdir())}})
        print(f"READY {directory}")
    except BaseException:
        cleanup(directory)
        raise


def doctor(run):
    run.private()
    build = json.loads((run.directory / "build.json").read_text())
    require(subprocess.check_output(["bend", "version"], text=True).strip() == build["bend"], "Bend version changed; relaunch")
    for name, digest in build["sources"].items():
        require(sha(ROOT / name) == digest, f"Source changed since launch: {name}; use a new run")
    for name, digest in build["binaries"].items():
        require(sha(run.scratch / "bin" / name) == digest, f"Prepared binary changed: {name}")
    require(sha(Path(build["xvfb"])) == build["xvfb_sha256"], "Xvfb binary changed since launch")
    require(not any(token(record["pid"]) == record["start"] and token(record["pid"]) is not None
                    for record in run.processes()), "An earlier owned process is still live; run cleanup before relaunching")
    result = {"healthy": True, "bend": build["bend"], "build": "source and binary hashes match", "active_instances": 0}
    save(run.directory / f"doctor-{uuid.uuid4().hex[:8]}.json", result)
    return result


@contextmanager
def display(run, evidence):
    session = run.scratch / ("display-" + uuid.uuid4().hex)
    session.mkdir(mode=0o700)
    authority = session / "authority"
    authority.touch(mode=0o600)
    server_authority = session / "server-authority"
    server_authority.touch(mode=0o600)
    server = None
    record = None
    number = None
    env = None
    socket_identity = None
    log = (evidence / "xvfb.log").open("wb")

    def inode(path):
        try:
            return path.stat().st_ino
        except FileNotFoundError:
            return None

    try:
        # The generated cookie stays in the private scratch directory and is never logged.
        cookie = secrets.token_hex(16)
        auth = subprocess.run(["xauth", "-f", str(server_authority)],
            input=f"add :0 MIT-MAGIC-COOKIE-1 {cookie}\n", text=True, capture_output=True)
        require(auth.returncode == 0, "Cannot configure private X11 server authentication")
        build = json.loads((run.directory / "build.json").read_text())
        read_fd, write_fd = os.pipe()
        try:
            args = [build["xvfb"], "-displayfd", str(write_fd), "-screen", "0", "800x600x24", "-nolisten", "tcp",
                    "-auth", str(server_authority), "-noreset"]
            server, record = run.spawn(args, stdout=log, stderr=subprocess.STDOUT, pass_fds=(write_fd,))
            os.close(write_fd)
            write_fd = None
            require(select.select([read_fd], [], [], 5)[0], "Xvfb did not allocate a display in five seconds")
            allocated = os.read(read_fd, 64).decode("ascii").strip()
            require(allocated.isdecimal(), "Xvfb exited without providing a display number; inspect xvfb.log")
            number = int(allocated)
        finally:
            os.close(read_fd)
            if write_fd is not None:
                os.close(write_fd)
        address = f":{number}"
        socket_identity = inode(Path(f"/tmp/.X11-unix/X{number}"))
        auth = subprocess.run(["xauth", "-f", str(authority)],
            input=f"add {address} MIT-MAGIC-COOKIE-1 {cookie}\n", text=True, capture_output=True)
        require(auth.returncode == 0, "Cannot configure private X11 client authentication")
        env = {**os.environ, "DISPLAY": address, "XAUTHORITY": str(authority), "BENDRTS": "--threads 1",
               "TMPDIR": str(session)}
        save(evidence / "display.json", {"argv": args, "pid": server.pid, "display": address,
            "socket_inode": socket_identity,
            "stand_in": "Private 800x600x24 Xvfb server, no window manager, generated authentication"})
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            require(server.poll() is None, "Owned Xvfb exited; inspect xvfb.log")
            probe = subprocess.run([str(run.scratch / "bin/x11"), "doctor"], env=env,
                capture_output=True, text=True, timeout=2)
            if probe.returncode == 0:
                state = json.loads(probe.stdout)
                require(state == {"width": 800, "height": 600, "depth": 24, "true_color": True, "windows": []},
                        "Fresh display is not a usable, empty TrueColor X11 instance")
                save(evidence / "display-doctor.json", state)
                break
            time.sleep(0.03)
        else:
            raise RuntimeError("Owned Xvfb did not become usable in five seconds")
        yield env
    except BaseException:
        if env is not None and server is not None and server.poll() is None:
            probe = subprocess.run([str(run.scratch / "bin/x11"), "doctor"], env=env,
                capture_output=True, text=True, timeout=2)
            save(evidence / "failure-doctor.json", {"exit_code": probe.returncode,
                "stdout": probe.stdout, "stderr": probe.stderr})
        raise
    finally:
        if record:
            stop(record)
        if server:
            server.wait(timeout=5)
        log.close()
        if session.exists():
            shutil.rmtree(session)
        lock = Path(f"/tmp/.X{number}-lock") if number is not None else None
        try:
            owned_lock_remains = lock is not None and lock.read_text().strip() == str(server.pid)
        except FileNotFoundError:
            owned_lock_remains = False
        result = {"server_exited": server is None or server.poll() is not None,
            "private_auth_removed": not session.exists(),
            "socket_removed": socket_identity is None or inode(Path(f"/tmp/.X11-unix/X{number}")) != socket_identity,
            "lock_removed": not owned_lock_remains}
        save(evidence / "display-cleanup.json", result)
        require(all(result.values()), "Private X11 server left a lock, socket, or other owned resource behind")


class Terminal:
    def __init__(self, run, args, env, evidence):
        self.master, slave = pty.openpty()
        tty.setraw(slave)
        self.out = (evidence / "stdout.txt").open("wb")
        self.err = (evidence / "stderr.txt").open("wb")
        self.data = bytearray()
        self.eof = False
        self.process, self.record = run.spawn([str(arg) for arg in args], cwd=ROOT, env=env,
            stdin=slave, stdout=slave, stderr=self.err)
        os.close(slave)
        os.set_blocking(self.master, False)
        save(evidence / "command.json", {"argv": [str(arg) for arg in args], "cwd": str(ROOT),
            "display": env["DISPLAY"], "BENDRTS": env.get("BENDRTS"),
            "terminal": "fresh raw PTY; stderr retained separately"})

    def pump(self):
        if self.eof:
            return
        if select.select([self.master], [], [], 0.05)[0]:
            try:
                data = os.read(self.master, 65536)
            except OSError as error:
                if error.errno != 5:
                    raise
                data = b""
            self.eof = not data
            self.data.extend(data)
            self.out.write(data)
            self.out.flush()

    def ready(self, marker):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            self.pump()
            if marker in self.data.decode(errors="replace").splitlines():
                return
            require(not (self.process.poll() is not None and self.eof), f"Consumer exited before {marker}")
        raise RuntimeError(f"Consumer did not reach {marker}")

    def send(self):
        os.write(self.master, b"g")

    def finish(self):
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            self.pump()
            if self.process.poll() is not None and self.eof:
                return self.process.returncode
        raise RuntimeError("Consumer timed out")

    def close(self):
        stop(self.record)
        self.process.wait(timeout=5)
        for _ in range(4):
            self.pump()
        os.close(self.master)
        self.out.close()
        self.err.close()


def screenshot_png(ppm):
    header, size, maximum, pixels = ppm.read_bytes().split(b"\n", 3)
    width, height = map(int, size.split())
    require(header == b"P6" and maximum == b"255" and len(pixels) == width * height * 3, "Invalid X11 screenshot")
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
    rows = b"".join(b"\0" + pixels[y * width * 3:(y + 1) * width * 3] for y in range(height))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    ppm.with_suffix(".png").write_bytes(png + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))
    return pixels


def drive(run, feature, entry):
    doctor(run)
    evidence = run.directory / (feature + "-" + entry + "-" + uuid.uuid4().hex[:8])
    evidence.mkdir()
    terminal = None
    status = {"feature": feature, "entry": entry, "passed": False}
    actions = []
    def note(action, observed=None):
        actions.append({"action": action, "observed": observed})
        save(evidence / "actions.json", actions)
    note("Prepare a fresh private X11 display")
    try:
        with display(run, evidence) as env:
            def x11(name, *args):
                out = run.command([run.scratch / "bin/x11", *args], evidence, name, env=env)
                value = json.loads(out)
                note("X11 " + " ".join(str(arg) for arg in args), value)
                return value
            if feature == "example":
                args = {"binary": [run.scratch / "bin/example"],
                        "bend": ["bend", ROOT / "examples/capture.bend"],
                        "check": [ROOT / "scripts/check.sh"]}[entry]
                if entry == "binary":
                    env = {key: value for key, value in env.items() if key != "BENDRTS"}
            else:
                require(entry == "binary", "The consumer features have one prepared-binary entry point")
                name = {"pixels": "pixels", "recoverable-failure": "recover", "events": "events"}[feature]
                args = [run.scratch / "bin" / name, "+RTS", "--threads", "1"]
            terminal = Terminal(run, args, env, evidence)
            note("Start the documented example" if feature == "example" else "Start the public-API consumer")
            if feature != "example":
                terminal.ready("READY")
                before = x11("window-before", "find", TITLE)
                require(before["width"] == 64 and before["height"] == 64 and before["map_state"] == 2,
                        "Consumer did not draw a visible 64x64 window")
                x11("screenshot-before", "snapshot", TITLE, evidence / "window-before.ppm")
                screenshot_png(evidence / "window-before.ppm")
                if feature == "pixels":
                    resized = x11("resize", "resize", TITLE, "3", "2")
                    require(resized["width"] == 3 and resized["height"] == 2, "Real window resize did not take effect")
                    x11("screenshot-resized", "snapshot", TITLE, evidence / "window-resized.ppm")
                    screenshot_png(evidence / "window-resized.ppm")
                elif feature == "recoverable-failure":
                    hidden = x11("hide", "hide", TITLE)
                    require(hidden["map_state"] == 0, "Window did not become hidden")
                elif feature == "events":
                    x11("queue-close", "close-event", TITLE)
                terminal.send()
                note("Type g to call Window.capture")
                if feature == "pixels":
                    terminal.ready("CAPTURED")
                    x11("screenshot-captured", "snapshot", TITLE, evidence / "window-captured.ppm")
                    require(screenshot_png(evidence / "window-captured.ppm") == bytes.fromhex("123456") * 6,
                            "Redrawn client does not contain the expected pixels")
                    terminal.send()
                    note("Type g to close the window and read the captured array")
                if feature == "recoverable-failure":
                    terminal.ready("RECOVERED 11")
                    recovered = x11("returned-window", "find", "BWC recovered")
                    require(recovered["map_state"] == 0, "Returned window was not usable after EAGAIN")
                    require(recovered["window"] == before["window"], "Failure returned a different X11 window")
                    terminal.send()
                    note("Type g to close the returned window")
            code = terminal.finish()
            status["exit_code"] = code
            text = terminal.data.decode()
            note("Consumer exits", {"exit_code": code, "stdout": text})
            require(code == 0, f"Consumer exited {code}; inspect stdout.txt and stderr.txt")
            lines = text.splitlines()
            if feature == "example":
                expected = "PASS: dimensions, RGB quadrants, row order, and pixels after close" if entry == "check" else EXPECTED
                require(expected in lines, "Documented example output does not match")
                require(entry != "check" or "ALL PROOFS CHECK" in lines, "Project check did not report the ownership proof")
            elif feature == "pixels":
                expected = "PIXELS 3 2 8 " + " ".join(["1193046"] * 6 + ["0", "0"])
                require([line.strip() for line in lines] == ["READY", "CAPTURED", "CLOSED", expected], "Capture dimensions, padding, pixels, or post-close report differ")
            elif feature == "events":
                require(lines == ["READY", "CLOSED", "CAPTURE_DONE CLOSE_EVENT true"], "Capture discarded the queued close event")
            else:
                require(lines == ["READY", "RECOVERED 11", "CLOSED"], "Failure did not preserve the usable Window owner")
            after = x11("window-after", "doctor")
            require(after["windows"] == [], "Consumer left an X11 window behind")
            terminal.close()
            terminal = None
        status["passed"] = True
    except BaseException as error:
        status["error"] = str(error)
        raise
    finally:
        if terminal:
            terminal.close()
        save(evidence / "result.json", status)
        require((evidence / "actions.json").exists(), "Drive lost its action evidence")
        print(f"{'PASS' if status['passed'] else 'FAIL'} {feature}: {evidence}", flush=True)


def cleanup(directory):
    run = Run(directory)
    if run.scratch.exists():
        run.private()
        for record in reversed(run.processes()):
            # Completed processes may have been reaped and their IDs reused; they no longer belong to us.
            current = token(record["pid"])
            if current == record["start"] and current is not None:
                stop(record)
    # Stop writers before the baseline so their final output remains part of the proof.
    def snapshot():
        return {str(file.relative_to(run.directory)): sha(file)
                for file in run.directory.rglob("*") if file.is_file()
                and file != run.directory / "cleanup.json"
                and file != run.scratch and run.scratch not in file.parents}

    artifacts = snapshot()
    if run.scratch.exists():
        shutil.rmtree(run.scratch)
    retained = snapshot()
    report = {"scratch_removed": not run.scratch.exists(), "evidence_files": artifacts,
              "evidence_preserved": bool(artifacts) and artifacts == retained}
    if artifacts != retained:
        report["evidence_after_cleanup"] = retained
    save(run.directory / "cleanup.json", report)
    require(report["evidence_preserved"], "Evidence changed during cleanup")
    print(f"CLEAN {run.directory}; {len(artifacts)} evidence files retained")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("setup-xvfb")
    for name in ("launch", "doctor", "drive", "cleanup"):
        sub = commands.add_parser(name)
        sub.add_argument("--run-dir", type=Path, required=True)
        if name == "drive":
            sub.add_argument("--feature", choices=FEATURES, required=True)
            sub.add_argument("--entry", choices=("binary", "bend", "check"), default="binary")
    args = parser.parse_args()
    if args.command == "setup-xvfb":
        setup_xvfb()
    elif args.command == "launch":
        launch(args.run_dir)
    elif args.command == "doctor":
        print(json.dumps(doctor(Run(args.run_dir)), indent=2))
    elif args.command == "drive":
        drive(Run(args.run_dir), args.feature, args.entry)
    else:
        cleanup(args.run_dir)


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt("Verification interrupted")
    signal.signal(signal.SIGTERM, interrupted)
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
