import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PromptInput from "../components/PromptInput";
import ImageUploader from "../components/ImageUploader";
import GenerationProgress, { stepIndex } from "../components/GenerationProgress";
import ExportPanel from "../components/ExportPanel";
import AssetCard from "../components/AssetCard";
import ModelStatistics from "../components/ModelStatistics";
import type { Asset, Job } from "../types";

const job = (o: Partial<Job> = {}): Job => ({ job_id: "j", status: "processing", progress: 40, message: "Generating", error: null, asset_id: null, generation_type: "text-to-3d", ...o });
const asset: Asset = { asset_id: "a1", name: "Red chair", generation_type: "text-to-3d", provider: "mock", format: "glb", created_at: 1700000000, file_size: 12500, prompt: "p", thumbnail: "/t.png",
  stats: { vertex_count: 1234, triangle_count: 5678, mesh_count: 3, material_count: 2, texture_count: 0, width: 1, height: 2, depth: 3, file_size: 12500 } };

describe("PromptInput", () => {
  it("shows an error and does not submit on empty prompt", async () => {
    const fn = vi.fn(); render(<PromptInput busy={false} onSubmit={fn} />);
    await userEvent.click(screen.getByText("Generate 3D model"));
    expect(screen.getByRole("alert")).toHaveTextContent(/Describe/); expect(fn).not.toHaveBeenCalled();
  });
  it("submits trimmed prompt with style and quality", async () => {
    const fn = vi.fn(); render(<PromptInput busy={false} onSubmit={fn} />);
    await userEvent.type(screen.getByLabelText(/Describe your object/), "  a red chair  ");
    await userEvent.selectOptions(screen.getByLabelText("Style"), "low-poly"); await userEvent.selectOptions(screen.getByLabelText("Quality"), "high");
    await userEvent.click(screen.getByText("Generate 3D model"));
    expect(fn).toHaveBeenCalledWith("a red chair", "low-poly", "high");
  });
  it("enhance button rewrites prompt; disabled when empty", async () => {
    render(<PromptInput busy={false} onSubmit={vi.fn()} />);
    const b = screen.getByText(/Enhance prompt/); expect(b).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/Describe your object/), "chair"); expect(b).toBeEnabled(); await userEvent.click(b);
    expect((screen.getByLabelText(/Describe your object/) as HTMLTextAreaElement).value).toMatch(/studio lighting/);
  });
  it("example chip fills the prompt; busy disables submit", async () => {
    const { rerender } = render(<PromptInput busy={false} onSubmit={vi.fn()} />);
    await userEvent.click(screen.getByText(/sci-fi robot/)); expect((screen.getByLabelText(/Describe/) as HTMLTextAreaElement).value).toMatch(/robot/);
    rerender(<PromptInput busy onSubmit={vi.fn()} />); expect(screen.getByRole("button", { name: /Generating/ })).toBeDisabled();
  });
});

describe("ImageUploader", () => {
  beforeEach(() => { (URL as any).createObjectURL = vi.fn(() => "blob:x"); (URL as any).revokeObjectURL = vi.fn(); });
  const up = (f: File) => fireEvent.change(screen.getByTestId("file-input"), { target: { files: [f] } });
  it("disables submit until valid file chosen", () => { render(<ImageUploader busy={false} onSubmit={vi.fn()} />); expect(screen.getByText("Generate from image")).toBeDisabled(); });
  it("rejects wrong type", async () => { render(<ImageUploader busy={false} onSubmit={vi.fn()} />); up(new File(["x"], "a.gif", { type: "image/gif" })); expect(await screen.findByRole("alert")).toHaveTextContent(/Unsupported/); expect(screen.getByText("Generate from image")).toBeDisabled(); });
  it("rejects oversize", async () => { render(<ImageUploader busy={false} onSubmit={vi.fn()} />); const f = new File(["x"], "a.png", { type: "image/png" }); Object.defineProperty(f, "size", { value: 9 * 1024 * 1024 }); up(f); expect(await screen.findByRole("alert")).toHaveTextContent(/too large/); });
  it("previews, then submits file with hint", async () => {
    const fn = vi.fn(); render(<ImageUploader busy={false} onSubmit={fn} />);
    const f = new File(["x"], "a.png", { type: "image/png" }); up(f);
    expect(await screen.findByAltText("Selected reference")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/Optional hint/), "chair"); await userEvent.click(screen.getByText("Generate from image"));
    expect(fn).toHaveBeenCalledWith(f, "chair", "realistic");
  });
  it("Replace clears the selection", async () => { render(<ImageUploader busy={false} onSubmit={vi.fn()} />); up(new File(["x"], "a.png", { type: "image/png" })); await userEvent.click(await screen.findByText("Replace")); expect(screen.queryByAltText("Selected reference")).toBeNull(); });
});

