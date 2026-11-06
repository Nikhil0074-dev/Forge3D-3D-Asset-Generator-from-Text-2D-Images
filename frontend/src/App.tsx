import { useCallback, useEffect, useRef, useState } from "react";
import ExportPanel from "./components/ExportPanel";
import GenerationProgress from "./components/GenerationProgress";
import ImageUploader from "./components/ImageUploader";
import ModelStatistics from "./components/ModelStatistics";
import ModelViewer from "./components/ModelViewer";
import PromptInput from "./components/PromptInput";
import AssetCard from "./components/AssetCard";
import { api, pollJob } from "./services/api";
import type { Asset, ExportFormat, Job } from "./types";

type Page = "generate" | "library";

export default function App() {
  const [page, setPage] = useState<Page>("generate");
  const [mode, setMode] = useState<"text" | "image">("text");
  const [job, setJob] = useState<Job | null>(null);
  const [asset, setAsset] = useState<Asset | null>(null);
  const [error, setError] = useState<string | null>(null);
  const busy = !!job && !["completed", "failed", "cancelled"].includes(job.status);
  const abort = useRef<AbortController | null>(null);
  useEffect(() => () => abort.current?.abort(), []);

  const run = useCallback(async (start: () => Promise<{ job_id: string }>) => {
    setError(null); setAsset(null);
    abort.current?.abort(); abort.current = new AbortController();
    try {
      const { job_id } = await start();
      setJob({ job_id, status: "queued", progress: 0, message: "Request accepted", error: null, asset_id: null, generation_type: "" });
      const final = await pollJob(job_id, setJob, 600, abort.current.signal);
      if (final.status === "completed" && final.asset_id) setAsset(await api.asset(final.asset_id));
    } catch (e) { if ((e as Error).message !== "aborted") { setError((e as Error).message); setJob(null); } }
  }, []);

  const exportAsset = async (f: ExportFormat) => {
    if (!asset) return;
    const { blob, filename } = await api.exportAsset(asset.asset_id, f);
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = filename; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };

  return (
    <div className="app">
      <header>
        <div className="brand"><span className="mark">◆</span> Forge<b>3D</b></div>
        <nav>{(["generate", "library"] as Page[]).map((p) => <button key={p} className={page === p ? "on" : ""} onClick={() => setPage(p)}>{p}</button>)}</nav>
      </header>
      {page === "generate" ? (
        <main className="workspace">
          <section className="panel">
            <div className="tabs" role="tablist">{(["text", "image"] as const).map((m) => <button key={m} role="tab" aria-selected={mode === m} className={mode === m ? "on" : ""} onClick={() => setMode(m)}>{m === "text" ? "Text → 3D" : "Image → 3D"}</button>)}</div>
            {mode === "text" ? <PromptInput busy={busy} onSubmit={(p, s, q) => run(() => api.generateText(p, s, q))} />
              : <ImageUploader busy={busy} onSubmit={(f, p, s) => run(() => api.generateImage(f, p, s))} />}
            {error && <p role="alert" className="error">{error}</p>}
            {job && <GenerationProgress job={job} onCancel={() => api.cancel(job.job_id).catch(() => {})} />}
          </section>
          <section className="stage">
            <ModelViewer url={asset ? api.previewUrl(asset.asset_id) : null} />
            {asset && <div className="meta"><div><h2>{asset.name}</h2><p className="muted small">Provider: {asset.provider} · {asset.generation_type}</p></div><ModelStatistics asset={asset} /><ExportPanel onExport={exportAsset} /></div>}
          </section>
        </main>
      ) : <Library onOpen={(a) => { setAsset(a); setPage("generate"); }} />}
    </div>
  );
}

function Library({ onOpen }: { onOpen: (a: Asset) => void }) {
  const [items, setItems] = useState<Asset[] | null>(null);
  const [search, setSearch] = useState("");
  const [type, setType] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const load = useCallback(() => api.assets(search, type).then(setItems).catch((e) => setErr(e.message)), [search, type]);
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);
  return (
    <main className="library">
      <div className="row gap toolbar">
        <input aria-label="Search assets" placeholder="Search assets…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select aria-label="Filter by type" value={type} onChange={(e) => setType(e.target.value)}><option value="">All types</option><option value="text-to-3d">Text → 3D</option><option value="image-to-3d">Image → 3D</option></select>
      </div>
      {err && <p role="alert" className="error">{err}</p>}
      {items && items.length === 0 && <p className="muted">No assets yet. Generate your first model.</p>}
      <div className="gridcards">{items?.map((a) => <AssetCard key={a.asset_id} asset={a} onOpen={onOpen}
        onRename={async (x, n) => { await api.rename(x.asset_id, n); load(); }}
        onDelete={async (x) => { if (confirm(`Delete “${x.name}”?`)) { await api.remove(x.asset_id); load(); } }} />)}</div>
    </main>
  );
}
