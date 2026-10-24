import { describe, expect, it, vi } from "vitest";
import { ApiError, createClient, greedyPlan, resolveSource } from "../api";

describe("data source config", () => {
  it("defaults to api, accepts fixture, rejects anything else", () => {
    expect(resolveSource(undefined)).toBe("api");
    expect(resolveSource("fixture")).toBe("fixture");
    expect(() => resolveSource("Fixture")).toThrow(/VITE_DATA_SOURCE/);
  });
});

describe("api client never falls back to fixtures", () => {
  it("surfaces the server detail on HTTP errors", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "unknown graph_id: x" }), { status: 404 }));
    const err = await createClient("api", "", fetchImpl).attack("x").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 404, message: "unknown graph_id: x" });
  });

  it("reports an unreachable API instead of returning data", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError("fetch failed"));
    await expect(createClient("api", "", fetchImpl).personas()).rejects.toMatchObject({ status: 0, message: expect.stringContaining("unreachable") });
  });
});

describe("fixture client", () => {
  const c = createClient("fixture");
  it("serves the committed synthetic persona and rejects unknown ones", async () => {
    const [p] = await c.personas();
    expect(p.id).toBe("pat-example-01");
    await expect(c.twin("someone-real")).rejects.toMatchObject({ status: 404 });
  });

  it("fix plan severs every fixture path", async () => {
    const { paths } = await c.attack("g-pat-example-01");
    const plan = greedyPlan(paths);
    expect(plan).toMatchObject({ paths_before: 3, paths_after: 0 });
  });
});
