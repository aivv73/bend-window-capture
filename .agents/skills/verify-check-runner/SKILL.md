---
name: verify-check-runner
description: Verify temporary-build cleanup when changing scripts/check.sh exit handling, compilation, execution, or result comparison.
---

Ordinary script exit leaves no temporary build directory. Otherwise failed checks accumulate build artifacts.

From the repository root, run:

```sh
python3 verification/verify.py check-runner
```

This checks the finite TLA+ model and executes the covered source with controlled external effects. Read every TLA+ result with `/statechart`, using `verification/models/CheckRunner.tla`, its adjacent `.cfg`, and `verification/views/CheckRunner.mjs`. Keep statechart work in a new scratch directory outside the repository.

Coverage: `scripts/check.sh`: proof command, `mktemp`, EXIT trap, compilation, execution, and comparison. `.github/workflows/check.yml`: compiler and dependency context, not GitHub service behavior.

Last confirmed source commit: `30d61efc501028fd433087e474272aa62a48ed80`.
File hashes and the coverage record are in [source-map.json](../../../verification/source-map.json). Exact assumptions, tool requirements, atomicity, and source-test boundaries are in [verification scope](../../../verification/SCOPE.md).

Bounds: One proof, directory allocation, trap registration, compile, run, comparison, and ordinary exit. Excludes interruption between mktemp and trap installation and excludes SIGKILL.

To prove the check can fail, run:

```sh
python3 verification/verify.py check-runner --mutations
```

Mutation witnesses: ExitCleansBuild; the broken source removes the EXIT trap and leaves a build directory after compiler failure.
The command mutates actual source in scratch copies, requires the corresponding model invariant to fail, and rechecks the unchanged originals. It never edits production code.

When a check fails, replay the counterexample against the covered source. Fix the model only if its behavior differs from the code. Preserve genuine findings and report them without changing product code unless requested.

When covered files drift, inspect their diff from the recorded commit and review the model and source harness together. If a behavior change is intended, update both before rerunning. Commit reviewed changes to covered source files first; sync refuses source bytes that differ from HEAD. After correspondence review, run the same command with `--sync-reviewed` to advance hashes and this skill's commit line only after checks pass. Do not use that flag solely to silence drift. Use `/maintain-formal-verification-skill` for a later audit.
