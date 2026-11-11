export const title = "Capture success and failures that return your window";
const labels = {
  "Start": "Capture requested",
  "Synchronize": "Finishing drawing",
  "Eligibility": "Checking the window",
  "ReadPixels": "Reading pixels",
  "Recheck": "Checking for changes"
};
const steps = {
  "Supported": "native backend available",
  "Unsupported": "backend unavailable",
  "Synchronize": "drawing is synchronized",
  "PendingError": "pending X11 request fails",
  "Eligible": "window passes initial checks",
  "Rejected": "window fails initial checks",
  "ReadPixels": "pixels are available",
  "ReadFails": "readback or color format fails",
  "Recheck": "window is checked again",
  "Finalize": "return the capture outcome",
  "ProtocolError": "X11 reports a protocol error",
  "Finished": "finished"
};
export function state(v) {
  if (v.phase === "Finalize" && v.changed && v.failure === "None") return "Changed snapshot accepted";
  if (v.phase === "Finalize") return v.failure === "None" ? "Snapshot validated" : "Capture rejected";
  if (v.phase === "Returned" && v.result === "Done" && v.changed) return "Invalid snapshot returned";
  if (v.phase === "Returned") return v.result === "Done" ? "Snapshot and window returned" : v.result === "EAGAIN" ? "Retryable error and window returned" : "Error and window returned";
  return labels[v.phase];
}
export function step(action, from, to) {
  if (action === "Recheck") return to.changed ? "client changes during readback" : "client still matches";
  if (action === "Finalize" || action === "ProtocolError")
    return to.result === "Done" ? "return snapshot and window" : to.result === "EAGAIN" ? "return EAGAIN and window" : "return error and window";
  return steps[action] ?? action;
}
export function group(v) {
  if (v.phase === "Returned") return v.result === "Done" ? "finished" : "failed";
  return "in progress";
}
export const colors = { finished: "teal", "in progress": "blue", failed: "orange" };
