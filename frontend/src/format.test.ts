import { describe, expect, it } from "vitest";
import { timeAgo } from "./format";

describe("timeAgo", () => {
  const now = Date.parse("2026-10-20T20:00:00.000Z");

  it("formats recent incidents", () => {
    expect(timeAgo("2026-10-20T19:59:40.000Z", now)).toBe("Just now");
    expect(timeAgo("2026-10-20T19:55:00.000Z", now)).toBe("5m ago");
    expect(timeAgo("2026-10-20T18:00:00.000Z", now)).toBe("2h ago");
    expect(timeAgo("2026-10-18T20:00:00.000Z", now)).toBe("2d ago");
  });

  it("handles clocks and invalid input", () => {
    expect(timeAgo("2026-10-21T20:00:00.000Z", now)).toBe("Just now");
    expect(timeAgo("invalid", now)).toBe("Unknown");
  });
});
