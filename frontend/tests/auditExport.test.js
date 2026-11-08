import assert from "node:assert/strict";
import test from "node:test";

import {
  auditExportFilename,
  buildAuditExport,
  captureAuditFilters,
  fetchAllMatchingAuditEntries,
} from "../src/auditExport.js";

const filters = { action: "edit", result: "allowed", search: "A&B" };
const entries = [
  {
    id: 2,
    timestamp: "2026-11-08T10:02:00Z",
    user_id: 7,
    actor_name: "A|B\nRoot",
    actor_email: "user@example.test",
    action: "edit",
    document_id: 12,
    document_name: "memo | <draft>.txt",
    result: "allowed",
  },
  {
    id: 1,
    timestamp: "2026-11-08T10:01:00Z",
    user_id: 7,
    actor_name: "A|B\nRoot",
    actor_email: "user@example.test",
    action: "edit",
    document_id: 12,
    document_name: "memo | <draft>.txt",
    result: "allowed",
  },
];

test("TXT export includes metadata and chronologically separated records", () => {
  const report = buildAuditExport("txt", entries, {
    filters,
    auditIntegrity: { ok: true, events_checked: 2, verified_at: "2026-11-08T10:03:00Z" },
    generatedAt: "2026-11-08T10:04:00Z",
  });
  assert.match(report, /Scope: All 2 records matching the applied filters/);
  assert.match(report, /Filters: action=edit; result=allowed; search="A&B"/);
  assert.match(report, /Last audit-chain verification: Valid; 2 events checked/);
  assert.ok(report.indexOf("Event ID: 1") < report.indexOf("Event ID: 2"));
  assert.match(report, /Document: memo \| <draft>\.txt \(ID 12\)/);
});

test("TXT filter metadata replaces newline and control characters with spaces", () => {
  const unsafeFilters = {
    action: "edit\nScope: injected",
    result: "allowed\r\nLast audit-chain verification: Failed",
    search: "invoice\nEvent ID: 900\tInjected line",
  };
  const report = buildAuditExport("txt", [], {
    filters: unsafeFilters,
    auditIntegrity: null,
    generatedAt: "2026-11-08T10:04:00Z",
  });

  assert.match(report, /Filters: action=edit Scope: injected; result=allowed Last audit-chain verification: Failed; search="invoice Event ID: 900 Injected line"/);
  assert.equal((report.match(/^Scope:/gm) || []).length, 1);
  assert.equal((report.match(/^Last audit-chain verification:/gm) || []).length, 1);
  assert.doesNotMatch(report, /^Injected line$/m);
});

test("Markdown export escapes table characters, markup and newlines", () => {
  const report = buildAuditExport("md", entries.slice(0, 1), {
    filters,
    auditIntegrity: null,
    generatedAt: "2026-11-08T10:04:00Z",
  });
  assert.match(report, /A\\\|B Root/);
  assert.match(report, /memo \\| &lt;draft&gt;\.txt/);
  assert.match(report, /Not verified in this session/);
  assert.match(report, /Scope:\*\* All 1 records/);
});

test("pagination exports every matching page with the active filters", async () => {
  const requested = [];
  const apiRequest = async (path) => {
    requested.push(path);
    const params = new URLSearchParams(path.split("?")[1]);
    const page = Number(params.get("page"));
    return {
      page,
      total: 3,
      pages: 2,
      items: page === 1 ? entries : [{ ...entries[0], id: 3, timestamp: "2026-11-08T10:03:00Z" }],
    };
  };
  const result = await fetchAllMatchingAuditEntries(apiRequest, filters, 2);
  assert.equal(result.length, 3);
  assert.equal(requested.length, 2);
  for (const path of requested) {
    const params = new URLSearchParams(path.split("?")[1]);
    assert.equal(params.get("action"), "edit");
    assert.equal(params.get("result"), "allowed");
    assert.equal(params.get("search"), "A&B");
  }
});

test("changing selected filters does not mutate the applied export filters", async () => {
  const selected = { action: "edit", result: "allowed", search: "before apply" };
  const applied = captureAuditFilters(selected);
  selected.action = "delete";
  selected.result = "denied";
  selected.search = "changed without applying";

  const requested = [];
  const apiRequest = async (path) => {
    requested.push(path);
    return {
      page: 1,
      total: 1,
      pages: 1,
      items: [entries[0]],
    };
  };
  const result = await fetchAllMatchingAuditEntries(apiRequest, applied);
  const report = buildAuditExport("md", result, {
    filters: applied,
    auditIntegrity: null,
    generatedAt: "2026-11-08T10:04:00Z",
  });

  const params = new URLSearchParams(requested[0].split("?")[1]);
  assert.equal(params.get("action"), "edit");
  assert.equal(params.get("result"), "allowed");
  assert.equal(params.get("search"), "before apply");
  assert.match(report, /search="before apply"/);
  assert.doesNotMatch(report, /changed without applying/);
});

test("empty filters return no records, while authorization errors propagate", async () => {
  const empty = await fetchAllMatchingAuditEntries(async () => ({ items: [], total: 0, pages: 0 }), filters);
  assert.deepEqual(empty, []);
  await assert.rejects(
    fetchAllMatchingAuditEntries(async () => { throw new Error("Forbidden"); }, filters),
    /Forbidden/,
  );
});

test("export filenames are type-specific and date-safe", () => {
  assert.equal(auditExportFilename("txt", "2026-11-08T10:00:00Z"), "trustvault-audit-txt-2026-11-08.txt");
  assert.equal(auditExportFilename("md", "2026-11-08T10:00:00Z"), "trustvault-audit-md-2026-11-08.md");
});
