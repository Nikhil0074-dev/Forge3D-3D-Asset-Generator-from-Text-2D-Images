import { useEffect, useRef, useState } from "react";
import { validateImage } from "../utils/validate";

interface Props { busy: boolean; onSubmit: (file: File, prompt: string, style: string) => void }

export default function ImageUploader({ busy, onSubmit }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState("");
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);

  const pick = (f?: File) => {
    if (!f) return;
    const e = validateImage(f);
    setError(e);
    if (e) { setFile(null); setUrl(null); return; }
    setFile(f); setUrl(URL.createObjectURL(f));
  };
  return (
    <div className="stack">
      <label className="label">Reference image</label>
      <div className="drop" role="button" tabIndex={0} onClick={() => input.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && input.current?.click()}
        onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); pick(e.dataTransfer.files[0]); }}>
        {url ? <img src={url} alt="Selected reference" /> : <span>Drop a photo or sketch here, or click to browse<br /><small className="muted">PNG · JPG · WebP · up to 8 MB</small></span>}
      </div>
      <input ref={input} data-testid="file-input" type="file" hidden accept="image/png,image/jpeg,image/webp" onChange={(e) => pick(e.target.files?.[0])} />
      {error && <p role="alert" className="error">{error}</p>}
      {file && <div className="row between small"><span className="muted">{file.name}</span><button type="button" className="link" onClick={() => { setFile(null); setUrl(null); if (input.current) input.current.value = ""; }}>Replace</button></div>}
      <label className="label" htmlFor="hint">Optional hint</label>
      <input id="hint" value={hint} placeholder="e.g. wooden chair" onChange={(e) => setHint(e.target.value)} />
      <p className="note small">A single image can’t show hidden surfaces, so the back and underside are estimated and may differ from your reference.</p>
      <button className="primary" disabled={busy || !file} onClick={() => file && onSubmit(file, hint.trim(), "realistic")}>{busy ? "Generating…" : "Generate from image"}</button>
    </div>
  );
}
