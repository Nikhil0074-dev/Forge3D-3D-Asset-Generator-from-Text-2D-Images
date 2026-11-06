import { enhancePrompt, formatBytes, validateImage, validatePrompt, MAX_IMAGE_BYTES } from "../utils/validate";

describe("validatePrompt", () => {
  it.each([["", /Describe/], ["   ", /Describe/], ["ab", /too short/], ["x".repeat(1001), /too long/]])("rejects %j", (v, m) => expect(validatePrompt(v)).toMatch(m as RegExp));
  it("accepts a normal prompt", () => expect(validatePrompt("a wooden chair")).toBeNull());
});
describe("validateImage", () => {
  it("accepts png/jpeg/webp", () => ["image/png", "image/jpeg", "image/webp"].forEach((type) => expect(validateImage({ type, size: 100 })).toBeNull()));
  it("rejects gif, pdf", () => { expect(validateImage({ type: "image/gif", size: 1 })).toMatch(/Unsupported/); expect(validateImage({ type: "application/pdf", size: 1 })).toMatch(/Unsupported/); });
  it("rejects empty and oversize", () => { expect(validateImage({ type: "image/png", size: 0 })).toMatch(/empty/); expect(validateImage({ type: "image/png", size: MAX_IMAGE_BYTES + 1 })).toMatch(/too large/); });
  it("accepts exactly the limit", () => expect(validateImage({ type: "image/png", size: MAX_IMAGE_BYTES })).toBeNull());
});
describe("formatBytes", () => it("formats", () => { expect(formatBytes(512)).toBe("512 B"); expect(formatBytes(2048)).toBe("2.0 KB"); expect(formatBytes(12_500_000)).toBe("11.9 MB"); }));
describe("enhancePrompt", () => {
  it("returns empty for blank", () => expect(enhancePrompt("  ")).toBe(""));
  it("adds detail and keeps original", () => { const o = enhancePrompt("Generate a chair.", "low-poly"); expect(o).toContain("Generate a chair"); expect(o).toContain("low-poly style"); expect(o).toContain("primary material"); });
  it("skips material hint when present", () => expect(enhancePrompt("wooden table, wood")).not.toContain("primary material"));
});
