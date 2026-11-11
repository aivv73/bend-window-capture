export const title = "Clean up temporary files after every ordinary check exit";
const labels = {
  "Proof": "Checking the Bend proof",
  "Create": "Creating a build directory",
  "Arm": "Build directory exists",
  "Compile": "Cleanup armed",
  "Run": "Example compiled",
  "Compare": "Example executed",
  "Exiting": "Script exiting",
  "Exited": "Build directory removed"
};
const steps = {
  "ProofPasses": "proof passes",
  "ProofFails": "proof fails",
  "Create": "create temporary directory",
  "CreateFails": "directory allocation fails",
  "Arm": "register exit cleanup",
  "Compile": "compile example",
  "Run": "execute example",
  "Fail": "a check fails",
  "Pass": "output matches",
  "Exit": "run exit cleanup",
  "Finished": "finished"
};
export function state(v) {
  
  if (v.phase === "Exited" && v.directory) return "Build directory leaked";
  if (v.phase === "Compile" && !v.armed) return "Cleanup missing";
  return labels[v.phase];
}
export function step(action, from, to) {
  if (action === "Arm" && !to.armed) return "continue without exit cleanup";
  if (action === "Exit" && to.directory) return "exit with the directory still present";
  return steps[action] ?? action;
}
export function group(v) {
  if (v.phase === "Exited") return v.status === "Pass" ? "finished" : "failed";
  return "in progress";
}
export const colors = { finished: "teal", "in progress": "blue", failed: "orange" };
