import assert from "node:assert/strict";
import test from "node:test";

import {
  activityExportFilename,
  buildActivityExport,
  captureActivityFilters,
  fetchAllMatchingActivity,
} from "../src/activityHistory.js";

const filters = {
  user_search: "actor@example.com",
  action: "edit",
  document_search: "report",
  outcome: "success",
  start_at: "2026-01-01T00:00:00.000Z",
  end_at: "2026-12-31T23:59:00.000Z",
};

const entries = [
  { id: 2, timestamp: "2026-05-02T10:00:00Z", user_id: 7, actor_email: "actor@example.com", action: "edit", document_id: 9, document_name: "Quarterly | Report", outcome: "success", hash: "hash-2", prev_hash: "hash-1" },
  { id: 1, timestamp: "2026-05-01T10:00:00Z", user_id: null, actor_email: null, action: "login", document_id: null, document_name: null, outcome: "denied", hash: "hash-1", prev_hash: "GENESIS" },
];

test("captureActivityFilters trims text and turns local datetime inputs into timezone-aware API values", () => {
  const applied = captureActivityFilters({ ...filters, user_search: " actor@example.com " });
  assert.equal(applied.user_search, "actor@example.com");
  assert.match(applied.start_at, /Z$/);
  assert.equal(applied.action, "edit");
});

test("activity export fetches every matching page with the same filters and no duplicate records", async () => {
  const requests = [];
  const apiRequest = async (path) => {
    requests.push(new URL(path, "http://localhost").searchParams);
    const page = Number(requests.at(-1).get("page"));
    return { items: page === 1 ? [entries[1]] : [entries[0]], total: 2, pages: 2 };
  };
  const result = await fetchAllMatchingActivity(apiRequest, filters, 1);
  assert.deepEqual(result.map((entry) => entry.id), [1, 2]);
  assert.equal(requests.length, 2);
  for (const request of requests) {
    assert.equal(request.get("user_search"), filters.user_search);
    assert.equal(request.get("action"), filters.action);
    assert.equal(request.get("document_search"), filters.document_search);
    assert.equal(request.get("outcome"), filters.outcome);
    assert.equal(request.get("start_at"), filters.start_at);
    assert.equal(request.get("end_at"), filters.end_at);
  }
});

test("activity exports include all fields, applied filters, count and safe missing-data fallbacks", () => {
  const txt = buildActivityExport("txt", entries, { filters, generatedAt: "2026-06-01T10:00:00Z" });
  const markedEntries = [{ ...entries[0], document_name: "Quarterly | Report\nInjected" }, entries[1]];
  const markdown = buildActivityExport("md", markedEntries, { filters, generatedAt: "2026-06-01T10:00:00Z" });
  assert.match(txt, /Exported records: 2/);
  assert.match(txt, /Applied filters: user=actor@example.com; action=edit/);
  assert.match(txt, /User: System/);
  assert.match(txt, /Document: N\/A/);
  assert.match(txt, /Action: edit/);
  assert.match(txt, /Outcome: success/);
  assert.match(markdown, /\*\*Exported records:\*\* 2/);
  assert.match(markdown, /Quarterly \\| Report Injected/);
  assert.match(markdown, /Previous hash: hash\\-1/);
});

test("activity export fetch returns empty data and rejects incomplete or duplicated pagination", async () => {
  const empty = await fetchAllMatchingActivity(async () => ({ items: [], total: 0, pages: 0 }), filters);
  assert.deepEqual(empty, []);
  await assert.rejects(
    fetchAllMatchingActivity(async () => ({ items: [{ id: 1 }], total: 2, pages: 2 }), filters, 1),
    /changed during export/,
  );
});

test("activity filenames are type-specific and date-safe", () => {
  assert.equal(activityExportFilename("txt", "2026-11-08T10:00:00Z"), "trustvault-activity-txt-2026-11-08.txt");
  assert.equal(activityExportFilename("md", "2026-11-08T10:00:00Z"), "trustvault-activity-md-2026-11-08.md");
});
