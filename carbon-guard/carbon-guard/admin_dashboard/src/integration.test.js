// Integration test against a RUNNING backend. Skipped unless CG_INTEGRATION=1.
//   set CG_INTEGRATION=1 & set CG_ADMIN_EMAIL=... & set CG_ADMIN_PASSWORD=... & set VITE_API_URL=http://127.0.0.1:8000
//   npx vitest run src/integration.test.js
// It uses the same api.js functions as the pages, so it proves the dashboard and backend agree on
// paths and fields. It changes data (approves/rejects submissions): use the in-memory database.
import { beforeAll, describe, expect, it, vi } from "vitest";

const RUN = process.env.CG_INTEGRATION === "1";
let api;

beforeAll(async () => {
  if (!RUN) return;
  const mem = {};
  vi.stubGlobal("localStorage", {
    getItem: (k) => mem[k] ?? null, setItem: (k, v) => { mem[k] = v; }, removeItem: (k) => { delete mem[k]; },
  });
  api = await import("./api.js");
  const { access_token } = await api.login(process.env.CG_ADMIN_EMAIL, process.env.CG_ADMIN_PASSWORD);
  api.setToken(access_token);
});

describe.skipIf(!RUN)("dashboard <-> backend", () => {
  it("logs in as admin", async () => {
    expect((await api.me()).role).toBe("admin");
  });

  it("loads overview data", async () => {
    const s = await api.getStats();
    expect(s.by_status).toHaveProperty("manual_review");
    const r = await api.getReports();
    expect(r.by_activity).toHaveLength(3);
  });

  it("reviews submissions: approve, reject, reopen", async () => {
    const queue = await api.listSubmissions({ status: "manual_review", limit: 50 });
    expect(queue.items.length).toBeGreaterThanOrEqual(2);
    const [first, second] = queue.items;
    const detail = await api.getSubmission(first.id);
    expect(detail).toHaveProperty("satellite_verification");
    expect(detail).toHaveProperty("related_submission_ids");

    const approved = await api.approve(first.id, "Integration test approval");
    expect(approved.status).toBe("verified");
    expect(approved.review_notes).toBe("Integration test approval");
    await expect(api.approve(first.id)).rejects.toThrow(/verified/);

    expect((await api.reject(second.id, "Integration test rejection")).status).toBe("rejected");
    const reopened = await api.sendToManualReview(second.id, "Second look");
    expect(reopened.status).toBe("manual_review");
    expect(reopened.review_round).toBe(1);
  });

  it("searches users, opens one, deactivates and reactivates", async () => {
    const page = await api.listUsers({ search: "demo.ben", limit: 25 });
    expect(page.total).toBe(1);
    const u = await api.getUser(page.items[0].id);
    expect(u.trust_events.length).toBeGreaterThan(0);
    expect((await api.setUserActive(u.id, false)).is_active).toBe(false);
    expect((await api.setUserActive(u.id, true)).is_active).toBe(true);
  });

  it("lists fraud flags and the audit log", async () => {
    const flags = await api.getFraudFlags({ limit: 25 });
    expect(flags.items.some((f) => f.flags.includes("duplicate_image"))).toBe(true);
    const audit = await api.getAuditLogs({ limit: 50 });
    expect(audit.items.map((a) => a.action)).toEqual(expect.arrayContaining(["submission_approved", "user_deactivated"]));
  });

  it("edits credit rules and settings", async () => {
    const rules = await api.getCreditRules();
    const solar = rules.find((r) => r.activity_type === "solar_panel");
    const saved = await api.updateCreditRule("solar_panel", { ...solar, base_credit_value: 6 });
    expect(saved.base_credit_value).toBe(6);
    const cfg = await api.getConfig();
    const updated = await api.updateConfig({ recommend_threshold: cfg.recommend_threshold });
    expect(updated.recommend_threshold).toBe(cfg.recommend_threshold);
    await expect(api.updateConfig({ trust_rules: { bogus: 1 } })).rejects.toThrow(/Unknown/);
  });
});
