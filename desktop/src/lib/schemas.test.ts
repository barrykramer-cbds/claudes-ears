import { describe, expect, it } from "vitest";
import { PerceptionDocumentSchema, ProgressEventSchema } from "@/lib/schemas";
import { mockPerception } from "@/mock/perception";

describe("PerceptionDocumentSchema", () => {
  it("round-trips the mock document without loss", () => {
    const parsed = PerceptionDocumentSchema.parse(mockPerception);
    expect(parsed).toEqual(mockPerception);
  });

  it("accepts null domains (degraded modules)", () => {
    const degraded = { schema_version: "1.0", track: mockPerception.track };
    const parsed = PerceptionDocumentSchema.parse(degraded);
    expect(parsed.harmony).toBeUndefined();
    expect(parsed.genome).toBeUndefined();
  });

  it("rejects a document missing the required track key", () => {
    expect(() => PerceptionDocumentSchema.parse({ schema_version: "1.0" })).toThrow();
  });
});

describe("ProgressEventSchema", () => {
  it("validates an SSE payload", () => {
    const event = ProgressEventSchema.parse({
      job_id: "j1",
      step: "separation",
      index: 1,
      total: 21,
      status: "started",
    });
    expect(event.status).toBe("started");
  });

  it("rejects a zero-based index", () => {
    expect(() =>
      ProgressEventSchema.parse({ job_id: "j1", step: "x", index: 0, total: 21, status: "started" }),
    ).toThrow();
  });
});
