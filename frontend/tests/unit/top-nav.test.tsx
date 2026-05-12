import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TopNav } from "@/components/nav/top-nav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/news/overview",
}));

describe("TopNav", () => {
  it("renders both top-level tabs", () => {
    render(<TopNav />);
    expect(screen.getByRole("button", { name: /news/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument();
  });

  it("opens the News dropdown on click and shows all six items", () => {
    render(<TopNav />);
    const trigger = screen.getByRole("button", { name: /news/i });
    fireEvent.click(trigger);
    for (const label of ["Overview", "Policy", "Markets", "Tech", "Adoption", "Misc"]) {
      const links = screen.getAllByRole("menuitem", { name: new RegExp(`^${label}$`, "i") });
      expect(links.length).toBeGreaterThan(0);
    }
  });

  it("marks the current News category as active in the dropdown", () => {
    render(<TopNav />);
    fireEvent.click(screen.getByRole("button", { name: /news/i }));
    const overview = screen.getByRole("menuitem", { name: /^overview$/i });
    expect(overview.className).toMatch(/brand/);
  });
});
