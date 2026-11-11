# WindowLifecycle

TLC reached 10 states and 12 steps. The chart draws 8 states and 8 arrows.
The chart does not draw 3 steps that stay in one chart state.

## ReportAfterClose breaks
The shortest path has 4 steps:
0. Opening a window
1. window opens: Window open
2. draw the image: Image drawn
3. capture succeeds: Snapshot ready
4. continue without closing the window: Reporting while the window remains open

## Rules that hold
NoDeadlock
