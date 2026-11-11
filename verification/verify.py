#!/usr/bin/env python3
"""Check source correspondence, bounded TLA+ models, and executable source witnesses."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

import source_checks
from toolchain import resolve

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "verification/models"
AREAS = {
    "window-lifecycle": ("WindowLifecycle", [
        ("SkipClose", "ReportAfterClose", "window-lifecycle", "report follows Window.close")]),
    "capture-transaction": ("CaptureTransaction", [
        ("SkipResizeCheck", "OnlyValidatedCaptureSucceeds", "capture-transaction", "unsuitable readback returns Fail")]),
    "x11-error-trap": ("X11ErrorTrap", [
        ("SkipRestore", "RestoredHandler", "x11-error-trap", "previous X11 error handler is restored"),
        ("OverwriteFirstError", "FirstErrorWins", "x11-first-error", "error mapping and first-error precedence")]),
    "pixel-ownership": ("PixelOwnership", [
        ("SkipZero", "PaddingZeroAndOwned", "pixel-ownership", "array padding is zero"),
        ("SkipRelease", "AllImagesReleased", "pixel-release", "temporary XImage is released before returning")]),
    "effect-registration": ("EffectRegistration", [
        ("SkipRegistration", "ReadyHasHandler", "effect-registration", "module evaluation registers one capture handler"),
        ("WrongNativeUnsupportedCode", "UnsupportedReturnsENOTSUP", "native-unsupported", "unsupported native backend returns ENOTSUP")]),
    "check-runner": ("CheckRunner", [
        ("SkipTrap", "ExitCleansBuild", "check-runner", "checker leaked its temporary build directory")]),
}
SOURCE_ONLY_MUTATIONS = {
    "x11-error-trap": [
        ("x11-drain-order", "all capture requests are drained before handler restoration"),
    ],
    "pixel-ownership": [
        ("pixel-row-order", "RGB quadrant positions and row order"),
        ("pixel-channel", "RGB quadrant positions and row order"),
    ]
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_check(name, java, jar, mutation=None):
    with tempfile.TemporaryDirectory(prefix="capture-tlc-") as directory:
        work = Path(directory)
        (work / f"{name}.tla").write_text((MODELS / f"{name}.tla").read_text())
        cfg = (MODELS / f"{name}.cfg").read_text()
        if mutation:
            cfg = source_checks.replace_once(cfg, f"{mutation[0]} = FALSE", f"{mutation[0]} = TRUE")
        (work / f"{name}.cfg").write_text(cfg)
        result = subprocess.run([java, "-XX:+UseParallelGC", "-cp", str(jar), "tlc2.TLC",
            "-workers", "1", "-fp", "0", "-lncheck", "final", name], cwd=work,
            text=True, capture_output=True, timeout=90)
        output = result.stdout + result.stderr
        if mutation:
            source_checks.require(result.returncode != 0 and
                f"Invariant {mutation[1]} is violated" in output,
                f"model mutation {mutation[0]} did not violate {mutation[1]}:\n{output}")
        else:
            source_checks.require(result.returncode == 0 and "No error has been found" in output,
                                  f"{name} failed:\n{output}")
        match = re.search(r"([\d,]+) distinct states found", output)
        return int(match[1].replace(",", "")) if match else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("area", choices=["all", *AREAS], default="all", nargs="?")
    parser.add_argument("--mutations", action="store_true", help="prove each rule fails on broken models and actual scratch source")
    parser.add_argument("--sync-reviewed", action="store_true", help="record current covered files after manual correspondence review and passing checks")
    parser.add_argument("--out", type=Path, help="write a JSON result to this new file")
    args = parser.parse_args()
    if args.out and args.out.exists():
        parser.error("--out must be a new file")
    record_path = ROOT / "verification/source-map.json"
    record = json.loads(record_path.read_text())
    java, jar = resolve()
    results = {}
    skill_updates = {}
    selected = AREAS if args.area == "all" else {args.area: AREAS[args.area]}
    reviewed_files = {}
    if args.sync_reviewed:
        sync_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        for area in selected:
            reviewed_files[area] = {path: digest(ROOT / path) for path in record[area]["files"]}
            for path, sha in reviewed_files[area].items():
                committed = subprocess.run(["git", "show", f"{sync_commit}:{path}"], cwd=ROOT, capture_output=True)
                if committed.returncode or hashlib.sha256(committed.stdout).hexdigest() != sha:
                    raise SystemExit(f"Cannot sync {area}: commit the reviewed covered source first ({path} differs from HEAD).")
    for area, (name, mutations) in selected.items():
        coverage = record[area]
        drift = [path for path, sha in coverage["files"].items() if digest(ROOT / path) != sha]
        if drift and not args.sync_reviewed:
            raise SystemExit(f"DRIFT {area}: {', '.join(drift)} changed since {coverage['sync_commit']}. "
                             "Review code, model, and harness before --sync-reviewed; a stale model pass is not verification.")
        states = model_check(name, java, jar)
        cases = source_checks.check(area)
        killed = []
        if args.mutations:
            for constant, invariant, source_mutation, witness in mutations:
                model_check(name, java, jar, (constant, invariant))
                try:
                    source_checks.check(area, mutation=source_mutation)
                except AssertionError as error:
                    source_checks.require(witness in str(error),
                                          f"mutation failed for an unrelated reason: {error}")
                    killed.append({"rule": invariant, "source_mutation": source_mutation,
                                   "source_witness": str(error)})
                else:
                    raise AssertionError(f"source mutation survived: {source_mutation}")
            for source_mutation, witness in SOURCE_ONLY_MUTATIONS.get(area, []):
                try:
                    source_checks.check(area, mutation=source_mutation)
                except AssertionError as error:
                    source_checks.require(witness in str(error),
                                          f"mutation failed for an unrelated reason: {error}")
                    killed.append({"rule": "Source behavioral oracle (not a TLA+ proof)",
                                   "source_mutation": source_mutation, "source_witness": str(error)})
                else:
                    raise AssertionError(f"source mutation survived: {source_mutation}")
            # Fresh scratch copies of the original source must return to passing.
            model_check(name, java, jar)
            source_checks.check(area)
        results[area] = {"model": name, "states": states, "source_cases": cases,
                         "mutations": killed, "sync_commit": coverage["sync_commit"]}
        print(f"PASS {area}: {states} model states, {cases} source cases, {len(killed)} mutations caught", flush=True)
        if args.sync_reviewed:
            old_commit = coverage["sync_commit"]
            coverage["sync_commit"] = sync_commit
            coverage["files"] = reviewed_files[area]
            results[area]["sync_commit"] = coverage["sync_commit"]
            skill = ROOT / f".agents/skills/verify-{area}/SKILL.md"
            skill_updates[skill] = source_checks.replace_once(skill.read_text(),
                f"Last confirmed source commit: `{old_commit}`.",
                f"Last confirmed source commit: `{coverage['sync_commit']}`.")
    if args.sync_reviewed:
        for area, files in reviewed_files.items():
            if any(digest(ROOT / path) != sha for path, sha in files.items()):
                raise SystemExit(f"Covered source changed during verification: {area}; rerun before syncing.")
        for skill, content in skill_updates.items():
            skill.write_text(content)
        record_path.write_text(json.dumps(record, indent=2) + "\n")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
