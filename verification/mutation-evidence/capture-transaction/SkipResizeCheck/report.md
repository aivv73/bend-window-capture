# CaptureTransaction

TLC reached 50 states and 92 steps. The chart draws 12 states and 18 arrows.
The chart does not draw 37 steps that stay in one chart state.

## OnlyValidatedCaptureSucceeds breaks
The shortest path has 6 steps:
0. Capture requested
1. native backend available: Finishing drawing
2. drawing is synchronized: Checking the window
3. window passes initial checks: Reading pixels
4. pixels are available: Checking for changes
5. client changes during readback: Changed snapshot accepted
6. return snapshot and window: Invalid snapshot returned

## Rules that hold
NoDeadlock
