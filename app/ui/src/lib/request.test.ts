import { describe, expect, it } from "vitest";
import {
  buildQueryString,
  extractErrorMessage,
  normalizeRequestError,
  MalcomRequestError,
  resolveBaseUrl,
  withQueryParams
} from "./request";

describe("request helpers", () => {
  it("resolves localhost file and remote origins consistently", () => {
    expect(resolveBaseUrl({ protocol: "file:", origin: "null" } as Location)).toBe("http://localhost:8000");
    expect(resolveBaseUrl({ protocol: "http:", origin: "http://localhost:8000" } as Location)).toBe("");
    expect(resolveBaseUrl({ protocol: "http:", origin: "http://127.0.0.1:8000" } as Location)).toBe("");
    expect(resolveBaseUrl({ protocol: "https:", origin: "https://malcom.example" } as Location)).toBe("https://malcom.example");
  });

  it("builds query strings while skipping empty values", () => {
    expect(buildQueryString({ page: 2, filter: "ready", empty: "", skip: null, ids: ["a", "b"] })).toBe("?page=2&filter=ready&ids=a&ids=b");
    expect(withQueryParams("/api/v1/tools", { enabled: true, search: "" })).toBe("/api/v1/tools?enabled=true");
  });

  it("extracts consistent messages from common payload shapes", () => {
    expect(extractErrorMessage({ detail: "Boom" }, "Fallback")).toBe("Boom");
    expect(extractErrorMessage({ message: "Bad request" }, "Fallback")).toBe("Bad request");
    expect(extractErrorMessage({ detail: { issues: [{ line: 3, column: 2, message: "Missing field" }] } }, "Fallback")).toBe("Line 3, column 2: Missing field");
    expect(extractErrorMessage(null, "Fallback")).toBe("Fallback");
  });

  it("normalizes request errors into a shared shape", () => {
    const error = new MalcomRequestError("Not found", { status: 404, method: "GET", url: "/api/v1/missing" });
    expect(normalizeRequestError(error)).toMatchObject({
      message: "Not found",
      status: 404,
      method: "GET",
      url: "/api/v1/missing"
    });
  });
});
