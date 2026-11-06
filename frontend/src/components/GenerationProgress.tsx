import type { Job } from "../types";

const STEPS = ["Request accepted", "Geometry & materials", "Validating model", "Ready for preview"];
export function stepIndex(job: Job): number {
  if (job.status === "completed") return 4;
  if (job.message.toLowerCase().includes("validat")) return 2;
  if (job.status === "processing") return 1;
  return 0;
}

export default function GenerationProgress({ job, onCancel }: { job: Job; onCancel?: () => void }) {
  const active = stepIndex(job);
  const failed = job.status === "failed" || job.status === "cancelled";
  const determinate = job.progress !== null && job.progress >= 0;
  return (
    <div className="progress" role="status" aria-live="polite">
      <div className="row between"><strong>{failed ? (job.status === "cancelled" ? "Cancelled" : "Generation failed") : active === 4 ? "Done" : "Generating your 3D model…"}</strong>
        {!failed && active < 4 && onCancel && <button className="link" onClick={onCancel}>Cancel</button>}</div>
      {failed ? <p className="error">{job.error || job.message}</p> : (
        <>
          <div className={`bar ${determinate ? "" : "indeterminate"}`} role="progressbar" aria-valuenow={determinate ? job.progress! : undefined}><i style={determinate ? { width: `${job.progress}%` } : undefined} /></div>
          <ol className="steps">{STEPS.map((s, i) => <li key={s} className={i < active ? "done" : i === active ? "now" : ""}>{i < active ? "✓" : "•"} {s}</li>)}</ol>
        </>)}
    </div>
  );
}
