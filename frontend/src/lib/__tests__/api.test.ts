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

  it("uses the page host for local mobile dev access", () => {
    setHostname("192.168.1.23");

    expect(getApiBaseUrl()).toBe("http://192.168.1.23:8000");
  });
});
