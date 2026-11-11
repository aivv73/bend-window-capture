# Implementation plans

## Execution status

| Plan | Outcome | Status |
| --- | --- | --- |
| 001: Gate capture contracts in CI | Existing source/model and live capture contracts run on pushes and pull requests, with cleanup and retained evidence | DONE — local gates and initial hosted CI passed; review follow-up below |
| 002: Report corners from captured dimensions | Example samples actual image corners, including resized single-row and rectangular captures | DONE — regression reproduced; local source, model, tooling, and live gates passed |

The supplied plan is at `/home/aivv/.t3/worktrees/bend-window-capture/t3-469e1841-040a5f7cdf8e8d62/plans/001-gate-capture-contracts-in-ci.md`.
That worktree's planning index is unchanged. This branch had no planning index, so this file records its execution evidence.

## Plan 001 evidence

- Reviewed workflow and documentation commit: `5668443425998fa013ca43b6e5af5e6697d25fed`.
- `bend PROOF.bend`: passed before each commit.
- `python3 -B -m unittest discover -s tests -v`: all 15 tests passed, with no skips.
- Baseline `python3 -B verification/verify.py all --mutations`: all six areas passed; mutation counts were `1, 1, 3, 4, 2, 1`.
- Workflow parsed with PyYAML; all three added Bash run blocks passed `bash -n`. `git diff --check` passed.
- Actual live and cleanup blocks replayed from the workflow: all five drives passed with exit code 0. Evidence: `/tmp/bwc-ci-plan001-ianmhi2z/capture-live`.
- Cleanup removed scratch and preserved all 135 evidence files; `cleanup.json` records `scratch_removed: true` and `evidence_preserved: true`.
- The local check-script drive exercised the native smoke check on a private display because this host lacks `xvfb-run`. The Ubuntu CI command remains `xvfb-run -a ./scripts/check.sh`.
- Expected pre-sync `DRIFT check-runner` rejected the changed workflow. Reviewed sync changed only the `check-runner` record and its skill's source-commit line. `scripts/check.sh` and all five other records are unchanged.
- `python3 -B verification/verify.py check-runner --mutations` passed without sync flags: 12 model states, 5 source cases, 1 mutation caught.
- Actual contracts block replayed from the workflow: six passing areas and twelve mutations caught. JSON evidence: `/tmp/bwc-contracts-plan001-0m0mefj9/capture-contracts.json`.

At implementation handoff, no push or hosted GitHub run had been performed. Local replay alone does not validate GitHub expression evaluation or artifact upload. Evidence paths are local temporary directories and may disappear. Physical displays, window-manager behavior, every error path, and other operating systems' ABIs remain outside this live coverage.

## PR 5 review follow-up

Both initial hosted CI runs passed at `7dce84e011d5d099360ad10842f17dc790a819b5`. The downloaded artifact from run `43070750314` contains six contract areas, twelve caught mutations, five passing live drives, and successful cleanup. Local archive: `/tmp/bwc-hosted-artifact-_ys81au9/capture-verification.zip`.

CodeRabbit correctly observed that verifier failures prevent JSON output. Reviewed workflow commit `44290d14ab8090abfeaafe1109ec3bcab0d24498` adds a retained `capture-contracts.log` with combined stdout/stderr. Bash `pipefail` preserves verifier failure through `tee`; the artifact includes the log alongside success JSON and live evidence.

- Actual contracts block with a deliberately invalid TLC dependency: exit 1, failure traceback retained, no success JSON. Evidence: `/tmp/bwc-contract-failure-nzrnpbb0`.
- Actual contracts block with valid dependencies: all six areas and twelve mutations passed; JSON and log retained. Evidence: `/tmp/bwc-contracts-plan001-takon6yr`.
- All three run blocks pass `bash -n`. Reviewed sync updates only `check-runner`; the ordinary full suite passes without sync flags. The existing live and cleanup blocks are unchanged.

## Plan 002 evidence

The supplied plan is at `/home/aivv/.t3/worktrees/bend-window-capture/t3-469e1841-040a5f7cdf8e8d62/plans/002-report-corners-from-captured-dimensions.md`.
Implementation branch: `advisor/002-report-corners-from-captured-dimensions`, based on completed Plan 001 commit `d1f72d4`.

- Drift review found only the expected Plan 001 index and `check-runner` metadata changes. Both affected source records passed before editing.
- Bend version: `bend 2.0.40`. Read `bend guide`; `bend PROOF.bend` passed before each commit.
- Regression before the example fix: the targeted pixel-ownership source command exited 1 with `AssertionError: small width 3: example corner report expected '3x1 1 3 1 3', actual stdout '3x1 1 0 1 0\n'`. Compilation and ownership checks succeeded.
- Reviewed implementation commit: `863b7594b4eab9238a91421afbbd7551e1813e0c`. Only the three corner expressions and reusable scalar annotations changed in the example. Array forwarding, close order, native code, laws, and models remain unchanged.
- After the fix, `source_checks.check("pixel-ownership")` returned `30`, including all five literal resized-fixture outputs. `source_checks.check("window-lifecycle")` returned `3`.
- Ordinary verification rejected the changed example with `DRIFT pixel-ownership` before sync. Reviewed sync passed with 10 lifecycle states, 3 source cases, and 1 caught mutation; pixel ownership passed with 59 states, 30 cases, and 4 caught mutations. Both records point to the implementation commit. Plan 001's `check-runner` record is unchanged.
- `python3 -B verification/verify.py all --mutations`: all six areas passed without sync flags; all twelve mutations caught, with unchanged model and case counts.
- `python3 -B -m unittest discover -s tests -v`: all 15 tooling regressions passed. `bend PROOF.bend` and `git diff --check` passed.
- Live evidence: `/tmp/bwc-plan002.BWN8hu/run`. Both example entry points and the resized-pixel consumer passed with exit 0. The binary printed `64x64 16711680 65280 255 16777215`; the check entry printed its existing PASS line. The pixel consumer printed `PIXELS 3 2 8 1193046 1193046 1193046 1193046 1193046 1193046 0 0` after close.
- Cleanup removed scratch and preserved all 84 evidence files. `cleanup.json` records `scratch_removed: true` and `evidence_preserved: true`.
- Statechart review: `/tmp/bwc-plan002-models-noml5y7k/WindowLifecycle` and `/tmp/bwc-plan002-models-noml5y7k/PixelOwnership`. All invariants and deadlock checks hold. Charts omit steps that stay within one displayed state; the bounded models do not prove native RGB arithmetic for every input.

No push, PR, or hosted CI run was performed for Plan 002. The live check-script entry exercised the native smoke check on a private display because this host lacks `xvfb-run`. Temporary evidence directories may disappear.
