import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";

describe("API session and mutation boundaries", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("includes the CSRF cookie for a protected incident transition", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "resolved" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("document", { cookie: "csrftoken=local-test-token" });
    vi.stubGlobal("fetch", fetchMock);

    await api.action("00000000-0000-0000-0000-000000000001", "resolve");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(path).toContain("/resolve/");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("same-origin");
    expect(headers.get("X-CSRFToken")).toBe("local-test-token");
  });

  it("signals an expired session without treating ordinary permissions as expiration", async () => {
    const dispatched = vi.fn();
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: "Authentication credentials were not provided." }),
        { status: 403, headers: { "Content-Type": "application/json" } },
      ),
    ).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "You do not have permission." }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("document", { cookie: "" });
    vi.stubGlobal("window", { dispatchEvent: dispatched });
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.list({})).rejects.toBeInstanceOf(ApiError);
    expect(dispatched).toHaveBeenCalledTimes(1);
    expect(dispatched.mock.calls[0][0]).toBeInstanceOf(Event);

    await expect(api.list({})).rejects.toBeInstanceOf(ApiError);
    expect(dispatched).toHaveBeenCalledTimes(1);
  });

  it("returns a defined error if a server sends an invalid JSON response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("not JSON", { status: 502, headers: { "Content-Type": "text/plain" } }),
    );
    vi.stubGlobal("document", { cookie: "" });
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.session()).rejects.toMatchObject({
      name: "ApiError",
      status: 502,
      message: "The server returned an unexpected response.",
    });
  });
});
