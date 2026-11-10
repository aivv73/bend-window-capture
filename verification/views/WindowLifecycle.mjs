export const title = "Capture a window, close it, then read its pixels";
const labels = {
  "Opening": "Opening a window",
  "Drawing": "Window open",
  "Capturing": "Image drawn",
  "OpenFailed": "Window could not open",
  "Printed": "Pixels printed",
  "CaptureFailed": "Error reported"
};
const steps = {
  "Open": "window opens",
  "OpenFails": "opening fails",
  "Draw": "draw the image",
  "Capture": "capture returns",
  "Close": "close the returned window",
  "Report": "report the outcome",
  "Finished": "finished"
};
export function state(v) {
  if (v.phase === "Returned") return v.outcome === "Done" ? "Snapshot ready" : "Capture failed";
  if (v.phase === "Reporting" && !v.closed) return "Reporting while the window remains open";
  if (v.phase === "Reporting") return v.outcome === "Done" ? "Window closed, snapshot ready" : "Window closed, capture failed";
  if (["Printed", "CaptureFailed"].includes(v.phase) && !v.closed) return "Reported without closing the window";
  return labels[v.phase];
}
export function step(action, from, to) {
  if (action === "Close" && !to.closed) return "continue without closing the window";
  if (action === "Capture") return to.outcome === "Done" ? "capture succeeds" : "capture fails";
  if (action === "Report") return to.outcome === "Done" ? "print captured pixels" : "report the capture error";
  return steps[action] ?? action;
}
export function group(v) {
  if (["OpenFailed", "CaptureFailed"].includes(v.phase)) return "failed";
  return v.phase === "Printed" ? "finished" : "in progress";
}
export const colors = { finished: "teal", "in progress": "blue", failed: "orange" };
