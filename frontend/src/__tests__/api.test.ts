import { api, pollJob } from "../services/api";

const res = (body: any, status = 200, headers: Record<string, string> = {}) => new Response(status === 204 ? null : JSON.stringify(body), { status, headers });
afterEach(() => vi.restoreAllMocks());

describe("api", () => {
  it("generateText posts JSON", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(res({ job_id: "j1" }, 202));
    expect(await api.generateText("chair", "realistic", "high")).toEqual({ job_id: "j1" });
    const [u, init] = f.mock.calls[0]; expect(u).toBe("/api/generation/text"); expect(JSON.parse((init as any).body)).toEqual({ prompt: "chair", style: "realistic", quality: "high", output_format: "glb" });
  });
  it("surfaces string and validation-array errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(res({ detail: "Rate limit exceeded" }, 429)).mockResolvedValueOnce(res({ detail: [{ msg: "too short" }, { msg: "bad" }] }, 422));
    await expect(api.generateText("x", "a", "b")).rejects.toThrow("Rate limit exceeded");
    await expect(api.generateText("x", "a", "b")).rejects.toThrow("too short; bad");
  });
  it("falls back to generic message on non-JSON error", async () => { vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("oops", { status: 500 })); await expect(api.asset("a")).rejects.toThrow("Request failed (500)"); });
  it("remove handles 204", async () => { vi.spyOn(globalThis, "fetch").mockResolvedValue(res(null, 204)); await expect(api.remove("a")).resolves.toBeUndefined(); });
  it("assets encodes search", async () => { const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(res([])); await api.assets("a b&c", "text-to-3d"); expect(f.mock.calls[0][0]).toBe("/api/assets?search=a%20b%26c&type=text-to-3d"); });
  it("exportAsset reads filename from header", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("zip", { status: 200, headers: { "content-disposition": 'attachment; filename="chair_obj.zip"' } }));
    expect((await api.exportAsset("a", "obj")).filename).toBe("chair_obj.zip");
  });
  it("exportAsset throws server error", async () => { vi.spyOn(globalThis, "fetch").mockResolvedValue(res({ detail: "Unsupported format" }, 422)); await expect(api.exportAsset("a", "obj")).rejects.toThrow("Unsupported format"); });
  it("generateImage sends multipart", async () => { const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(res({ job_id: "j" }, 202)); await api.generateImage(new File(["x"], "a.png", { type: "image/png" }), "hint", "realistic"); expect((f.mock.calls[0][1] as any).body).toBeInstanceOf(FormData); });
});

describe("pollJob", () => {
  const J = (status: string) => res({ job_id: "j", status, progress: null, message: "", error: null, asset_id: null, generation_type: "t" });
  it("polls until terminal state and reports each update", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(J("queued")).mockResolvedValueOnce(J("processing")).mockResolvedValueOnce(J("completed"));
    const seen: string[] = []; const out = await pollJob("j", (j) => seen.push(j.status), 1);
    expect(out.status).toBe("completed"); expect(seen).toEqual(["queued", "processing", "completed"]);
  });
  it("stops on failure", async () => { vi.spyOn(globalThis, "fetch").mockResolvedValue(J("failed")); expect((await pollJob("j", () => {}, 1)).status).toBe("failed"); });
  it("aborts", async () => { const c = new AbortController(); c.abort(); await expect(pollJob("j", () => {}, 1, c.signal)).rejects.toThrow("aborted"); });
});
