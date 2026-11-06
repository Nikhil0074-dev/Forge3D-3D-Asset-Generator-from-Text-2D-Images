import { useState } from "react";
import type { Asset } from "../types";
import { formatBytes } from "../utils/validate";

interface Props { asset: Asset; onOpen: (a: Asset) => void; onRename: (a: Asset, name: string) => void; onDelete: (a: Asset) => void }

export default function AssetCard({ asset, onOpen, onRename, onDelete }: Props) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(asset.name);
  const save = () => { const n = name.trim(); setEditing(false); if (n && n !== asset.name) onRename(asset, n); else setName(asset.name); };
  return (
    <article className="card">
      <button className="thumb" aria-label={`Open ${asset.name}`} onClick={() => onOpen(asset)}><img src={asset.thumbnail} alt="" loading="lazy" /></button>
      {editing ? <input autoFocus aria-label="Asset name" value={name} onChange={(e) => setName(e.target.value)} onBlur={save} onKeyDown={(e) => e.key === "Enter" && save()} />
        : <h3 title={asset.name}>{asset.name}</h3>}
      <p className="small muted mono">{asset.generation_type} · {asset.format.toUpperCase()} · {formatBytes(asset.file_size)} · {new Date(asset.created_at * 1000).toLocaleDateString()}</p>
      <div className="row gap small"><button className="link" onClick={() => setEditing(true)}>Rename</button><button className="link danger" onClick={() => onDelete(asset)}>Delete</button></div>
    </article>
  );
}
