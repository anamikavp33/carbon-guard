import { afterEach, describe, expect, it, vi } from "vitest";
import { approve, formatDetail, listSubmissions, login, query } from "./api.js";
import { fmtDate, num, statusLabel } from "./format.js";

afterEach(() => vi.unstubAllGlobals());

function fakeFetch(status, body) {
  const fn = vi.fn(async () => ({ ok: status < 400, status, json: async () => body }));
  vi.stubGlobal("fetch", fn);
  return fn;
}

describe("query()", () => {
  it("leaves out empty values and 'all'", () => {
    expect(query({ status: "pending", activity_type: "all", search: "", skip: 0, limit: 25 }))
      .toBe("?status=pending&skip=0&limit=25");
    expect(query({})).toBe("");
  });
  it("encodes user input", () => {
    expect(query({ search: "a&b c" })).toBe("?search=a%26b%20c");
  });
});

describe("formatDetail()", () => {
  it("handles text, 422 lists and nothing", () => {
    expect(formatDetail({ detail: "Email already registered" })).toBe("Email already registered");
    expect(formatDetail({ detail: [{ loc: ["body", "password"], msg: "too short" }] })).toBe("password: too short");
    expect(formatDetail(null)).toBe("");
  });
});

describe("request()", () => {
  it("calls the contract paths with the right method and body", async () => {
    const f = fakeFetch(200, { items: [], total: 0, skip: 0, limit: 25 });
    await listSubmissions({ status: "manual_review", limit: 25 });
    expect(f.mock.calls[0][0]).toMatch(/\/admin\/submissions\?status=manual_review&limit=25$/);
    await approve("abc", "Looks right");
    const [url, opts] = f.mock.calls[1];
    expect(url).toMatch(/\/admin\/submissions\/abc\/approve$/);
    expect(opts.method).toBe("POST");
    expect(JSON.parse(opts.body)).toEqual({ notes: "Looks right" });
  });

  it("turns backend errors into readable messages", async () => {
    fakeFetch(401, { detail: "Invalid email or password" });
    await expect(login("a@b.com", "x")).rejects.toThrow("Invalid email or password");
    fakeFetch(409, {});
    await expect(approve("abc")).rejects.toThrow("Request failed (409)");
  });

  it("explains when the backend is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    await expect(login("a@b.com", "x")).rejects.toThrow(/Cannot reach the backend/);
  });
});

describe("format helpers", () => {
  it("formats dates, numbers and statuses", () => {
    expect(fmtDate(null)).toBe("-");
    expect(fmtDate("not a date")).toBe("-");
    expect(fmtDate("2026-10-25T16:19:14.129000Z")).not.toBe("-");
    expect(num(null)).toBe("-");
    expect(num(12)).toBe("12");
    expect(statusLabel("manual_review")).toBe("Manual review");
  });
});
