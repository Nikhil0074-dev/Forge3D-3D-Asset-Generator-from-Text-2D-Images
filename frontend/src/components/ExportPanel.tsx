import { useState } from "react";
import type { ExportFormat } from "../types";

const INFO: Record<ExportFormat, string> = { glb: "Single binary file — best for web, Unity, Godot", gltf: "JSON glTF with embedded buffer", obj: "ZIP with .obj + .mtl (colours only; no PBR)" };

export default function ExportPanel({ onExport }: { onExport: (f: ExportFormat) => Promise<void> }) {
  const [busy, setBusy] = useState<ExportFormat | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const go = async (f: ExportFormat) => { setBusy(f); setErr(null); try { await onExport(f); } catch (e) { setErr((e as Error).message); } finally { setBusy(null); } };
  return (
    <div className="stack">
      <div className="row gap">{(Object.keys(INFO) as ExportFormat[]).map((f) => <button key={f} className="ghost" title={INFO[f]} disabled={busy !== null} onClick={() => go(f)}>{busy === f ? "…" : `Download .${f}`}</button>)}</div>
      {err && <p role="alert" className="error">{err}</p>}
    </div>
  );
}
