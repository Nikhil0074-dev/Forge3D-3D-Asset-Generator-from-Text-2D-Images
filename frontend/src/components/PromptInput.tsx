import { useState } from "react";
import { enhancePrompt, MAX_PROMPT, validatePrompt } from "../utils/validate";

export const STYLES = ["realistic", "stylized", "low-poly", "sci-fi", "fantasy"];
export const QUALITIES = ["draft", "standard", "high"];
export const EXAMPLES = ["A futuristic sports car with metallic blue paint", "A sci-fi robot with glowing blue eyes", "A detailed fantasy sword with a golden handle", "A low-poly medieval castle with stone walls"];

interface Props { busy: boolean; onSubmit: (prompt: string, style: string, quality: string) => void }

export default function PromptInput({ busy, onSubmit }: Props) {
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("realistic");
  const [quality, setQuality] = useState("standard");
  const [error, setError] = useState<string | null>(null);

  const submit = () => {
    const e = validatePrompt(prompt);
    setError(e);
    if (!e) onSubmit(prompt.trim(), style, quality);
  };
  return (
    <div className="stack">
      <label className="label" htmlFor="prompt">Describe your object</label>
      <textarea id="prompt" rows={4} value={prompt} placeholder="e.g. A realistic wooden chair with four legs" maxLength={MAX_PROMPT + 50}
        onChange={(e) => { setPrompt(e.target.value); if (error) setError(null); }} />
      <div className="row between small muted"><span>{prompt.trim().length}/{MAX_PROMPT}</span>
        <button type="button" className="link" disabled={!prompt.trim()} onClick={() => setPrompt(enhancePrompt(prompt, style))}>✦ Enhance prompt</button></div>
      {error && <p role="alert" className="error">{error}</p>}
      <div className="chips" aria-label="Examples">{EXAMPLES.map((x) => <button type="button" key={x} className="chip" onClick={() => { setPrompt(x); setError(null); }}>{x}</button>)}</div>
      <div className="grid2">
        <div><label className="label" htmlFor="style">Style</label><select id="style" value={style} onChange={(e) => setStyle(e.target.value)}>{STYLES.map((s) => <option key={s}>{s}</option>)}</select></div>
        <div><label className="label" htmlFor="quality">Quality</label><select id="quality" value={quality} onChange={(e) => setQuality(e.target.value)}>{QUALITIES.map((s) => <option key={s}>{s}</option>)}</select></div>
      </div>
      <button className="primary" disabled={busy} onClick={submit}>{busy ? "Generating…" : "Generate 3D model"}</button>
    </div>
  );
}
