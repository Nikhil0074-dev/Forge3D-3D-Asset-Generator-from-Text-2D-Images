export const MAX_PROMPT = 1000;
export const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
export const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"];

export function validatePrompt(p: string): string | null {
  const t = p.trim();
  if (!t) return "Describe the object you want to generate.";
  if (t.length < 3) return "Prompt is too short — add a few more words.";
  if (t.length > MAX_PROMPT) return `Prompt is too long (max ${MAX_PROMPT} characters).`;
  return null;
}

export function validateImage(f: { type: string; size: number }): string | null {
  if (!IMAGE_TYPES.includes(f.type)) return "Unsupported file type. Use PNG, JPG or WebP.";
  if (f.size === 0) return "That file is empty.";
  if (f.size > MAX_IMAGE_BYTES) return `Image is too large (max ${MAX_IMAGE_BYTES / 1024 / 1024} MB).`;
  return null;
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 ** 2).toFixed(1)} MB`;
}

/** Rule-based prompt enhancer (no AI call): adds detail the user can edit before generating. */
export function enhancePrompt(raw: string, style = "realistic"): string {
  const t = raw.trim().replace(/\.$/, "");
  if (!t) return "";
  const hasMaterial = /(wood|metal|steel|stone|glass|plastic|gold|silver|leather|fabric|marble)/i.test(t);
  const bits = [t];
  if (!hasMaterial) bits.push("with a clearly defined primary material");
  bits.push(`${style} style`, "clean silhouette", "smooth edges", "neutral studio lighting", "single object, centered");
  return bits.join(", ") + ".";
}
