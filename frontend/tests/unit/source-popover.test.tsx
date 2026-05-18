import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import {
  SourceChip,
  groupCorroborators,
  uniqueIndependentSourceCount,
} from "@/components/brief/source-popover";

describe("groupCorroborators", () => {
  it("dedupes by source name and counts signals", () => {
    const groups = groupCorroborators([
      { id: "s1", name: "Defillama" },
      { id: "s2", name: "Defillama" },
      { id: "s3", name: "Defillama" },
      { id: "s4", name: "Defillama" },
      { id: "s5", name: "Defillama" },
      { id: "s6", name: "Defillama" },
      { id: "s7", name: "Defillama" },
      { id: "s8", name: "Fear & Greed Index" },
    ]);
    expect(groups).toEqual([
      { name: "Defillama", count: 7 },
      { name: "Fear & Greed Index", count: 1 },
    ]);
  });

  it("sorts by count desc then alphabetical", () => {
    const groups = groupCorroborators([
      { id: "a1", name: "Decrypt" },
      { id: "b1", name: "CoinDesk" },
      { id: "b2", name: "CoinDesk" },
      { id: "c1", name: "Bankless" },
      { id: "c2", name: "Bankless" },
    ]);
    // Bankless (2) and CoinDesk (2) tie on count → alpha → Bankless first
    expect(groups.map((g) => g.name)).toEqual(["Bankless", "CoinDesk", "Decrypt"]);
  });

  it("returns empty array for no corroborators", () => {
    expect(groupCorroborators([])).toEqual([]);
  });
});

describe("uniqueIndependentSourceCount", () => {
  it("excludes the primary source name from the count", () => {
    // Primary is Defillama; 7 Defillama corroborators don't count, F&G does
    const count = uniqueIndependentSourceCount("Defillama", [
      { id: "s1", name: "Defillama" },
      { id: "s2", name: "Defillama" },
      { id: "s3", name: "Defillama" },
      { id: "s4", name: "Defillama" },
      { id: "s5", name: "Defillama" },
      { id: "s6", name: "Defillama" },
      { id: "s7", name: "Defillama" },
      { id: "s8", name: "Fear & Greed Index" },
    ]);
    expect(count).toBe(1);
  });

  it("counts distinct names not signals", () => {
    const count = uniqueIndependentSourceCount("The Block", [
      { id: "a1", name: "CoinDesk" },
      { id: "a2", name: "CoinDesk" },
      { id: "a3", name: "CoinDesk" },
      { id: "b1", name: "Decrypt" },
    ]);
    expect(count).toBe(2);
  });

  it("returns 0 when all corroborators share name with primary", () => {
    const count = uniqueIndependentSourceCount("Defillama", [
      { id: "s1", name: "Defillama" },
      { id: "s2", name: "Defillama" },
    ]);
    expect(count).toBe(0);
  });
});

describe("SourceChip", () => {
  it("renders +1 source for 7 Defillama + 1 Fear & Greed with Defillama primary", () => {
    render(
      <SourceChip
        primaryName="Defillama"
        corroborators={[
          { id: "s1", name: "Defillama" },
          { id: "s2", name: "Defillama" },
          { id: "s3", name: "Defillama" },
          { id: "s4", name: "Defillama" },
          { id: "s5", name: "Defillama" },
          { id: "s6", name: "Defillama" },
          { id: "s7", name: "Defillama" },
          { id: "s8", name: "Fear & Greed Index" },
        ]}
      />,
    );
    const btn = screen.getByRole("button");
    expect(btn).toHaveTextContent(/\+1 source\b/);
    expect(btn).not.toHaveTextContent(/\+8/);
  });

  it("opens popover showing Defillama once with count and Fear & Greed once", () => {
    render(
      <SourceChip
        primaryName="Defillama"
        corroborators={[
          { id: "s1", name: "Defillama" },
          { id: "s2", name: "Defillama" },
          { id: "s3", name: "Defillama" },
          { id: "s4", name: "Defillama" },
          { id: "s5", name: "Defillama" },
          { id: "s6", name: "Defillama" },
          { id: "s7", name: "Defillama" },
          { id: "s8", name: "Fear & Greed Index" },
        ]}
      />,
    );
    fireEvent.click(screen.getByRole("button"));
    const dialog = screen.getByRole("dialog", { name: /corroborating sources/i });
    const items = within(dialog).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent(/Defillama/);
    expect(items[0]).toHaveTextContent(/\(7 signals\)/);
    expect(items[1]).toHaveTextContent(/Fear & Greed Index/);
    expect(items[1]).not.toHaveTextContent(/signals/);
  });

  it("renders sources plural correctly", () => {
    render(
      <SourceChip
        primaryName="The Block"
        corroborators={[
          { id: "a", name: "CoinDesk" },
          { id: "b", name: "Decrypt" },
        ]}
      />,
    );
    expect(screen.getByRole("button")).toHaveTextContent(/\+2 sources/);
  });

  it("shows single-sourced message when no corroborators", () => {
    render(<SourceChip primaryName="The Block" corroborators={[]} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("dialog")).toHaveTextContent(/single-sourced/i);
  });
});
