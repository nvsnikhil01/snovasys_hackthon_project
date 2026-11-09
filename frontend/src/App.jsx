import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiRequest, apiUrl, downloadFile, getToken, setToken, clearToken } from "./api";
import { auditExportFilename, buildAuditExport, captureAuditFilters, fetchAllMatchingAuditEntries } from "./auditExport";
import { activityExportFilename, activityHistoryEndpoint, buildActivityExport, captureActivityFilters, fetchAllMatchingActivity } from "./activityHistory";
import { AuthSubmitButton } from "./AuthSubmitButton.js";
import "./App.css";

function Shield() { return <svg className="shield" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3 19 6v5.2c0 4.7-3 7.8-7 9.8-4-2-7-5.1-7-9.8V6l7-3Z" stroke="currentColor" strokeWidth="1.7"/><path d="m9 12 2 2 4-4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>; }
const date = (v) => new Date(v).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
const size = (v) => v < 1048576 ? `${(v / 1024).toFixed(1)} KB` : `${(v / 1048576).toFixed(1)} MB`;

const actionIcons = { login: "\u21aa", upload: "\u2191", download: "\u2193", read: "\u25c9", edit: "\u270e", delete: "\u232b", grant_access: "\u21e2", share: "\u21e2", revoke_access: "\u2298", revoke: "\u2298" };
function ActivityTable({ entries, onDetails }) {
  return <table className="data-table audit-table"><thead><tr><th>Timestamp</th><th>Actor Name / Email</th><th>Action</th><th>Document Name &amp; ID</th><th>Result</th><th>Details</th></tr></thead><tbody>{entries.flatMap((entry, index) => {
    const dateLabel = new Date(entry.timestamp).toLocaleDateString(undefined, { weekday: "long", year: "numeric", month: "long", day: "numeric" });
    const previousDate = index ? new Date(entries[index - 1].timestamp).toLocaleDateString(undefined, { weekday: "long", year: "numeric", month: "long", day: "numeric" }) : "";
    const group = dateLabel !== previousDate;
    return [ ...(group ? [<tr className="audit-date-group" key={`date-${entry.id}`}><th colSpan="6">{dateLabel}</th></tr>] : []), <tr key={entry.id}><td>{new Date(entry.timestamp).toLocaleTimeString()}</td><td><b>{entry.actor_name || "System"}</b><small>{entry.actor_email || (entry.user_id ? `User #${entry.user_id}` : "System event")}</small></td><td><span className={`action-badge action-${entry.action}`}><i>{actionIcons[entry.action] || "\u2022"}</i>{entry.action.replaceAll("_", " ")}</span></td><td>{entry.document_name || "\u2014"}<small>{entry.document_id ? `ID ${entry.document_id}` : "No document"}</small></td><td><span className={`result-badge result-${entry.result}`}>{entry.result}</span></td><td><button className="button button-quiet button-sm" onClick={() => onDetails(entry)}>Details</button></td></tr> ];
  })}</tbody></table>;
}

function ActivityHistoryTable({ entries, onDetails }) {
  const timestampOptions = { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false };
  return <div className="activity-table-wrap"><table className="data-table activity-table"><thead><tr><th>ID</th><th>User</th><th>Action</th><th>Document</th><th>Timestamp</th><th>Outcome</th><th>Details</th></tr></thead><tbody>{entries.map((entry) => {
    const actor = entry.actor_email || (entry.user_id !== null && entry.user_id !== undefined ? `User #${entry.user_id}` : "System");
    const document = entry.document_name || "N/A";
    const outcome = entry.outcome || "N/A";
    const outcomeLabel = { success: "Success", denied: "Denied", failure: "Failure" }[outcome] || outcome;
    const action = entry.action === "login" ? `Login ${outcome === "success" ? "success" : outcome === "denied" || outcome === "failure" ? "failure" : ""}`.trim() : (entry.action || "N/A").replaceAll("_", " ");
    return <tr key={entry.id}><td>#{entry.id}</td><td>{actor}<small>{entry.user_id !== null && entry.user_id !== undefined ? `ID ${entry.user_id}` : "System event"}</small></td><td><span className={`action-badge action-${entry.action || "unknown"}`}>{action}</span></td><td>{document}<small>{entry.document_id !== null && entry.document_id !== undefined ? `ID ${entry.document_id}` : "No document reference"}</small></td><td>{entry.timestamp ? new Date(entry.timestamp).toLocaleString(undefined, timestampOptions) : "N/A"}</td><td><span className={`result-badge result-${outcome}`}>{outcomeLabel}</span></td><td><button className="button button-quiet button-sm" onClick={() => onDetails(entry)}>Details</button></td></tr>;
  })}</tbody></table></div>;
}

