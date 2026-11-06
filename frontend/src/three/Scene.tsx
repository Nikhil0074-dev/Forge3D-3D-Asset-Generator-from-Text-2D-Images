import { Component, ReactNode, Suspense, useLayoutEffect, useMemo } from "react";
import { Environment, Grid, Html, Lightformer, useGLTF } from "@react-three/drei";
import * as THREE from "three";

export type Lighting = "studio" | "directional" | "ambient" | "environment";
export type Backdrop = "dark" | "light" | "grid";

export class ModelErrorBoundary extends Component<{ children: ReactNode; onError: (m: string) => void; resetKey: string }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(e: Error) { this.props.onError(e.message || "Could not load model"); }
  componentDidUpdate(p: { resetKey: string }) { if (p.resetKey !== this.props.resetKey && this.state.failed) this.setState({ failed: false }); }
  render() { return this.state.failed ? null : this.props.children; }
}

export function LightingSetup({ mode }: { mode: Lighting }) {
  switch (mode) {
    case "directional": return <><ambientLight intensity={0.25} /><directionalLight position={[4, 6, 3]} intensity={2.6} /></>;
    case "ambient": return <><ambientLight intensity={1.1} /><hemisphereLight args={["#ffffff", "#444455", 0.9]} /></>;
    case "environment": return (
      <Environment resolution={256}><group rotation={[0, 0.6, 0]}>
        <Lightformer form="rect" intensity={4} position={[0, 5, -6]} scale={[10, 4, 1]} />
        <Lightformer form="rect" intensity={2} position={[-6, 1, 2]} rotation-y={Math.PI / 2} scale={[8, 3, 1]} />
        <Lightformer form="ring" color="#ffb066" intensity={3} position={[5, 2, 3]} scale={3} />
      </group></Environment>);
    default: return <><ambientLight intensity={0.5} /><directionalLight position={[3, 5, 4]} intensity={2.2} /><directionalLight position={[-4, 2, 2]} intensity={0.9} color="#a8c4ff" /><directionalLight position={[0, 3, -5]} intensity={1.4} color="#ffd9b0" /></>;
  }
}

export function Model({ url, wireframe }: { url: string; wireframe: boolean }) {
  const gltf = useGLTF(url);
  const scene = useMemo(() => {
    const s = gltf.scene.clone(true);
    const box = new THREE.Box3().setFromObject(s);
    const size = box.getSize(new THREE.Vector3());
    const k = 2 / Math.max(size.x, size.y, size.z, 1e-6);       // normalise to a 2-unit cube
    const c = box.getCenter(new THREE.Vector3());
    const wrap = new THREE.Group();
    s.position.sub(c);
    wrap.add(s);
    wrap.scale.setScalar(k);
    wrap.position.y = (size.y * k) / 2 - 0.0;                    // rest on the floor
    return wrap;
  }, [gltf]);
  useLayoutEffect(() => {
    scene.traverse((o) => { const m = (o as THREE.Mesh).material as THREE.Material | THREE.Material[] | undefined; if (m) [m].flat().forEach((x: any) => { x.wireframe = wireframe; x.needsUpdate = true; }); });
  }, [scene, wireframe]);
  return <primitive object={scene} />;
}

export function Floor({ backdrop }: { backdrop: Backdrop }) {
  if (backdrop !== "grid") return null;
  return <Grid args={[20, 20]} cellColor="#6b4b2a" sectionColor="#e08a3c" fadeDistance={14} infiniteGrid position={[0, 0, 0]} />;
}

export function Loading() { return <Html center><span className="loading">Loading model…</span></Html>; }
export { Suspense };
