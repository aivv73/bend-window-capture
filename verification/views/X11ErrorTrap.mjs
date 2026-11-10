export const title = "Install, drain, and restore the capture error handler";
const labels = {
  "Idle": "Previous handler active",
  "Context": "Capture context published",
  "Drained": "Requests drained",
  "Restored": "Previous handler restored",
  "Returned": "Capture context cleared"
};
const steps = {
  "SetContext": "publish capture context",
  "Install": "install capture handler",
  "OwnedError": "capture request fails",
  "UnrelatedError": "forward an unrelated error",
  "Drain": "finish pending requests",
  "Restore": "restore previous handler",
  "ClearContext": "clear capture context",
  "Finished": "finished"
};
export function state(v) {
  const owned = Object.values(v.errors).filter(code => code !== 0);
  if (owned.length && v.first !== owned[0]) return "First capture error overwritten";
  if (!v.context && v.handler === "Capture") return "Handler points at cleared context";
  if (v.phase === "Restored" && v.handler === "Capture") return "Capture handler left installed";
  if (v.phase === "Active") return v.first === 0 ? "Capture handler active" : "First capture error retained";
  return labels[v.phase];
}
export function step(action, from, to) {
  if (action === "Restore" && to.handler === "Capture") return "skip restoring the handler";
  if (action === "OwnedError" && from.first !== 0 && to.first !== from.first) return "another error replaces the first";
  return steps[action] ?? action;
}
export function group(v) {
  return v.phase === "Returned" ? "finished" : "in progress";
}
export const colors = { finished: "teal", "in progress": "blue", failed: "orange" };