function RegisteredUsersTable({ registeredUsers, user, deletingUserId, onDelete }) {
  return <div className="table-scroll"><table className="data-table users-table"><thead><tr><th>ID</th><th>Email</th><th>Role</th><th>Actions</th></tr></thead><tbody>
    {registeredUsers === null ? <tr><td colSpan="4">Loading users…</td></tr> : registeredUsers.length === 0 ? <tr><td colSpan="4">No registered users.</td></tr> : registeredUsers.map((account) => <tr key={account.id}><td>{account.id}</td><td>{account.email}</td><td>{account.role}</td><td>{user.role === "admin" && <button className="button button-danger button-sm" disabled={deletingUserId !== null || account.id === user.id} title={account.id === user.id ? "You cannot delete your own account" : undefined} onClick={() => onDelete(account)}>{deletingUserId === account.id ? "Deleting…" : "Delete user"}</button>}</td></tr>)}
  </tbody></table></div>;
}

export default function App() {
  const [user, setUser] = useState(null), [authMode, setAuthMode] = useState("login");
  const [email, setEmail] = useState(""), [password, setPassword] = useState(""), [confirmPassword, setConfirmPassword] = useState("");
  const [documents, setDocuments] = useState([]), [sharedDocuments, setSharedDocuments] = useState([]);
  const [sharedDocsLoaded, setSharedDocsLoaded] = useState(false), [activeTab, setActiveTab] = useState("my-docs");
  const [error, setError] = useState(""), [uploading, setUploading] = useState(false);
  const [authLoading, setAuthLoading] = useState(false), authRequestRef = useRef(false);
  const [deletingUserId, setDeletingUserId] = useState(null);
  const [page, setPage] = useState("documents"), [uploadFile, setUploadFile] = useState(null), [query, setQuery] = useState("");
  const [shareDocId, setShareDocId] = useState(null), [shareEmail, setShareEmail] = useState("");
  const [shareLevel, setShareLevel] = useState("read"), [shares, setShares] = useState([]), [sharesLoading, setSharesLoading] = useState(false), [sharing, setSharing] = useState(false);
  const [registeredUsers, setRegisteredUsers] = useState(null), [auditEntries, setAuditEntries] = useState(null), [auditIntegrity, setAuditIntegrity] = useState(null);
  const [auditPage, setAuditPage] = useState(1), [auditTotal, setAuditTotal] = useState(0), [auditSummary, setAuditSummary] = useState({ total_events: 0, allowed_count: 0, denied_count: 0 });
  const [auditAction, setAuditAction] = useState(""), [auditResult, setAuditResult] = useState(""), [auditSearch, setAuditSearch] = useState(""), [selectedAudit, setSelectedAudit] = useState(null);
  const [appliedAuditFilters, setAppliedAuditFilters] = useState({ action: "", result: "", search: "" });
  const [auditExporting, setAuditExporting] = useState(false);
  const [activityEntries, setActivityEntries] = useState(null), [activityPage, setActivityPage] = useState(1), [activityTotal, setActivityTotal] = useState(0), [activityExporting, setActivityExporting] = useState(false);
  const [activityFilters, setActivityFilters] = useState({ user_search: "", action: "", document_search: "", outcome: "", start_at: "", end_at: "" });
  const [appliedActivityFilters, setAppliedActivityFilters] = useState({ user_search: "", action: "", document_search: "", outcome: "", start_at: "", end_at: "" });
  const activityEndpoint = activityHistoryEndpoint(user?.role);

  const fetchUser = useCallback(async () => {
    try { const u = await apiRequest("/auth/me"); setUser(u); setDocuments(await apiRequest("/documents")); }
    catch { clearToken(); setUser(null); }
  }, []);
  // Fetch initial session data after mount; state updates happen after the requests resolve.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { if (getToken()) fetchUser(); }, [fetchUser]);
  useEffect(() => { if (Number.isInteger(shareDocId)) loadShares(shareDocId); }, [shareDocId]);

  async function loadAuditPage(page = auditPage, filters = appliedAuditFilters) {
    try {
      const params = new URLSearchParams({ page: String(page), limit: "20" });
      if (filters.action) params.set("action", filters.action);
      if (filters.result) params.set("result", filters.result);
      if (filters.search) params.set("search", filters.search);
      const data = await apiRequest(`/admin/audit?${params}`);
      setAuditEntries(data.items); setAuditTotal(data.total); setAuditPage(data.page);
      setAppliedAuditFilters(filters);
      setAuditSummary({ total_events: data.total_events, allowed_count: data.allowed_count, denied_count: data.denied_count });
    } catch (err) { setError(err.message); }
  }
  async function verifyAudit() {
    try { setAuditIntegrity(await apiRequest("/admin/audit/verify")); }
    catch (err) { setError(err.message); }
  }
  async function loadActivityPage(page = activityPage, filters = appliedActivityFilters) {
    try {
      const requestFilters = activityEndpoint === "/auth/activity" ? { ...filters, user_search: "" } : filters;
      const params = new URLSearchParams({ page: String(page), limit: "25" });
      for (const [key, value] of Object.entries(requestFilters)) if (value) params.set(key, value);
      const data = await apiRequest(`${activityEndpoint}?${params}`);
      setActivityEntries(data.items); setActivityTotal(data.total); setActivityPage(data.page);
      setAppliedActivityFilters(requestFilters);
    } catch (err) { setError(err.message); }
  }
  async function downloadActivity(format) {
    if (activityExporting) return;
    setActivityExporting(true);
    setError("");
    try {
      const filters = activityEndpoint === "/auth/activity"
        ? { ...appliedActivityFilters, user_search: "" }
        : { ...appliedActivityFilters };
      const entries = await fetchAllMatchingActivity(apiRequest, filters, 100, activityEndpoint);
      if (entries.length === 0) {
        setError("No activity records match the applied filters.");
        return;
      }
      const generatedAt = new Date();
      const content = buildActivityExport(format, entries, { filters, generatedAt });
      const markdown = format === "md";
      const blob = new Blob([content], { type: markdown ? "text/markdown;charset=utf-8" : "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = activityExportFilename(format, generatedAt);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (err) {
      setError(`Activity export failed: ${err.message}`);
    } finally {
      setActivityExporting(false);
    }
  }
  async function downloadAudit(format) {
    if (auditExporting) return;
    setAuditExporting(true);
    setError("");
    try {
      const filters = { ...appliedAuditFilters };
      const entries = await fetchAllMatchingAuditEntries(apiRequest, filters);
      if (entries.length === 0) {
        setError("No audit records match the applied filters.");
        return;
      }
      const generatedAt = new Date();
      const content = buildAuditExport(format, entries, { filters, auditIntegrity, generatedAt });
      const markdown = format === "md";
      const blob = new Blob([content], { type: markdown ? "text/markdown;charset=utf-8" : "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = auditExportFilename(format, generatedAt);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (err) {
      setError(`Audit export failed: ${err.message}`);
    } finally {
      setAuditExporting(false);
    }
  }
  async function loadDocs() { try { setDocuments(await apiRequest("/documents")); } catch (err) { setError(err.message); } }
  async function loadSharedDocs() { try { setSharedDocuments(await apiRequest("/documents/shared-with-me")); setSharedDocsLoaded(true); } catch (err) { setError(err.message); } }
  async function loadShares(id) {
    setSharesLoading(true);
    try { setShares(await apiRequest(`/documents/${id}/shares`)); } catch (err) { setError(err.message); }
    finally { setSharesLoading(false); }
  }
  async function handleAuth(e) {
    e.preventDefault(); setError("");
    if (authRequestRef.current) return;
    if (authMode === "register" && password !== confirmPassword) { setError("Passwords do not match"); return; }
    authRequestRef.current = true;
    setAuthLoading(true);
    try {
      if (authMode === "register") await apiRequest("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) });
      const data = await apiRequest("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
      setToken(data.access_token); setEmail(""); setPassword(""); setConfirmPassword(""); await fetchUser();
    } catch (err) { setError(err.message); }
    finally { authRequestRef.current = false; setAuthLoading(false); }
  }
  async function handleUpload(e) {
    e.preventDefault();
    if (!uploadFile) return;
    setUploading(true); setError("");
    const formData = new FormData(); formData.append("file", uploadFile);
    try { await apiRequest("/documents", { method: "POST", body: formData }); await loadDocs(); setUploadFile(null); setPage("documents"); }
    catch (err) { setError(err.message); }
    finally { setUploading(false); }
  }
  async function handleDelete(id) {
    if (!confirm("Are you sure you want to delete this document?")) return;
    try { await apiRequest(`/documents/${id}`, { method: "DELETE" }); setDocuments((items) => items.filter((d) => d.id !== id)); setSharedDocuments((items) => items.filter((d) => d.id !== id)); }
    catch (err) { setError(err.message); }
  }
  async function openRegisteredUsers() {
    setPage("documents"); setActiveTab("users"); setError("");
    try { setRegisteredUsers(await apiRequest("/admin/users")); }
    catch (err) { setError(err.message); }
  }
  async function handleDeleteUser(target) {
    if (target.id === user.id) { setError("You cannot delete your own account"); return; }
    if (!confirm(`Permanently delete ${target.email}? Their documents will be transferred to your account.`)) return;
    setError(""); setDeletingUserId(target.id);
    try {
      await apiRequest(`/admin/users/${target.id}`, { method: "DELETE" });
      setRegisteredUsers((items) => (items || []).filter((item) => item.id !== target.id));
    } catch (err) { setError(err.message); }
    finally { setDeletingUserId(null); }
  }
  async function handleDownload(doc) { setError(""); try { await downloadFile(doc.id, doc.filename); } catch (err) { setError(err.message); } }
  async function handleShare(e) {
    e.preventDefault(); setError(""); setSharing(true);
    try {
      if (!Number.isInteger(shareDocId)) throw new Error("Select a document to share");
      const response = await fetch(apiUrl(`/documents/${shareDocId}/share`), {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ user_email: shareEmail, level: shareLevel }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Failed to share document");
      setShareEmail(""); await loadShares(shareDocId);
    } catch (err) { setError(err.message); }
    finally { setSharing(false); }
  }
  async function revoke(userId) {
    try { await apiRequest(`/documents/${shareDocId}/share/${userId}`, { method: "DELETE" }); setShares((items) => items.filter((g) => g.user_id !== userId)); }
    catch (err) { setError(err.message); }
  }
  function logout() { clearToken(); setUser(null); setDocuments([]); setSharedDocuments([]); setSharedDocsLoaded(false); setActivityEntries(null); setActiveTab("my-docs"); setPage("documents"); }
  const list = activeTab === "my-docs" ? documents : sharedDocuments;
  const filtered = useMemo(() => list.filter((d) => d.filename.toLowerCase().includes(query.trim().toLowerCase())), [list, query]);
  const searchResults = useMemo(() => [...documents, ...sharedDocuments].filter((d) => d.filename.toLowerCase().includes(query.trim().toLowerCase())), [documents, sharedDocuments, query]);

  if (!user) return <main className="auth-shell"><section className="auth-card">
    <div className="auth-brand"><span className="vault-mark"><Shield /></span><span className="eyebrow">PRIVATE FILES. PROTECTED.</span><h1>TrustVault</h1><p>Your secure workspace for important documents.</p></div>
    {error && <div className="alert" role="alert">{error}</div>}
    <form className="auth-form" onSubmit={handleAuth}>
      <label className="field"><span>Email address</span><input type="email" autoComplete="email" placeholder="you@example.com" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
      <label className="field"><span>Password</span><input type="password" autoComplete={authMode === "login" ? "current-password" : "new-password"} placeholder="At least 8 characters" required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
      {authMode === "register" && <label className="field"><span>Confirm Password</span><input type="password" autoComplete="new-password" required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} /></label>}<AuthSubmitButton loading={authLoading} mode={authMode} />
    </form>
    <p className="auth-switch">{authMode === "login" ? "New to TrustVault?" : "Already have an account?"} <button className="text-button" disabled={authLoading} onClick={() => { setAuthMode(authMode === "login" ? "register" : "login"); setError(""); }}>{authMode === "login" ? "Create an account" : "I already have an account"}</button></p>
  </section></main>;

  return <div className="app-shell workspace-layout">
    <aside className="sidebar">
      <a className="brand" href="#" onClick={(e) => { e.preventDefault(); setPage("documents"); setActiveTab("my-docs"); }}><span className="brand-icon"><Shield /></span><span>Trust<span className="gold">Vault</span></span></a>
      <nav className="sidebar-nav" aria-label="Workspace navigation">
        <span className="sidebar-label">WORKSPACE</span>
        <button type="button" className={`sidebar-link ${page === "documents" && activeTab === "my-docs" ? "active" : ""}`} aria-current={page === "documents" && activeTab === "my-docs" ? "page" : undefined} onClick={() => { setPage("documents"); setActiveTab("my-docs"); }}>My Documents</button>
        <button type="button" className={`sidebar-link ${page === "documents" && activeTab === "shared-with-me" ? "active" : ""}`} aria-current={page === "documents" && activeTab === "shared-with-me" ? "page" : undefined} onClick={() => { setPage("documents"); setActiveTab("shared-with-me"); if (!sharedDocsLoaded) loadSharedDocs(); }}>Shared With Me</button>
        {(user.role === "admin" || user.role === "auditor") && <button type="button" className={`sidebar-link ${page === "documents" && activeTab === "users" ? "active" : ""}`} aria-current={page === "documents" && activeTab === "users" ? "page" : undefined} onClick={openRegisteredUsers}>Registered Users</button>}
        {(user.role === "admin" || user.role === "auditor") && <button type="button" className={`sidebar-link ${page === "documents" && activeTab === "security" ? "active" : ""}`} aria-current={page === "documents" && activeTab === "security" ? "page" : undefined} onClick={() => { setPage("documents"); setActiveTab("security"); loadAuditPage(1); }}>Security &amp; Audit</button>}
        <button type="button" className={`sidebar-link ${page === "activity" ? "active" : ""}`} aria-current={page === "activity" ? "page" : undefined} onClick={() => { setPage("activity"); loadActivityPage(1); }}>Activity History</button>
      </nav>
      <div className="sidebar-actions">
        <button type="button" className={`button button-secondary ${page === "search" ? "sidebar-action-active" : ""}`} onClick={() => { setPage("search"); if (!sharedDocsLoaded) loadSharedDocs(); }}>Search</button>
        <button type="button" className={`button button-primary ${page === "upload" ? "sidebar-action-active" : ""}`} onClick={() => { setUploadFile(null); setPage("upload"); }}>Upload</button>
      </div>
      <div className="sidebar-account"><span className="avatar">{user.email?.[0]?.toUpperCase()}</span><div className="sidebar-identity"><b>{user.email}</b><span>{user.role}</span></div><button type="button" className="button button-quiet button-sm" onClick={logout}>Log out</button></div>
    </aside>
    <div className="workspace-content">
    <main className="main-content">
      <div className="page-heading"><div><span className="eyebrow">TRUSTVAULT WORKSPACE</span><h1>{page === "upload" ? "Upload a document" : page === "search" ? "Search documents" : page === "activity" ? "Activity History" : activeTab === "shared-with-me" ? "Shared With Me" : activeTab === "users" ? "Registered Users" : activeTab === "security" ? "Security & Audit Center" : "My Documents"}</h1><p>Keep your important files organized and access controlled.</p></div>
        {page === "documents" && <div className="heading-actions"><button className="button button-secondary" onClick={() => { setPage("search"); if (!sharedDocsLoaded) loadSharedDocs(); }}>Search documents</button><button className="button button-primary" onClick={() => { setUploadFile(null); setPage("upload"); }}>Upload a document</button></div>}</div>
      {error && <div className="alert alert-banner" role="alert">{error}<button className="text-button" onClick={() => setError("")}>Dismiss</button></div>}

      {page === "activity" && <section className="panel activity-history"><div className="section-heading"><div><h2>{user.role === "admin" || user.role === "auditor" ? "System Activity" : "My Activity"}</h2><p>{user.role === "admin" || user.role === "auditor" ? "Review recorded events across TrustVault." : "Review activity recorded for your account."}</p></div><span className="count">{activityTotal} events</span></div><div className="activity-filters">
        {(user.role === "admin" || user.role === "auditor") && <label className="field"><span>User email or ID</span><input value={activityFilters.user_search} onChange={(e) => setActivityFilters({ ...activityFilters, user_search: e.target.value })} placeholder="Search user" /></label>}
        <label className="field"><span>Action</span><select value={activityFilters.action} onChange={(e) => setActivityFilters({ ...activityFilters, action: e.target.value })}><option value="">All actions</option>{["login", "upload", "download", "read", "edit", "delete", "grant_access", "revoke_access", "share", "revoke"].map((action) => <option key={action} value={action}>{action.replaceAll("_", " ")}</option>)}</select></label>
        <label className="field"><span>Document name or ID</span><input value={activityFilters.document_search} onChange={(e) => setActivityFilters({ ...activityFilters, document_search: e.target.value })} placeholder="Search document" /></label>
        <label className="field"><span>Outcome</span><select value={activityFilters.outcome} onChange={(e) => setActivityFilters({ ...activityFilters, outcome: e.target.value })}><option value="">All outcomes</option><option value="success">Success</option><option value="denied">Denied</option><option value="failure">Failure</option></select></label>
        <label className="field"><span>Start date and time</span><input type="datetime-local" value={activityFilters.start_at} onChange={(e) => setActivityFilters({ ...activityFilters, start_at: e.target.value })} /></label>
        <label className="field"><span>End date and time</span><input type="datetime-local" value={activityFilters.end_at} onChange={(e) => setActivityFilters({ ...activityFilters, end_at: e.target.value })} /></label>
        <div className="activity-filter-actions"><button className="button button-secondary" onClick={() => loadActivityPage(1, captureActivityFilters(activityFilters))}>Apply filters</button><button className="button button-quiet" onClick={() => { const cleared = { user_search: "", action: "", document_search: "", outcome: "", start_at: "", end_at: "" }; setActivityFilters(cleared); loadActivityPage(1, cleared); }}>Clear filters</button><button className="button button-quiet" disabled={!activityTotal || activityExporting} onClick={() => downloadActivity("txt")}>{activityExporting ? "Preparing export…" : "Export TXT"}</button><button className="button button-quiet" disabled={!activityTotal || activityExporting} onClick={() => downloadActivity("md")}>{activityExporting ? "Preparing export…" : "Export Markdown"}</button></div>
      </div>{activityEntries === null ? <p className="activity-empty">Loading activity…</p> : activityEntries.length === 0 ? <div className="empty-state activity-empty"><h3>No activity records found</h3><p>Try clearing or changing the applied filters.</p></div> : <><ActivityHistoryTable entries={activityEntries} onDetails={setSelectedAudit} /><div className="audit-pagination"><span>{activityTotal} events · Page {activityPage} of {Math.max(1, Math.ceil(activityTotal / 25))}</span><div><button className="button button-secondary button-sm" disabled={activityPage <= 1} onClick={() => loadActivityPage(activityPage - 1)}>Previous</button><button className="button button-secondary button-sm" disabled={activityPage >= Math.ceil(activityTotal / 25)} onClick={() => loadActivityPage(activityPage + 1)}>Next</button></div></div></>}</section>}

      {page === "upload" && <section className="panel upload-panel"><h2>Add a document</h2><p className="panel-subtitle">Select a file to add it to your vault.</p><form onSubmit={handleUpload}>
        <label className="dropzone"><input className="file-input" type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" onChange={(e) => setUploadFile(e.target.files?.[0] || null)} /><span className="upload-icon">↑</span><strong>{uploadFile ? uploadFile.name : "Choose a file to upload"}</strong><small>{uploadFile ? size(uploadFile.size) : "PDF, PNG, JPG or TXT · up to 5 MB"}</small><span className="button button-secondary">Browse files</span></label>
        <p className="form-note">The filename is used as the document title in this workspace.</p><div className="form-actions"><button type="button" className="button button-quiet" onClick={() => setPage("documents")}>Back</button><button className="button button-primary" type="submit" disabled={!uploadFile || uploading}>{uploading ? "Uploading…" : "Upload document"}</button></div></form></section>}

      {page === "search" && <section className="panel search-panel"><label className="field"><span>Search by filename</span><input autoFocus value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Type a filename…" /></label><p className="form-note">Searching across your documents and files shared with you.</p><div className="document-list">{searchResults.map((doc) => <article className="document-row" key={doc.id}><div className="document-details"><span className="file-mark">FILE</span><div><h3>{doc.filename}</h3><p>{size(doc.size)} · Added {date(doc.created_at)}</p></div></div><div className="document-actions"><button className="button button-secondary button-sm" onClick={() => handleDownload(doc)}>Download</button>{doc.owner_id === user.id && <><button className="button button-outline button-sm" onClick={() => setShareDocId(doc.id)}>Share</button><button className="button button-danger button-sm" onClick={() => handleDelete(doc.id)}>Delete</button></>}</div></article>)}</div>{searchResults.length === 0 && <p className="access-empty">No matching documents.</p>}<div className="form-actions"><button className="button button-quiet" onClick={() => { setQuery(""); setPage("documents"); }}>Back to documents</button></div></section>}

      {page === "documents" && <section className="documents-panel" id="document-list-panel"><div className="section-heading"><div><h2>Documents</h2><p>Manage your files and shared access.</p></div><span className="count">{list.length} files</span></div>
          <div className="tabs" role="tablist" aria-label="Dashboard sections"><button role="tab" aria-selected={activeTab === "my-docs"} className={activeTab === "my-docs" ? "tab active" : "tab"} onClick={() => setActiveTab("my-docs")}>My documents <span>{documents.length}</span></button><button role="tab" aria-selected={activeTab === "shared-with-me"} className={activeTab === "shared-with-me" ? "tab active" : "tab"} onClick={() => { setActiveTab("shared-with-me"); if (!sharedDocsLoaded) loadSharedDocs(); }}>Shared with me <span>{sharedDocuments.length}</span></button>{(user.role === "admin" || user.role === "auditor") && <button role="tab" aria-selected={activeTab === "security"} className={activeTab === "security" ? "tab active" : "tab"} onClick={() => { setActiveTab("security"); loadAuditPage(1); }}>Security &amp; Audit Center</button>}{(user.role === "admin" || user.role === "auditor") && <button role="tab" aria-selected={activeTab === "users"} className={activeTab === "users" ? "tab active" : "tab"} onClick={openRegisteredUsers}>Registered users</button>}</div>
          {activeTab === "security" ? <section className="security-center"><div className="audit-summary"><article><span>Total Audit Events</span><b>{auditSummary.total_events}</b></article><article><span>Successful Events</span><b>{auditSummary.allowed_count}</b></article><article><span>Denied Events</span><b>{auditSummary.denied_count}</b></article></div><section className="audit-integrity"><div><span className="eyebrow">AUDIT INTEGRITY</span><h3>{auditIntegrity ? (auditIntegrity.ok ? "Valid" : "Tampered") : "Not verified yet"}</h3><p>Last verification: {auditIntegrity?.verified_at ? new Date(auditIntegrity.verified_at).toLocaleString() : "\u2014"} \u00b7 Events checked: {auditIntegrity?.events_checked ?? "\u2014"}</p></div><button className="button button-primary" onClick={verifyAudit}>Verify Audit Integrity</button></section><div className="audit-toolbar"><input className="audit-filter" value={auditSearch} onChange={(e) => setAuditSearch(e.target.value)} onKeyDown={(e) => e.key === "Enter" && loadAuditPage(1, captureAuditFilters({ action: auditAction, result: auditResult, search: auditSearch }))} placeholder="Search actor or document" aria-label="Search actor or document"/><select className="audit-filter" value={auditAction} onChange={(e) => { setAuditAction(e.target.value); }} aria-label="Filter by action"><option value="">All actions</option>{["login","upload","download","read","edit","delete","grant_access","revoke_access","delete_user"].map((a) => <option key={a} value={a}>{a.replaceAll("_", " ")}</option>)}</select><select className="audit-filter" value={auditResult} onChange={(e) => setAuditResult(e.target.value)} aria-label="Filter by result"><option value="">All results</option><option value="allowed">Allowed</option><option value="denied">Denied</option></select><button className="button button-secondary" onClick={() => loadAuditPage(1, captureAuditFilters({ action: auditAction, result: auditResult, search: auditSearch }))}>Apply filters</button><button className="button button-quiet" disabled={!auditEntries?.length || auditTotal === 0 || auditExporting} onClick={() => downloadAudit("txt")}>{auditExporting ? "Preparing export…" : "Export TXT"}</button><button className="button button-quiet" disabled={!auditEntries?.length || auditTotal === 0 || auditExporting} onClick={() => downloadAudit("md")}>{auditExporting ? "Preparing export…" : "Export Markdown"}</button><span className="audit-export-note">Exports include all {auditTotal} records matching the applied filters.</span></div>{auditEntries && <><ActivityTable entries={auditEntries} onDetails={setSelectedAudit}/><div className="audit-pagination"><span>{auditTotal} events \u00b7 Page {auditPage} of {Math.max(1, Math.ceil(auditTotal / 20))}</span><div><button className="button button-secondary button-sm" disabled={auditPage <= 1} onClick={() => loadAuditPage(auditPage - 1)}>Previous</button><button className="button button-secondary button-sm" disabled={auditPage >= Math.ceil(auditTotal / 20)} onClick={() => loadAuditPage(auditPage + 1)}>Next</button></div></div></>}</section> : activeTab === "users" ? <RegisteredUsersTable registeredUsers={registeredUsers} user={user} deletingUserId={deletingUserId} onDelete={handleDeleteUser} /> : filtered.length === 0 ? <div className="empty-state"><span className="empty-icon">{query ? "⌕" : activeTab === "my-docs" ? "▤" : "⇆"}</span><h3>{query ? "No matching documents" : activeTab === "my-docs" ? "Your vault is ready" : "Nothing has been shared with you"}</h3><p>{query ? "Try searching for another filename." : activeTab === "my-docs" ? "You have not uploaded any documents yet." : "Documents shared with you will appear here."}</p>{activeTab === "my-docs" && !query && <button className="button button-primary" onClick={() => setPage("upload")}>＋ Upload your first document</button>}</div> :
            <div className="document-list">{filtered.map((doc) => <article className="document-row" key={doc.id}><div className="document-details"><span className="file-mark">FILE</span><div><h3 title={doc.filename}>{doc.filename}</h3><p>{size(doc.size)} <i>·</i> Added {date(doc.created_at)}</p></div></div><div className="document-actions"><button className="button button-secondary button-sm" onClick={() => handleDownload(doc)}>↓ Download</button>{activeTab === "my-docs" && doc.owner_id === user.id && <><button className="button button-outline button-sm" onClick={() => setShareDocId(doc.id)}>Share</button><button className="button button-danger button-sm" onClick={() => handleDelete(doc.id)}>Delete</button></>}</div></article>)}</div>}
        </section>}
    </main>
    <footer className="footer"><span><Shield /> TrustVault</span><span>Private by design</span></footer>
    </div>

    {selectedAudit && <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) setSelectedAudit(null); }}><aside className="audit-drawer" role="dialog" aria-modal="true" aria-label="Audit event details"><div className="section-heading"><h2>Audit Event #{selectedAudit.id}</h2><button className="close-button" onClick={() => setSelectedAudit(null)}>\u00d7</button></div><p>Hash chain links</p><pre>{JSON.stringify({ previous_hash: selectedAudit.prev_hash, hash: selectedAudit.hash }, null, 2)}</pre><p>Event metadata</p><pre>{JSON.stringify(selectedAudit, null, 2)}</pre></aside></div>}
    {shareDocId && <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) setShareDocId(null); }}><section className="share-modal" role="dialog" aria-modal="true" aria-labelledby="share-title"><div className="modal-heading"><div><span className="eyebrow">DOCUMENT ACCESS</span><h2 id="share-title">Share document</h2><p>Choose who can access this file.</p></div><button className="close-button" aria-label="Close" onClick={() => setShareDocId(null)}>×</button></div>
      <form onSubmit={handleShare}>{shareDocId === "choose" && <label className="field"><span>Document</span><select required value={shareDocId === "choose" ? "" : shareDocId} onChange={(e) => setShareDocId(Number(e.target.value))}><option value="" disabled>Select a document</option>{documents.filter((d) => d.owner_id === user.id).map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}</select></label>}<label className="field"><span>Email address</span><input type="email" placeholder="colleague@example.com" required value={shareEmail} onChange={(e) => setShareEmail(e.target.value)} /></label>
        <fieldset className="permission-options"><legend>Permission level</legend><label className={shareLevel === "read" ? "permission-card selected" : "permission-card"}><input type="radio" name="permission" value="read" checked={shareLevel === "read"} onChange={() => setShareLevel("read")} /><span className="radio-dot" /><span><b>Read</b><small>View and download only</small></span></label><label className={shareLevel === "edit" ? "permission-card selected" : "permission-card"}><input type="radio" name="permission" value="edit" checked={shareLevel === "edit"} onChange={() => setShareLevel("edit")} /><span className="radio-dot" /><span><b>Edit</b><small>Modify document content</small></span></label></fieldset>
        <div className="modal-actions"><button className="button button-quiet" type="button" onClick={() => setShareDocId(null)}>Done</button><button className="button button-primary" disabled={sharing}>{sharing ? "Saving…" : "Grant access"}</button></div></form>
      <div className="access-list"><div className="access-title"><h3>Who has access</h3><span>{shares.length}</span></div>{sharesLoading ? <p className="access-empty">Loading access list…</p> : shares.length === 0 ? <p className="access-empty">No one else has access yet.</p> : shares.map((grant) => <div className="grant-row" key={grant.id}><span className="grant-avatar">{grant.user_email[0]?.toUpperCase()}</span><span className="grant-user"><b>{grant.user_email}</b><small>{grant.level === "edit" ? "Can edit" : "Can read"}</small></span><button className="revoke-button" onClick={() => revoke(grant.user_id)}>Revoke</button></div>)}</div>
    </section></div>}
  </div>;
}



