import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ThemeCard } from "@/components/brief/theme-card";
import type { BriefTheme } from "@/types/brief";

vi.mock("next/navigation", () => ({
  usePathname: () => "/news/overview",
}));

const sampleTheme: BriefTheme = {
  id: "t1",
  display_order: 0,
  title: "Foo Corp partners with Bar for X",
  body: "Foo Corp announced a thing. Multiple sources confirm.",
  conviction_score: 4,
  primary_signal_id: "p1",
  primary_source_name: "The Block",
  primary_signal_title: "Foo Corp partnership announced",
  primary_signal_url: "https://example.com/foo",
  corroborating_count: 2,
  categories: ["markets", "tech"],
  corroborating_sources: [
    { id: "s2", name: "CoinDesk" },
    { id: "s3", name: "Decrypt" },
  ],
};

describe("ThemeCard", () => {
  it("renders title, body, primary source, and category chips", () => {
    render(<ThemeCard theme={sampleTheme} total={5} />);
    expect(screen.getByText(/Foo Corp partners with Bar for X/i)).toBeInTheDocument();
    expect(screen.getByText(/multiple sources confirm/i)).toBeInTheDocument();
    expect(screen.getByText(/The Block/i)).toBeInTheDocument();
    expect(screen.getByText(/markets/i)).toBeInTheDocument();
    expect(screen.getByText(/tech/i)).toBeInTheDocument();
  });

  it("shows the read primary article link with the URL", () => {
    render(<ThemeCard theme={sampleTheme} total={5} />);
    const link = screen.getByRole("link", { name: /read primary article/i });
    expect(link).toHaveAttribute("href", "https://example.com/foo");
  });

  it("opens the conviction tooltip on click and shows the scale", () => {
    render(<ThemeCard theme={sampleTheme} total={5} />);
    const trigger = screen.getByRole("button", { name: /conviction 4 of 5/i });
    fireEvent.click(trigger);
    const dialog = screen.getByRole("dialog", { name: /conviction scale/i });
    expect(dialog).toBeInTheDocument();
    // Score 5 row describes cross-type corroboration (post-v7.1), not "broad consensus"
    expect(dialog).toHaveTextContent(/cross-source-type corroboration/i);
    expect(dialog).not.toHaveTextContent(/broad consensus/i);
  });

  it("opens the corroborating-sources popover and lists names", () => {
    render(<ThemeCard theme={sampleTheme} total={5} />);
    const chip = screen.getByText(/The Block/i).closest("button");
    expect(chip).toBeTruthy();
    // Badge shows "+2 sources" since both corroborators are distinct from primary
    expect(chip).toHaveTextContent(/\+2 sources/);
    fireEvent.click(chip!);
    const dialog = screen.getByRole("dialog", { name: /corroborating sources/i });
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveTextContent("CoinDesk");
    expect(dialog).toHaveTextContent("Decrypt");
  });
});
