import { useRef, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { Backdrop, Floor, Lighting, LightingSetup, Loading, Model, ModelErrorBoundary, Suspense } from "../three/Scene";

export default function ModelViewer({ url }: { url: string | null }) {
  const [lighting, setLighting] = useState<Lighting>("studio");
  const [backdrop, setBackdrop] = useState<Backdrop>("dark");
  const [wire, setWire] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controls = useRef<any>(null);
  const box = useRef<HTMLDivElement>(null);

  return (
    <div className="viewer" ref={box} data-backdrop={backdrop}>
      {!url && <div className="empty"><b>No model yet</b><span>Generate one or open an asset from your library.</span></div>}
      {url && !error && (
        <Canvas key={url} camera={{ position: [3.2, 2.2, 3.6], fov: 40 }} gl={{ preserveDrawingBuffer: true, antialias: true, alpha: true }} dpr={[1, 2]}>
          <LightingSetup mode={lighting} />
          <ModelErrorBoundary resetKey={url} onError={setError}>
            <Suspense fallback={<Loading />}><Model url={url} wireframe={wire} /></Suspense>
          </ModelErrorBoundary>
          <Floor backdrop={backdrop} />
          <OrbitControls ref={controls} makeDefault enableDamping target={[0, 1, 0]} minDistance={1.5} maxDistance={14} />
        </Canvas>)}
      {error && <div className="empty" role="alert"><b>Couldn’t display this model</b><span>{error}</span><button className="ghost" onClick={() => setError(null)}>Retry</button></div>}
      <div className="vbar">
        <div className="seg" aria-label="Lighting">{(["studio", "directional", "ambient", "environment"] as Lighting[]).map((l) => <button key={l} className={lighting === l ? "on" : ""} aria-pressed={lighting === l} onClick={() => setLighting(l)}>{l}</button>)}</div>
        <div className="seg" aria-label="Background">{(["dark", "light", "grid"] as Backdrop[]).map((b) => <button key={b} className={backdrop === b ? "on" : ""} aria-pressed={backdrop === b} onClick={() => setBackdrop(b)}>{b}</button>)}</div>
        <div className="seg">
          <button className={wire ? "on" : ""} aria-pressed={wire} onClick={() => setWire(!wire)}>wireframe</button>
          <button onClick={() => controls.current?.reset()}>reset</button>
          <button onClick={() => box.current?.requestFullscreen?.()}>fullscreen</button>
        </div>
      </div>
    </div>
  );
}