describe("GenerationProgress", () => {
  it("determinate bar shows percentage", () => { render(<GenerationProgress job={job({ progress: 65 })} />); expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "65"); });
  it("indeterminate when progress is null (never invents a number)", () => { render(<GenerationProgress job={job({ progress: null })} />); const p = screen.getByRole("progressbar"); expect(p).not.toHaveAttribute("aria-valuenow"); expect(p.className).toMatch(/indeterminate/); });
  it("shows error on failure and no cancel", () => { render(<GenerationProgress job={job({ status: "failed", error: "quota exceeded" })} onCancel={vi.fn()} />); expect(screen.getByText("quota exceeded")).toBeInTheDocument(); expect(screen.queryByText("Cancel")).toBeNull(); });
  it("cancel fires while running", async () => { const f = vi.fn(); render(<GenerationProgress job={job()} onCancel={f} />); await userEvent.click(screen.getByText("Cancel")); expect(f).toHaveBeenCalled(); });
  it("step mapping", () => { expect(stepIndex(job({ status: "queued" }))).toBe(0); expect(stepIndex(job())).toBe(1); expect(stepIndex(job({ message: "Validating and processing model" }))).toBe(2); expect(stepIndex(job({ status: "completed" }))).toBe(4); });
});

describe("ExportPanel", () => {
  it("calls export for each format", async () => { const f = vi.fn().mockResolvedValue(undefined); render(<ExportPanel onExport={f} />); for (const x of ["glb", "gltf", "obj"]) await userEvent.click(screen.getByText(`Download .${x}`)); expect(f.mock.calls.map((c) => c[0])).toEqual(["glb", "gltf", "obj"]); });
  it("shows an error when export fails", async () => { render(<ExportPanel onExport={vi.fn().mockRejectedValue(new Error("Export failed: bad"))} />); await userEvent.click(screen.getByText("Download .obj")); expect(await screen.findByRole("alert")).toHaveTextContent("Export failed: bad"); });
});

describe("AssetCard", () => {
  it("opens, renames (Enter), deletes", async () => {
    const o = vi.fn(), r = vi.fn(), d = vi.fn(); render(<AssetCard asset={asset} onOpen={o} onRename={r} onDelete={d} />);
    await userEvent.click(screen.getByLabelText("Open Red chair")); expect(o).toHaveBeenCalledWith(asset);
    await userEvent.click(screen.getByText("Rename")); const i = screen.getByLabelText("Asset name"); await userEvent.clear(i); await userEvent.type(i, "Blue chair{Enter}");
    expect(r).toHaveBeenCalledWith(asset, "Blue chair"); await userEvent.click(screen.getByText("Delete")); expect(d).toHaveBeenCalledWith(asset);
  });
  it("does not rename to blank", async () => { const r = vi.fn(); render(<AssetCard asset={asset} onOpen={vi.fn()} onRename={r} onDelete={vi.fn()} />); await userEvent.click(screen.getByText("Rename")); await userEvent.clear(screen.getByLabelText("Asset name")); await userEvent.tab(); expect(r).not.toHaveBeenCalled(); expect(screen.getByText("Red chair")).toBeInTheDocument(); });
});

describe("ModelStatistics", () => it("renders counts", () => { render(<ModelStatistics asset={asset} />); expect(screen.getByText("5,678")).toBeInTheDocument(); expect(screen.getByText("1,234")).toBeInTheDocument(); expect(screen.getByText("12.2 KB")).toBeInTheDocument(); }));
