import type { Asset, ExportFormat, Job } from "../types";

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let msg = `Request failed (${r.status})`;
    try {
      const b = await r.json();
      msg = typeof b.detail === "string" ? b.detail : Array.isArray(b.detail) ? b.detail.map((d: any) => d.msg).join("; ") : msg;
    } catch { /* keep default */ }
    throw new Error(msg);
  }
  return r.status === 204 ? (undefined as T) : r.json();
}
const post = (u: string, body?: unknown) =>
  fetch(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  generateText: (prompt: string, style: string, quality: string) =>
    post("/api/generation/text", { prompt, style, quality, output_format: "glb" }).then(j<{ job_id: string }>),
  generateImage: (file: File, prompt: string, style: string) => {
    const f = new FormData(); f.append("file", file); f.append("prompt", prompt); f.append("style", style);
    return fetch("/api/generation/image", { method: "POST", body: f }).then(j<{ job_id: string }>);
  },
  job: (id: string) => fetch(`/api/generation/${id}`).then(j<Job>),
  cancel: (id: string) => post(`/api/generation/${id}/cancel`).then(j<unknown>),
  assets: (search = "", type = "") => fetch(`/api/assets?search=${encodeURIComponent(search)}&type=${type}`).then(j<Asset[]>),
  asset: (id: string) => fetch(`/api/assets/${id}`).then(j<Asset>),
  rename: (id: string, name: string) =>
    fetch(`/api/assets/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) }).then(j<Asset>),
  remove: (id: string) => fetch(`/api/assets/${id}`, { method: "DELETE" }).then(j<void>),
  previewUrl: (id: string) => `/api/assets/${id}/preview`,
  exportAsset: async (id: string, format: ExportFormat) => {
    const r = await post(`/api/assets/${id}/export`, { format });
    if (!r.ok) await j(r);
    const cd = r.headers.get("content-disposition") || "";
    return { blob: await r.blob(), filename: /filename="([^"]+)"/.exec(cd)?.[1] ?? `model.${format}` };
  },
};

export async function pollJob(id: string, onUpdate: (j: Job) => void, intervalMs = 700, signal?: AbortSignal): Promise<Job> {
  for (;;) {
    if (signal?.aborted) throw new Error("aborted");
    const job = await api.job(id);
    onUpdate(job);
    if (["completed", "failed", "cancelled"].includes(job.status)) return job;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
