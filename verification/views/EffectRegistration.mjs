export const title = "Load the capture module before dispatching its effect";
const labels = {
  "Loading": "Module loading",
  "Ready": "Capture handler registered"
};
const steps = {
  "Register": "initialize the module",
  "Dispatch": "call capture",
  "Finished": "finished"
};
export function state(v) {
  if (v.phase === "Ready" && !v.registered) return "Capture handler missing";
  if (v.phase === "Returned" && v.backend !== "Native" && v.result !== "ENOTSUP") return "Window and unexpected error returned";
  if (v.phase === "Returned") return v.backend === "Native" ? "Native capture dispatched" : "Window and unsupported error returned";
  return labels[v.phase];
}
export function step(action, from, to) {
  if (action === "Register" && !to.registered) return "module loads without registering capture";
  if (action === "Dispatch") return to.backend === "Native" ? "run native capture" : to.result === "ENOTSUP" ? "return ENOTSUP and window" : "return an unexpected error";
  return steps[action] ?? action;
}
export function group(v) {
  return v.phase === "Returned" ? "finished" : "in progress";
}
export const colors = { finished: "teal", "in progress": "blue", failed: "orange" };
