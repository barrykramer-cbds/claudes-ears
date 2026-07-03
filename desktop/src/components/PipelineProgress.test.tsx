import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PipelineProgress } from "@/components/PipelineProgress";
import { PIPELINE_STEP_COUNT } from "@/lib/pipeline-steps";

describe("PipelineProgress", () => {
  it("renders all 21 stages and a zeroed progressbar", () => {
    render(<PipelineProgress statuses={{}} activeStep={null} />);
    expect(screen.getByText(`0 / ${PIPELINE_STEP_COUNT}`)).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");
    expect(screen.getByText("Separating stems")).toBeInTheDocument();
  });

  it("counts completed and skipped steps toward progress", () => {
    render(
      <PipelineProgress
        statuses={{ separation: "completed", analyze_stems: "skipped" }}
        activeStep="freq_interaction"
      />,
    );
    expect(screen.getByText(`2 / ${PIPELINE_STEP_COUNT}`)).toBeInTheDocument();
    const expected = String(Math.round((2 / PIPELINE_STEP_COUNT) * 100));
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", expected);
  });

  it("renders unknown SSE steps (YouTube download) ahead of the pipeline", () => {
    render(
      <PipelineProgress
        statuses={{ download: "completed", separation: "started" }}
        activeStep="separation"
      />,
    );
    expect(screen.getByText("Downloading audio")).toBeInTheDocument();
    expect(screen.getByText("Source")).toBeInTheDocument();
    expect(screen.getByText(`1 / ${PIPELINE_STEP_COUNT + 1}`)).toBeInTheDocument();
  });

  it("humanizes an unrecognized step name instead of crashing", () => {
    render(<PipelineProgress statuses={{ future_step: "started" }} activeStep="future_step" />);
    expect(screen.getByText("future step")).toBeInTheDocument();
  });
});
