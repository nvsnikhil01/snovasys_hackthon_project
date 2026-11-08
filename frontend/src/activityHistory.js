function safeText(value, fallback = "N/A") {
  if (value === null || value === undefined || value === "") return fallback;
  return Array.from(String(value), (character) => {
    const code = character.charCodeAt(0);
    return code < 32 || code === 127 ? " " : character;
  }).join("").replace(/ {2,}/g, " ").trim() || fallback;
}

function escapeMarkdown(value) {
  return safeText(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\\/g, "\\\\")
    .replace(/([`*_{}()[\]#+.!|~-])/g, "\\$1");
}

function formatTimestamp(value) {
  if (!value) return "N/A";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? safeText(value) : parsed.toISOString();
}

function chronological(entries) {
  return [...entries].sort((left, right) => {
    const leftTimestamp = Date.parse(left.timestamp);
    const rightTimestamp = Date.parse(right.timestamp);
    if (Number.isFinite(leftTimestamp) && Number.isFinite(rightTimestamp) && leftTimestamp !== rightTimestamp) {
      return leftTimestamp - rightTimestamp;
    }
    return Number(left.id || 0) - Number(right.id || 0);
  });
}

export function captureActivityFilters(filters) {
  return {
    user_search: filters.user_search.trim(),
    action: filters.action,
    document_search: filters.document_search.trim(),
    outcome: filters.outcome,
    start_at: filters.start_at ? new Date(filters.start_at).toISOString() : "",
    end_at: filters.end_at ? new Date(filters.end_at).toISOString() : "",
  };
}

export function activityHistoryEndpoint(role) {
  return role === "admin" || role === "auditor" ? "/admin/activity" : "/auth/activity";
}

export async function fetchAllMatchingActivity(apiRequest, filters, limit = 100, endpoint = "/admin/activity") {
  const requestPage = async (page) => {
    const params = new URLSearchParams({ page: String(page), limit: String(limit) });
    for (const [key, value] of Object.entries(filters)) {
      if (value) params.set(key, value);
    }
    return apiRequest(`${endpoint}?${params}`);
  };

  const firstPage = await requestPage(1);
  const total = Number(firstPage.total);
  const pages = Number(firstPage.pages);
  const expectedPages = total === 0 ? 0 : Math.ceil(total / limit);
  if (!Array.isArray(firstPage.items) || !Number.isSafeInteger(total) || total < 0 || pages !== expectedPages) {
    throw new Error("The activity service returned incomplete pagination data.");
  }
  if (total === 0) return [];

  const entries = [...firstPage.items];
  const ids = new Set(entries.map((entry) => entry.id));
  for (let page = 2; page <= pages; page += 1) {
    const response = await requestPage(page);
    if (!Array.isArray(response.items) || Number(response.total) !== total || Number(response.pages) !== pages) {
      throw new Error("Activity records changed during export. Please retry.");
    }
    for (const entry of response.items) {
      if (ids.has(entry.id)) throw new Error("Activity records changed during export. Please retry.");
      ids.add(entry.id);
      entries.push(entry);
    }
  }
  if (entries.length !== total) throw new Error("Activity records changed during export. Please retry.");
  return chronological(entries);
}

function actorLabel(event) {
  const email = safeText(event.actor_email, "");
  const userId = event.user_id === null || event.user_id === undefined ? "" : `ID ${safeText(event.user_id)}`;
  return [email, userId].filter(Boolean).join(" / ") || "System";
}

function documentLabel(event) {
  const name = safeText(event.document_name, "");
  const id = event.document_id === null || event.document_id === undefined ? "" : `ID ${safeText(event.document_id)}`;
  return [name, id].filter(Boolean).join(" / ") || "N/A";
}

function detailsLabel(event) {
  const details = [];
  if (event.prev_hash) details.push(`Previous hash: ${safeText(event.prev_hash)}`);
  if (event.hash) details.push(`Hash: ${safeText(event.hash)}`);
  return details.join("; ") || "N/A";
}

function filterLabel(filters) {
  const localDate = (value) => value ? formatTimestamp(value) : "All";
  return [
    `user=${safeText(filters.user_search, "All")}`,
    `action=${safeText(filters.action, "All")}`,
    `document=${safeText(filters.document_search, "All")}`,
    `outcome=${safeText(filters.outcome, "All")}`,
    `start=${localDate(filters.start_at)}`,
    `end=${localDate(filters.end_at)}`,
  ].join("; ");
}

export function buildActivityExport(format, entries, { filters, generatedAt }) {
  const records = chronological(entries);
  const generated = formatTimestamp(generatedAt);
  if (format === "txt") {
    const lines = [
      "TrustVault Activity History Export",
      `Generated: ${generated}`,
      `Exported records: ${records.length}`,
      "Scope: All records matching the applied filters (not only the current page).",
      `Applied filters: ${filterLabel(filters)}`,
      "Events are listed in chronological order.",
      "",
    ];
    for (const event of records) {
      lines.push(
        "============================================================",
        `ID: ${safeText(event.id)}`,
        `User: ${actorLabel(event)}`,
        `Action: ${safeText(event.action)}`,
        `Document: ${documentLabel(event)}`,
        `Timestamp: ${formatTimestamp(event.timestamp)}`,
        `Outcome: ${safeText(event.outcome)}`,
        `Details: ${detailsLabel(event)}`,
        "",
      );
    }
    return lines.join("\n");
  }
  if (format === "md") {
    const lines = [
      "# TrustVault Activity History Export",
      "",
      `- **Generated:** ${escapeMarkdown(generated)}`,
      `- **Exported records:** ${records.length}`,
      "- **Scope:** All records matching the applied filters (not only the current page).",
      `- **Applied filters:** ${escapeMarkdown(filterLabel(filters))}`,
      "- **Order:** Chronological",
      "",
    ];
    for (const event of records) {
      lines.push(
        `## Event ${escapeMarkdown(event.id)}`,
        `- **User:** ${escapeMarkdown(actorLabel(event))}`,
        `- **Action:** ${escapeMarkdown(event.action)}`,
        `- **Document:** ${escapeMarkdown(documentLabel(event))}`,
        `- **Timestamp:** ${escapeMarkdown(formatTimestamp(event.timestamp))}`,
        `- **Outcome:** ${escapeMarkdown(event.outcome)}`,
        `- **Details:** ${escapeMarkdown(detailsLabel(event))}`,
        "",
      );
    }
    return lines.join("\n");
  }
  throw new Error("Unsupported activity export format.");
}

export function activityExportFilename(format, generatedAt = new Date()) {
  if (format !== "txt" && format !== "md") throw new Error("Unsupported activity export format.");
  const date = new Date(generatedAt).toISOString().slice(0, 10);
  return `trustvault-activity-${format}-${date}.${format}`;
}
