function safeText(value) {
  if (value === null || value === undefined || value === "") return "Not provided";
  return Array.from(String(value), (character) => {
    const code = character.charCodeAt(0);
    return code < 32 || code === 127 ? " " : character;
  }).join("").replace(/ {2,}/g, " ").trim() || "Not provided";
}

function escapeMarkdown(value) {
  return safeText(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\\/g, "\\\\")
    .replaceAll("[", "\\[")
    .replaceAll("]", "\\]")
    .replace(/\r\n?|\n/g, "<br>")
    .replace(/([`*_{}()#+.!|~-])/g, "\\$1");
}

function timestamp(value) {
  if (value === null || value === undefined || value === "") return "Not provided";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? safeText(value) : parsed.toISOString();
}

function chronological(events) {
  return [...events].sort((left, right) => {
    const leftTime = Date.parse(left.timestamp);
    const rightTime = Date.parse(right.timestamp);
    if (Number.isFinite(leftTime) && Number.isFinite(rightTime) && leftTime !== rightTime) {
      return leftTime - rightTime;
    }
    return Number(left.id || 0) - Number(right.id || 0);
  });
}

function actorLabel(event) {
  const parts = [];
  if (event.actor_name) parts.push(safeText(event.actor_name));
  if (event.actor_email && event.actor_email !== event.actor_name) {
    parts.push(safeText(event.actor_email));
  }
  if (event.user_id !== null && event.user_id !== undefined) {
    parts.push(`User ID ${safeText(event.user_id)}`);
  }
  return parts.join(" / ") || "Not provided";
}

function documentLabel(event) {
  if (event.document_name && event.document_id !== null && event.document_id !== undefined) {
    return `${safeText(event.document_name)} (ID ${safeText(event.document_id)})`;
  }
  if (event.document_name) return safeText(event.document_name);
  if (event.document_id !== null && event.document_id !== undefined) {
    return `Document ID ${safeText(event.document_id)}`;
  }
  return "No document reference";
}

function filterLabel(filters) {
  return [
    `action=${safeText(filters.action || "All")}`,
    `result=${safeText(filters.result || "All")}`,
    `search=${filters.search ? `"${safeText(filters.search)}"` : "All"}`,
  ].join("; ");
}

export function captureAuditFilters({ action, result, search }) {
  return {
    action: action || "",
    result: result || "",
    search: search.trim(),
  };
}

function verificationLabel(auditIntegrity) {
  if (!auditIntegrity || typeof auditIntegrity.ok !== "boolean") {
    return "Not verified in this session";
  }
  const status = auditIntegrity.ok ? "Valid" : "Failed";
  const checked = Number.isFinite(auditIntegrity.events_checked)
    ? `; ${auditIntegrity.events_checked} events checked`
    : "";
  const verifiedAt = auditIntegrity.verified_at
    ? ` at ${timestamp(auditIntegrity.verified_at)}`
    : "";
  return `${status}${checked}${verifiedAt}`;
}

export async function fetchAllMatchingAuditEntries(apiRequest, filters, limit = 100) {
  const requestPage = async (page) => {
    const params = new URLSearchParams({ page: String(page), limit: String(limit) });
    if (filters.action) params.set("action", filters.action);
    if (filters.result) params.set("result", filters.result);
    if (filters.search) params.set("search", filters.search);
    return apiRequest(`/admin/audit?${params}`);
  };

  const firstPage = await requestPage(1);
  const total = Number(firstPage.total);
  const pages = Number(firstPage.pages);
  const expectedPages = total === 0 ? 0 : Math.ceil(total / limit);
  if (
    !Array.isArray(firstPage.items) || !Number.isSafeInteger(total) || total < 0 ||
    !Number.isSafeInteger(pages) || pages !== expectedPages
  ) {
    throw new Error("The audit service returned incomplete pagination data.");
  }
  if (total === 0) return [];

  const entries = [...firstPage.items];
  const ids = new Set(entries.map((entry) => entry.id));
  for (let page = 2; page <= pages; page += 1) {
    const response = await requestPage(page);
    if (
      !Array.isArray(response.items) || Number(response.total) !== total ||
      Number(response.pages) !== pages
    ) {
      throw new Error("Audit records changed during export. Please retry.");
    }
    for (const entry of response.items) {
      if (ids.has(entry.id)) {
        throw new Error("Audit records changed during export. Please retry.");
      }
      ids.add(entry.id);
      entries.push(entry);
    }
  }
  if (entries.length !== total) {
    throw new Error("Audit records changed during export. Please retry.");
  }
  return chronological(entries);
}

export function buildAuditExport(format, entries, { filters, auditIntegrity, generatedAt }) {
  const generated = timestamp(generatedAt);
  const sortedEntries = chronological(entries);
  const verification = verificationLabel(auditIntegrity);
  if (format === "txt") {
    const lines = [
      "TrustVault Security & Audit Center — Audit Log Export",
      `Generated: ${generated}`,
      `Scope: All ${sortedEntries.length} records matching the applied filters (not only the current page).`,
      `Filters: ${filterLabel(filters)}`,
      `Last audit-chain verification: ${verification}`,
      "Events are listed in chronological order.",
      "",
    ];
    for (const event of sortedEntries) {
      lines.push(
        "============================================================",
        `Event ID: ${safeText(event.id)}`,
        `Timestamp: ${timestamp(event.timestamp)}`,
        `Actor: ${actorLabel(event)}`,
        `Action: ${safeText(event.action)}`,
        `Document: ${documentLabel(event)}`,
        `Outcome: ${safeText(event.result)}`,
        "",
      );
    }
    return lines.join("\n");
  }

  if (format === "md") {
    const lines = [
      "# TrustVault Security & Audit Center — Audit Log Export",
      "",
      `- **Generated:** ${escapeMarkdown(generated)}`,
      `- **Scope:** All ${sortedEntries.length} records matching the applied filters (not only the current page).`,
      `- **Filters:** ${escapeMarkdown(filterLabel(filters))}`,
      `- **Last audit-chain verification:** ${escapeMarkdown(verification)}`,
      "- **Order:** Chronological",
      "",
      "## Events",
      "",
    ];
    for (const event of sortedEntries) {
      lines.push(
        `### Event ${escapeMarkdown(event.id)}`,
        `- **Timestamp:** ${escapeMarkdown(timestamp(event.timestamp))}`,
        `- **Actor:** ${escapeMarkdown(actorLabel(event))}`,
        `- **Action:** ${escapeMarkdown(event.action)}`,
        `- **Document:** ${escapeMarkdown(documentLabel(event))}`,
        `- **Outcome:** ${escapeMarkdown(event.result)}`,
        "",
      );
    }
    return lines.join("\n");
  }
  throw new Error("Unsupported audit export format.");
}

export function auditExportFilename(format, generatedAt = new Date()) {
  if (format !== "txt" && format !== "md") {
    throw new Error("Unsupported audit export format.");
  }
  const date = new Date(generatedAt).toISOString().slice(0, 10);
  return `trustvault-audit-${format}-${date}.${format}`;
}
