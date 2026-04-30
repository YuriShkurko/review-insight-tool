import { afterEach, describe, expect, it, vi } from "vitest";
import { getApiBaseUrl } from "../api";

function setHostname(hostname: string) {
  vi.stubGlobal("window", { location: { hostname } });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("getApiBaseUrl", () => {
  it("keeps localhost when the page is local", () => {
    setHostname("localhost");

    expect(getApiBaseUrl()).toBe("http://localhost:8000");
  });

  it("keeps localhost when the page is 127.0.0.1", () => {
    setHostname("127.0.0.1");

    expect(getApiBaseUrl()).toBe("http://localhost:8000");
  });

  it("uses the page host for local mobile dev access", () => {
    setHostname("192.168.1.23");

    expect(getApiBaseUrl()).toBe("http://192.168.1.23:8000");
  });

  it("does not rewrite an explicit remote NEXT_PUBLIC_API_URL", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com");
    setHostname("192.168.1.23");
    const { getApiBaseUrl: freshGetBase } = await import("../api");

    expect(freshGetBase()).toBe("https://api.example.com");

    vi.unstubAllEnvs();
  });
});
