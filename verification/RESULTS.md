# Formal verification results

All six current-code models pass. Twelve real-source mutations are caught: nine paired with TLA+ invariant violations and three source-only oracle checks. The original sources and models pass again after the mutations.

The two main user flows are available in the [interactive flow diagrams](flows.html): capture and close, and capture decisions. Each chart includes its Mermaid text. The page also contains the implementation protocols and deliberately broken models.

## Rerun the checks

From the repository root:

```sh
python3 verification/verify.py all --mutations
bend PROOF.bend
```

The first command checks pinned TLC 1.7.4 models, runs actual source with controlled external effects, and verifies the negative controls. The second command reports `ALL PROOFS CHECK` for the existing structural ownership proof.

Read [the scope and prerequisites](SCOPE.md) before interpreting a pass. Invoke `/statechart` on a model in `verification/models` with its adjacent configuration and matching view in `verification/views`. Work in a fresh scratch directory outside the repository. The resulting shortest paths are preserved below. Run `node verification/render.mjs` to render the checked Mermaid files with `pele@1.9.0`; the script gives the exact cache-install command when the renderer is absent.

## Subsystem skills

Each skill includes its covered functions, assumptions, mutation command, and last confirmed source commit. State counts apply to separate models and must not be added into a system-wide coverage claim. Source cases overlap between skills.

| Skill | Model states | Source cases | Mutations caught | Evidence |
| --- | ---: | ---: | ---: | --- |
| [window-lifecycle](../.agents/skills/verify-window-lifecycle/SKILL.md) | 10 | 3 | 1 | [chart](charts/window-lifecycle/chart.svg), [Mermaid](charts/window-lifecycle/chart.mmd), [checker report](charts/window-lifecycle/report.md) |
| [capture-transaction](../.agents/skills/verify-capture-transaction/SKILL.md) | 49 | 25 | 1 | [chart](charts/capture-transaction/chart.svg), [Mermaid](charts/capture-transaction/chart.mmd), [checker report](charts/capture-transaction/report.md) |
| [x11-error-trap](../.agents/skills/verify-x11-error-trap/SKILL.md) | 54 | 25 | 3 | [chart](charts/x11-error-trap/chart.svg), [Mermaid](charts/x11-error-trap/chart.mmd), [checker report](charts/x11-error-trap/report.md) |
| [pixel-ownership](../.agents/skills/verify-pixel-ownership/SKILL.md) | 59 | 30 | 4 | [chart](charts/pixel-ownership/chart.svg), [Mermaid](charts/pixel-ownership/chart.mmd), [checker report](charts/pixel-ownership/report.md) |
| [effect-registration](../.agents/skills/verify-effect-registration/SKILL.md) | 9 | 5 | 2 | [chart](charts/effect-registration/chart.svg), [Mermaid](charts/effect-registration/chart.mmd), [checker report](charts/effect-registration/report.md) |
| [check-runner](../.agents/skills/verify-check-runner/SKILL.md) | 12 | 5 | 1 | [chart](charts/check-runner/chart.svg), [Mermaid](charts/check-runner/chart.mmd), [checker report](charts/check-runner/report.md) |

## Negative-control counterexamples

These paths describe deliberately broken scratch copies. They are not findings against the current application. Step numbers refer to the linked statechart reports.

| Rule | Broken source and shortest path | Source replay |
| --- | --- | --- |
| [ReportAfterClose](mutation-evidence/window-lifecycle/SkipClose/report.md) | Remove close. Steps 0–4: open → draw → capture succeeds → continue without closing. | The compiled example reaches reporting with an open window. |
| [OnlyValidatedCaptureSucceeds](mutation-evidence/capture-transaction/SkipResizeCheck/report.md) | Remove the width-change guard. Steps 0–6: synchronize → validate → read pixels → client changes → return an invalid snapshot. | Changed-width readback incorrectly returns Done. |
| [RestoredHandler](mutation-evidence/x11-error-trap/SkipRestore/report.md) | Remove handler restoration. Steps 0–5: publish context → install → drain → skip restoration → clear context. | The old handler is still not restored when capture returns. |
| [FirstErrorWins](mutation-evidence/x11-error-trap/OverwriteFirstError/report.md) | Remove the first-error latch. Steps 0–4: install the trap → receive one error → overwrite it with another. | BadWindow replaces an earlier BadValue and changes the returned errno. |
| [PaddingZeroAndOwned](mutation-evidence/pixel-ownership/SkipZero/report.md) | Remove zeroing. Steps 0–10: acquire image → choose capacity 4 for 3 pixels → allocate → skip initialization → copy → release → return stale padding. | A nonzero sentinel remains in array padding. |
| [AllImagesReleased](mutation-evidence/pixel-ownership/SkipRelease/report.md) | Remove failure-path image cleanup. Steps 0–2: acquire image → validation fails without release. | An unsupported mask returns while the temporary image remains owned. |
| [ReadyHasHandler](mutation-evidence/effect-registration/SkipRegistration/report.md) | Remove JavaScript registration. Steps 0–1: module loads without a handler. | Executing the module registers zero capture handlers. The model also reports NoDeadlock at this missing-dispatch state. |
| [UnsupportedReturnsENOTSUP](mutation-evidence/effect-registration/WrongNativeUnsupportedCode/report.md) | Change the native fallback errno to EIO. Steps 0–2: register → call capture → return the wrong error. | The actual C fallback, forced by preprocessing, returns EIO instead of ENOTSUP. |
| [ExitCleansBuild](mutation-evidence/check-runner/SkipTrap/report.md) | Remove the EXIT trap. Steps 0–5: proof passes → create directory → skip cleanup registration → compile fails → exit with the directory present. | The actual shell script leaves its build directory behind. |

Three additional source-only mutations replace the row-major index with `x`, corrupt the red-channel shift, and move the final synchronization before readback. They fail the full image oracle or the request-drain assertion. These checks are not TLA+ arithmetic proofs or X11 server proofs.

[Machine-readable results](results.json) preserve each behavioral witness. The charts omit steps that stay in the same visible state, including terminal self-loops. Each checker report records the omitted-step count.

## Bounds and outstanding coverage

The models cover one attempt. The trap allows at most two callbacks. Pixel capacity covers logical counts 1, 3, 4, and 5, through capacity 8. The source harness also checks the full 64×64 quadrants and a padded 3×2 image.

The models assume serialized effects, valid Bend-owned handles, successful runtime allocation, and ordinary process exit. They do not prove real X11 rendering, continuous geometry stability, unobscured pixels, arbitrary concurrency, all-input C arithmetic, or memory safety. The C fallback is executed on Linux with its preprocessor branch forced; another platform's ABI is not validated.

No current-code invariant violation was found. This formal suite uses controlled X11 boundaries. The separate [live verification skill](../.agents/skills/verify-bend-window-capture/SKILL.md) now verifies successful native capture, resized-client padding, recoverable failure ownership, and queued close-event preservation on private Xvfb servers. Physical desktop and window-manager behavior remain outside that headless run.

Per-subsystem source commits and covered-file fingerprints are in [source-map.json](source-map.json). Use `/maintain-formal-verification-skill` after later changes, and advance the sync commit only after confirming that each model still describes its source.
