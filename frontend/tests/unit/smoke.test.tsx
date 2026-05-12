import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

describe("vitest + RTL smoke", () => {
  it("renders a basic element", () => {
    render(<h1>hello</h1>);
    expect(screen.getByRole("heading", { name: /hello/i })).toBeInTheDocument();
  });
});
