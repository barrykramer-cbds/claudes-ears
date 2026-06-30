import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { mockPerception } from "@/mock/perception";
import { VoicesTab } from "./VoicesTab";
import { HarmonyTab } from "./HarmonyTab";
import { StructureTab } from "./StructureTab";
import { SpaceTab } from "./SpaceTab";
import { AiLensTab } from "./AiLensTab";
import { StoryTab } from "./StoryTab";
import { LibraryTab } from "./LibraryTab";

describe("tab render smoke", () => {
  it("Voices renders the beeswarm and the register readout", () => {
    const { container } = render(<VoicesTab doc={mockPerception} />);
    expect(screen.getByText("Vocal relationship · density over time")).toBeInTheDocument();
    expect(container.querySelectorAll(".swarm-dot").length).toBeGreaterThan(0);
    expect(screen.getByText("196.4")).toBeInTheDocument();
  });

  it("Harmony renders the chord ribbon and a cadence", () => {
    render(<HarmonyTab doc={mockPerception} />);
    expect(screen.getByText("Chords across time")).toBeInTheDocument();
    expect(screen.getByText(/authentic/)).toBeInTheDocument();
  });

  it("Structure renders the energy/tension field and a section state", () => {
    render(<StructureTab doc={mockPerception} />);
    expect(screen.getByText("Energy & tension across the song")).toBeInTheDocument();
    expect(screen.getAllByText(/weary/).length).toBeGreaterThan(0);
  });

  it("Space renders the stereo field and room readout", () => {
    render(<SpaceTab doc={mockPerception} />);
    expect(screen.getByText("Stereo field")).toBeInTheDocument();
    expect(screen.getByText("Width by band")).toBeInTheDocument();
    expect(screen.getByText("medium hall")).toBeInTheDocument();
  });

  it("AI lens frames the read as a lens, not a verdict", () => {
    render(<AiLensTab doc={mockPerception} />);
    expect(screen.getByText("The voice argues with itself.")).toBeInTheDocument();
    expect(screen.getByText("Register variance")).toBeInTheDocument();
  });

  it("Story renders the grounded reading", () => {
    render(<StoryTab doc={mockPerception} />);
    expect(screen.getByText(/Nazareth/)).toBeInTheDocument();
    expect(screen.getByText(/transcribed via whisper/)).toBeInTheDocument();
  });

  it("Library renders the track browser and twins shape", () => {
    render(<LibraryTab doc={mockPerception} />);
    expect(screen.getByText("Tracks")).toBeInTheDocument();
    expect(screen.getByText("Sonic twins")).toBeInTheDocument();
  });
});
