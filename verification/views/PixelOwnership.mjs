export const title = "Copy pixels into storage that survives window closure";
const labels = {
  "Start": "No image acquired",
  "Image": "Temporary image owned",
  "Buffer": "Pixel array allocated",
  "Copying": "Copying client pixels",
  "Copied": "Temporary image released",
  "Returned": "Independent capture returned",
  "Failed": "Capture failed, image released"
};
const steps = {
  "Acquire": "acquire client image",
  "FailBeforeImage": "acquisition fails",
  "FailAfterImage": "validation fails",
  "Grow": "choose array capacity",
  "Allocate": "allocate pixel array",
  "Zero": "clear pixel storage",
  "Copy": "copy a pixel",
  "ReleaseImage": "release client image",
  "Publish": "return independent capture",
  "Finished": "finished"
};
export function state(v) {
  
  if (v.phase === "Failed" && v.image) return "Capture failed, image leaked";
  if (v.phase === "Returned" && v.capacity > v.count && !v.zeroed) return "Capture returned with stale padding";
  return labels[v.phase];
}
export function step(action, from, to) {
  if (action === "Zero" && !to.zeroed) return "skip clearing pixel storage";
  if (action === "FailAfterImage" && to.image) return "validation fails without image cleanup";
  return steps[action] ?? action;
}
export function group(v) {
  if (v.phase === "Failed") return "failed";
  return v.phase === "Returned" ? "finished" : "in progress";
}
export const colors = { finished: "teal", "in progress": "blue", failed: "orange" };
