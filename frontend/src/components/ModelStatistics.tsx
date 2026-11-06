import type { Asset } from "../types";
import { formatBytes } from "../utils/validate";

export default function ModelStatistics({ asset }: { asset: Asset }) {
  const s = asset.stats;
  const rows: [string, string][] = [["Triangles", s.triangle_count.toLocaleString()], ["Vertices", s.vertex_count.toLocaleString()], ["Meshes", String(s.mesh_count)], ["Materials", String(s.material_count)], ["Textures", String(s.texture_count)], ["Size (w·h·d)", `${s.width.toFixed(2)} · ${s.height.toFixed(2)} · ${s.depth.toFixed(2)}`], ["File", formatBytes(s.file_size)]];
  return <dl className="stats">{rows.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>;
}
