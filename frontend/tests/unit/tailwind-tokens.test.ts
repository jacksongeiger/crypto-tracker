import { describe, expect, it } from "vitest";
import config from "../../tailwind.config";

describe("tailwind theme tokens", () => {
  const colors = config.theme?.extend?.colors as Record<string, unknown>;
  const fontSize = config.theme?.extend?.fontSize as Record<string, unknown>;

  it("exposes Coinbase brand blue shades", () => {
    expect(colors.brand).toMatchObject({
      500: "#0052FF",
      600: "#0040C2",
    });
  });

  it("exposes ink and surface tokens", () => {
    expect(colors.ink).toMatchObject({ DEFAULT: "#0A0B0D" });
    expect(colors.surface).toMatchObject({ DEFAULT: "#FFFFFF" });
  });

  it("exposes the editorial type scale", () => {
    expect(fontSize.display).toBeDefined();
    expect(fontSize.bodyLg).toBeDefined();
    expect(fontSize.caption).toBeDefined();
    expect(fontSize.mono).toBeDefined();
  });
});
