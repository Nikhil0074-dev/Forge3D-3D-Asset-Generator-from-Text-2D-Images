export type JobStatus = "queued" | "processing" | "completed" | "failed" | "cancelled";
export interface Job { job_id: string; status: JobStatus; progress: number | null; message: string; error: string | null; asset_id: string | null; generation_type: string }
export interface Stats { vertex_count: number; triangle_count: number; mesh_count: number; material_count: number; texture_count: number; width: number; height: number; depth: number; file_size: number }
export interface Asset { asset_id: string; name: string; generation_type: "text-to-3d" | "image-to-3d"; provider: string; format: string; created_at: number; file_size: number; prompt: string; stats: Stats; thumbnail: string }
export type ExportFormat = "glb" | "gltf" | "obj";
