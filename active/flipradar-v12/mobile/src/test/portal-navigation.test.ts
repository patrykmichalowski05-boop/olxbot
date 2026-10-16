import { isPublicWebRoute, safeReturnPath } from "@/features/portal/navigation";

describe("Public website and account boundaries", () => {
  it.each([[], ["index"], ["(auth)", "login"], ["register"], ["info"]])(
    "allows public content for %s",
    (...parts) => {
      const segments = Array.isArray(parts[0]) ? parts[0] : parts;
      expect(isPublicWebRoute(segments as string[])).toBe(true);
    },
  );
  it.each([
    ["radar"],
    ["(tabs)", "radar"],
    ["account"],
    ["searches"],
    ["searches", "results"],
    ["market"],
    ["bot"],
  ])("keeps private routes behind authentication: %s", (...parts) => {
    const segments = Array.isArray(parts[0]) ? parts[0] : parts;
    expect(isPublicWebRoute(segments as string[])).toBe(false);
  });
  it.each([
    "https://evil.example",
    "//evil.example",
    "/\\evil.example",
    "/login",
    "/register",
    "/%2f%2fevil.example",
    "/radar\nhttps://evil.example",
  ])("rejects unsafe or looping return destinations: %s", (path) => {
    expect(safeReturnPath(path)).toBeNull();
  });
  it("preserves the intended account/plan and normalizes an existing tab destination", () => {
    expect(safeReturnPath("/account?plan=STANDARD")).toBe(
      "/account?plan=STANDARD",
    );
    expect(safeReturnPath("/(tabs)/radar")).toBe("/radar");
    expect(safeReturnPath("/offer/snap-123")).toBe("/offer/snap-123");
    expect(safeReturnPath("/market")).toBe("/market");
    expect(safeReturnPath("/searches/results?id=own-profile")).toBe(
      "/searches/results?id=own-profile",
    );
  });
});
