import hashlib
import importlib.util
import io
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "verification"))
import toolchain
import verify

spec = importlib.util.spec_from_file_location("capture_control", ROOT / ".agents/skills/verify-bend-window-capture/scripts/control.py")
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class DownloadTests(unittest.TestCase):
    def test_interrupted_cache_write_never_publishes_partial_jar(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            jar = cache / "tla2tools-1.7.4.jar"
            data = b"complete verified jar"
            response = io.BytesIO(data)
            write = Path.write_bytes

            def interrupted(path, content):
                write(path, content[:3])
                raise InterruptedError("interrupted cache write")

            with mock.patch.object(toolchain, "CACHE", cache), \
                 mock.patch.object(toolchain, "TLC_SHA256", hashlib.sha256(data).hexdigest()), \
                 mock.patch.dict(os.environ, {"JAVA": sys.executable, "TLA2TOOLS": str(jar)}), \
                 mock.patch.object(toolchain.urllib.request, "urlopen", return_value=response), \
                 mock.patch.object(Path, "write_bytes", interrupted):
                with self.assertRaises(InterruptedError):
                    toolchain.resolve()
            self.assertFalse(jar.exists(), "an interrupted download left a partial final jar")
            self.assertTrue(response.closed)
            self.assertEqual(list(cache.iterdir()), [])

    def test_concurrent_downloads_publish_a_complete_verified_jar(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            jar = cache / "tla2tools-1.7.4.jar"
            data = b"complete verified jar"
            barrier = threading.Barrier(2)
            write = Path.write_bytes

            def concurrent_write(path, content):
                barrier.wait(timeout=5)
                return write(path, content)

            with mock.patch.object(toolchain, "CACHE", cache), \
                 mock.patch.object(toolchain, "TLC_SHA256", hashlib.sha256(data).hexdigest()), \
                 mock.patch.dict(os.environ, {"JAVA": sys.executable, "TLA2TOOLS": str(jar)}), \
                 mock.patch.object(toolchain.urllib.request, "urlopen", side_effect=lambda *a, **k: io.BytesIO(data)), \
                 mock.patch.object(Path, "write_bytes", concurrent_write), \
                 ThreadPoolExecutor(max_workers=2) as workers:
                results = list(workers.map(lambda _: toolchain.resolve(), range(2)))
            self.assertEqual([result[1] for result in results], [jar, jar])
            self.assertEqual(jar.read_bytes(), data)
            self.assertEqual(list(cache.iterdir()), [jar])


class XvfbDownloadTests(unittest.TestCase):
    def provision(self, cache, data, response):
        metadata = f"xorg-server-xvfb 1 {hashlib.sha256(data).hexdigest()} https://example.invalid/xvfb.pkg.tar.zst\n"

        def extract(*args, **kwargs):
            binary = cache / "usr/bin/Xvfb"
            binary.parent.mkdir(parents=True, exist_ok=True)
            binary.write_text("#!/bin/sh\nexit 0\n")
            binary.chmod(0o755)

        with mock.patch.object(control, "CACHE", cache), \
             mock.patch.object(control.platform, "machine", return_value="x86_64"), \
             mock.patch.object(control.shutil, "which", side_effect=lambda name: "/usr/bin/pacman" if name == "pacman" else None), \
             mock.patch.object(control.subprocess, "check_output", return_value=metadata), \
             mock.patch.object(control.subprocess, "run", side_effect=extract) as extraction, \
             mock.patch.object(control.urllib.request, "urlopen", return_value=response), \
             mock.patch.dict(os.environ, {"XVFB_BIN": str(cache / "usr/bin/Xvfb")}):
            control.setup_xvfb()
        return extraction

    def test_corrupt_archive_is_replaced_without_manual_cache_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            archive = cache / "xvfb.pkg.tar.zst"
            archive.write_bytes(b"truncated")
            response = io.BytesIO(b"verified archive")
            self.provision(cache, b"verified archive", response)
            self.assertEqual(archive.read_bytes(), b"verified archive")
            self.assertTrue(response.closed)

    def test_invalid_download_is_not_published_or_extracted(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "SHA-256"):
                self.provision(cache, b"verified archive", io.BytesIO(b"wrong archive"))
            self.assertEqual(list(cache.iterdir()), [])

    def test_interruption_does_not_publish_a_partial_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            write = Path.write_bytes

            def interrupted(path, data):
                write(path, data[:3])
                raise InterruptedError("interrupted archive write")

            with mock.patch.object(Path, "write_bytes", interrupted):
                with self.assertRaises(InterruptedError):
                    self.provision(cache, b"verified archive", io.BytesIO(b"verified archive"))
            self.assertEqual(list(cache.iterdir()), [])


class DisplayAllocationTests(unittest.TestCase):
    def test_concurrent_runs_get_different_authenticated_displays(self):
        if not sys.platform.startswith("linux") or not shutil.which("clang") or not shutil.which("xauth"):
            self.skipTest("requires Linux, Clang, xauth, and Xvfb")
        try:
            server = control.xvfb_path()
        except RuntimeError as error:
            self.skipTest(str(error))
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            inspector = base / "x11"
            subprocess.run(["clang", str(control.SKILL / "scripts/x11.c"), "-o", str(inspector), "-lX11"], check=True)
            runs = []
            for index in range(2):
                evidence = base / str(index)
                evidence.mkdir()
                scratch = base / f"bwc-live-{index}"
                (scratch / "bin").mkdir(parents=True)
                (scratch / ".owner").write_text(str(index))
                shutil.copy2(inspector, scratch / "bin/x11")
                control.save(evidence / "session.json", {"scratch": str(scratch), "owner": str(index)})
                control.save(evidence / "build.json", {"xvfb": server})
                runs.append(control.Run(evidence))
            start = threading.Barrier(2)
            active = threading.Barrier(2)
            local = threading.local()
            execute = subprocess.run

            def synchronized_auth(args, **kwargs):
                if args[0] == "xauth" and not getattr(local, "started", False):
                    local.started = True
                    start.wait(timeout=5)
                return execute(args, **kwargs)

            def open_display(run):
                with control.display(run, run.directory) as env:
                    active.wait(timeout=5)
                    return env["DISPLAY"]

            try:
                with mock.patch.object(control.subprocess, "run", side_effect=synchronized_auth) as commands, \
                     ThreadPoolExecutor(max_workers=2) as workers:
                    displays = list(workers.map(open_display, runs))
                self.assertEqual(len(set(displays)), 2)
                auth_calls = [call for call in commands.call_args_list if call.args[0][0] == "xauth"]
                self.assertEqual(len(auth_calls), 4)
                for call in auth_calls:
                    self.assertEqual(len(call.args[0]), 3, "X11 cookies must stay out of process arguments")
                    self.assertIn("input", call.kwargs)
            finally:
                for run in runs:
                    control.cleanup(run.directory)


class ShutdownTests(unittest.TestCase):
    def test_slow_termination_gets_time_to_remove_its_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "graceful.txt"
            script = """
import pathlib, signal, sys, time
def finish(*args):
    time.sleep(.2)
    pathlib.Path(sys.argv[1]).write_text('released')
    sys.exit(0)
signal.signal(signal.SIGTERM, finish)
print('READY', flush=True)
time.sleep(30)
"""
            child = subprocess.Popen([sys.executable, "-c", script, str(marker)],
                start_new_session=True, stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(child.stdout.readline().strip(), "READY")
                control.stop({"pid": child.pid, "start": control.token(child.pid)})
                self.assertEqual(child.wait(timeout=5), 0)
                self.assertEqual(marker.read_text(), "released")
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, 9)
                    child.wait(timeout=5)
                child.stdout.close()

    def test_group_cleanup_includes_a_stubborn_descendant_after_leader_exit(self):
        script = """
import signal, subprocess, sys, time
signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
child = subprocess.Popen([sys.executable, '-c',
    "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print('READY',flush=True); time.sleep(30)"],
    stdout=subprocess.PIPE, text=True)
child.stdout.readline()
print(child.pid, flush=True)
time.sleep(30)
"""
        leader = subprocess.Popen([sys.executable, "-c", script], start_new_session=True,
            stdout=subprocess.PIPE, text=True)
        try:
            descendant = int(leader.stdout.readline().strip())
            control.stop({"pid": leader.pid, "start": control.token(leader.pid)})
            leader.wait(timeout=5)
            # A killed orphan can remain a zombie until its new parent reaps it.
            for _ in range(100):
                if not control.group_running(leader.pid):
                    break
                threading.Event().wait(.01)
            self.assertFalse(control.group_running(leader.pid), f"descendant {descendant} remained running")
        finally:
            try:
                os.killpg(leader.pid, 9)
            except ProcessLookupError:
                pass
            leader.wait(timeout=5)
            leader.stdout.close()


class EvidenceTests(unittest.TestCase):
    def run_fixture(self, base, nested=False):
        evidence = base / "evidence"
        evidence.mkdir()
        scratch = (evidence if nested else base) / "bwc-live-scratch"
        scratch.mkdir()
        (scratch / ".owner").write_text("test-owner")
        (scratch / "temporary.txt").write_text("scratch")
        control.save(evidence / "session.json", {"scratch": str(scratch), "owner": "test-owner"})
        (evidence / "stdout.txt").write_text("original proof")
        return evidence, scratch

    def test_cleanup_detects_modified_or_deleted_evidence(self):
        for mutation in ("modify", "delete"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                evidence, scratch = self.run_fixture(Path(directory))
                remove = shutil.rmtree

                def damaged_cleanup(path):
                    remove(path)
                    artifact = evidence / "stdout.txt"
                    if mutation == "modify":
                        artifact.write_text("changed during cleanup")
                    else:
                        artifact.unlink()

                with mock.patch.object(control.shutil, "rmtree", damaged_cleanup):
                    with self.assertRaisesRegex(RuntimeError, "Evidence changed during cleanup"):
                        control.cleanup(evidence)
                self.assertFalse(json.loads((evidence / "cleanup.json").read_text())["evidence_preserved"])

    def test_nested_scratch_is_not_retained_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence, scratch = self.run_fixture(Path(directory), nested=True)
            control.cleanup(evidence)
            report = json.loads((evidence / "cleanup.json").read_text())
            self.assertFalse(scratch.exists())
            self.assertTrue(report["evidence_preserved"])
            self.assertFalse(any(name.startswith("bwc-live-scratch/") for name in report["evidence_files"]))
            control.cleanup(evidence)
            self.assertEqual(report, json.loads((evidence / "cleanup.json").read_text()))

    def test_final_output_from_shutdown_is_included_in_the_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence, scratch = self.run_fixture(Path(directory))
            script = """
import pathlib, signal, sys, time
def finish(*args):
    pathlib.Path(sys.argv[1]).write_text('final output')
    sys.exit(0)
signal.signal(signal.SIGTERM, finish)
print('READY', flush=True)
time.sleep(30)
"""
            child = subprocess.Popen([sys.executable, "-c", script, str(evidence / "stdout.txt")],
                start_new_session=True, stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(child.stdout.readline().strip(), "READY")
                control.save(scratch / "processes.json", [{"pid": child.pid, "start": control.token(child.pid)}])
                control.cleanup(evidence)
                child.wait(timeout=5)
                report = json.loads((evidence / "cleanup.json").read_text())
                self.assertTrue(report["evidence_preserved"])
                self.assertEqual((evidence / "stdout.txt").read_text(), "final output")
                self.assertEqual(report["evidence_files"]["stdout.txt"], control.sha(evidence / "stdout.txt"))
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, 9)
                    child.wait(timeout=5)
                child.stdout.close()


class SyncTests(unittest.TestCase):
    def git(self, root, *args):
        return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)

    def fixture(self, root):
        self.git(root, "init", "-q")
        (root / "tracked.txt").write_text("A\n")
        self.git(root, "add", "tracked.txt")
        self.commit(root)
        commit = self.git(root, "rev-parse", "HEAD").decode().strip()
        (root / "verification").mkdir()
        skill = root / ".agents/skills/verify-window-lifecycle/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(f"Last confirmed source commit: `{commit}`.")
        control.save(root / "verification/source-map.json", {"window-lifecycle": {
            "sync_commit": commit, "files": {"tracked.txt": verify.digest(root / "tracked.txt")}}})

    def commit(self, root):
        self.git(root, "-c", "user.name=Verification test", "-c", "user.email=test@example.invalid",
                 "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
                 "commit", "-qm", "Source snapshot")

    def sync(self, root):
        with mock.patch.object(verify, "ROOT", root), \
             mock.patch.object(verify, "resolve", return_value=("java", "jar")), \
             mock.patch.object(verify, "model_check", return_value=1), \
             mock.patch.object(verify.source_checks, "check", return_value=1), \
             mock.patch.object(sys, "argv", ["verify.py", "window-lifecycle", "--sync-reviewed"]):
            verify.main()

    def test_sync_rejects_uncommitted_covered_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "tracked.txt").write_text("B\n")
            before = (root / "verification/source-map.json").read_bytes()
            with self.assertRaisesRegex(SystemExit, "commit.*covered|covered.*commit"):
                self.sync(root)
            self.assertEqual((root / "verification/source-map.json").read_bytes(), before)

    def test_recorded_commit_contains_reviewed_bytes_and_explains_a_revert(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "tracked.txt").write_text("B\n")
            self.git(root, "add", "tracked.txt")
            self.commit(root)
            self.sync(root)
            record = json.loads((root / "verification/source-map.json").read_text())["window-lifecycle"]
            self.assertEqual(self.git(root, "show", f"{record['sync_commit']}:tracked.txt"), b"B\n")
            (root / "tracked.txt").write_text("A\n")
            self.assertTrue(self.git(root, "diff", record["sync_commit"], "--", "tracked.txt"))


if __name__ == "__main__":
    unittest.main()
