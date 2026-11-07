import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest, apiUrl, downloadFile, getToken, setToken, clearToken } from "./api";
import "./App.css";

function Shield() { return <svg className="shield" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3 19 6v5.2c0 4.7-3 7.8-7 9.8-4-2-7-5.1-7-9.8V6l7-3Z" stroke="currentColor" strokeWidth="1.7"/><path d="m9 12 2 2 4-4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>; }
const date = (v) => new Date(v).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
const size = (v) => v < 1048576 ? `${(v / 1024).toFixed(1)} KB` : `${(v / 1048576).toFixed(1)} MB`;

function ActivityTable({ entries }) {
  return <table className="data-table"><thead><tr><th>Timestamp</th><th>Actor</th><th>Action</th><th>Document ID</th><th>Result</th></tr></thead><tbody>{entries.map((entry) => <tr key={entry.id}><td>{new Date(entry.timestamp).toLocaleString()}</td><td>{entry.user_id ?? "System"}</td><td>{entry.action}</td><td>{entry.document_id ?? "—"}</td><td>{entry.result}</td></tr>)}</tbody></table>;
}

export default function App() {
  const [user, setUser] = useState(null), [authMode, setAuthMode] = useState("login");
  const [email, setEmail] = useState(""), [password, setPassword] = useState(""), [confirmPassword, setConfirmPassword] = useState("");
  const [documents, setDocuments] = useState([]), [sharedDocuments, setSharedDocuments] = useState([]);
  const [sharedDocsLoaded, setSharedDocsLoaded] = useState(false), [activeTab, setActiveTab] = useState("my-docs");
  const [error, setError] = useState(""), [uploading, setUploading] = useState(false);
  const [page, setPage] = useState("documents"), [uploadFile, setUploadFile] = useState(null), [query, setQuery] = useState("");
  const [shareDocId, setShareDocId] = useState(null), [shareEmail, setShareEmail] = useState("");
  const [shareLevel, setShareLevel] = useState("read"), [shares, setShares] = useState([]), [sharesLoading, setSharesLoading] = useState(false), [sharing, setSharing] = useState(false);
  const [registeredUsers, setRegisteredUsers] = useState(null), [auditEntries, setAuditEntries] = useState(null), [auditIntegrity, setAuditIntegrity] = useState(null);

  const fetchUser = useCallback(async () => {
    try { const u = await apiRequest("/auth/me"); setUser(u); setDocuments(await apiRequest("/documents")); }
    catch { clearToken(); setUser(null); }
  }, []);
  // Fetch initial session data after mount; state updates happen after the requests resolve.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { if (getToken()) fetchUser(); }, [fetchUser]);
  useEffect(() => { if (Number.isInteger(shareDocId)) loadShares(shareDocId); }, [shareDocId]);

  async function loadDocs() { try { setDocuments(await apiRequest("/documents")); } catch (err) { setError(err.message); } }
  async function loadSharedDocs() { try { setSharedDocuments(await apiRequest("/documents/shared-with-me")); setSharedDocsLoaded(true); } catch (err) { setError(err.message); } }
  async function loadShares(id) {
    setSharesLoading(true);
    try { setShares(await apiRequest(`/documents/${id}/shares`)); } catch (err) { setError(err.message); }
    finally { setSharesLoading(false); }
  }
  async function handleAuth(e) {
    e.preventDefault(); setError("");
    try {
      if (authMode === "register") { if (password !== confirmPassword) { setError("Passwords do not match"); return; } await apiRequest("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }); }
      const data = await apiRequest("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
      setToken(data.access_token); setEmail(""); setPassword(""); setConfirmPassword(""); await fetchUser();
    } catch (err) { setError(err.message); }
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
  function logout() { clearToken(); setUser(null); setDocuments([]); setSharedDocuments([]); setSharedDocsLoaded(false); setActiveTab("my-docs"); setPage("documents"); }
  const list = activeTab === "my-docs" ? documents : sharedDocuments;
  const filtered = useMemo(() => list.filter((d) => d.filename.toLowerCase().includes(query.trim().toLowerCase())), [list, query]);
  const searchResults = useMemo(() => [...documents, ...sharedDocuments].filter((d) => d.filename.toLowerCase().includes(query.trim().toLowerCase())), [documents, sharedDocuments, query]);

  if (!user) return <main className="auth-shell"><section className="auth-card">
    <div className="auth-brand"><span className="vault-mark"><Shield /></span><span className="eyebrow">PRIVATE FILES. PROTECTED.</span><h1>TrustVault</h1><p>Your secure workspace for important documents.</p></div>
    {error && <div className="alert" role="alert">{error}</div>}
    <form className="auth-form" onSubmit={handleAuth}>
      <label className="field"><span>Email address</span><input type="email" autoComplete="email" placeholder="you@example.com" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
      <label className="field"><span>Password</span><input type="password" autoComplete={authMode === "login" ? "current-password" : "new-password"} placeholder="At least 8 characters" required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
      {authMode === "register" && <label className="field"><span>Confirm Password</span><input type="password" autoComplete="new-password" required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} /></label>}<button className="button button-primary button-wide" type="submit">{authMode === "login" ? "Log in" : "Create account"} <span>→</span></button>
    </form>
    <p className="auth-switch">{authMode === "login" ? "New to TrustVault?" : "Already have an account?"} <button className="text-button" onClick={() => { setAuthMode(authMode === "login" ? "register" : "login"); setError(""); }}>{authMode === "login" ? "Create an account" : "I already have an account"}</button></p>
  </section></main>;

  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="#" onClick={(e) => { e.preventDefault(); setPage("documents"); }}><span className="brand-icon"><Shield /></span><span>Trust<span className="gold">Vault</span></span></a>
      <div className="account"><span className="avatar">{user.email?.[0]?.toUpperCase()}</span><span className="account-email">Welcome, {user.email}!</span><span className="role-badge">Your Role: {user.role}</span><button className="button button-quiet" onClick={logout}>Log out</button></div></header>
    <main className="main-content">
      <div className="page-heading"><div><span className="eyebrow">SECURE FILE SPACE</span><h1>{page === "upload" ? "Upload a document" : page === "search" ? "Search documents" : "Your documents"}</h1><p>Keep your important files organized and access controlled.</p></div>
        {page === "documents" && <div className="heading-actions"><button className="button button-secondary" onClick={() => { setPage("search"); if (!sharedDocsLoaded) loadSharedDocs(); }}>Search documents</button><button className="button button-primary" onClick={() => { setUploadFile(null); setPage("upload"); }}>Upload a document</button></div>}</div>
      {error && <div className="alert alert-banner" role="alert">{error}<button className="text-button" onClick={() => setError("")}>Dismiss</button></div>}

      {page === "upload" && <section className="panel upload-panel"><h2>Add a document</h2><p className="panel-subtitle">Select a file to add it to your vault.</p><form onSubmit={handleUpload}>
        <label className="dropzone"><input className="file-input" type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" onChange={(e) => setUploadFile(e.target.files?.[0] || null)} /><span className="upload-icon">↑</span><strong>{uploadFile ? uploadFile.name : "Choose a file to upload"}</strong><small>{uploadFile ? size(uploadFile.size) : "PDF, PNG, JPG or TXT · up to 5 MB"}</small><span className="button button-secondary">Browse files</span></label>
        <p className="form-note">The filename is used as the document title in this workspace.</p><div className="form-actions"><button type="button" className="button button-quiet" onClick={() => setPage("documents")}>Back</button><button className="button button-primary" type="submit" disabled={!uploadFile || uploading}>{uploading ? "Uploading…" : "Upload document"}</button></div></form></section>}

      {page === "search" && <section className="panel search-panel"><label className="field"><span>Search by filename</span><input autoFocus value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Type a filename…" /></label><p className="form-note">Searching across your documents and files shared with you.</p><div className="document-list">{searchResults.map((doc) => <article className="document-row" key={doc.id}><div className="document-details"><span className="file-mark">FILE</span><div><h3>{doc.filename}</h3><p>{size(doc.size)} · Added {date(doc.created_at)}</p></div></div><div className="document-actions"><button className="button button-secondary button-sm" onClick={() => handleDownload(doc)}>Download</button>{doc.owner_id === user.id && <><button className="button button-outline button-sm" onClick={() => setShareDocId(doc.id)}>Share</button><button className="button button-danger button-sm" onClick={() => handleDelete(doc.id)}>Delete</button></>}</div></article>)}</div>{searchResults.length === 0 && <p className="access-empty">No matching documents.</p>}<div className="form-actions"><button className="button button-quiet" onClick={() => { setQuery(""); setPage("documents"); }}>Back to documents</button></div></section>}

      {page === "documents" && <><section className="dashboard-management"><div className="management-heading"><span className="eyebrow">YOUR WORKSPACE</span><h2>Dashboard Overview</h2><p>Quick access to your documents, people, and activity.</p></div><div className="management-grid"><section className="management-group"><h3>Document Management</h3><div className="management-actions"><button className="button button-primary" onClick={() => { setUploadFile(null); setPage("upload"); }}>Upload Documents</button><button className="button button-secondary" onClick={() => { setActiveTab("my-docs"); document.getElementById("document-list-panel")?.scrollIntoView({ behavior: "smooth" }); }}>My Documents</button><button className="button button-secondary" onClick={() => { setActiveTab("shared-with-me"); loadSharedDocs(); document.getElementById("document-list-panel")?.scrollIntoView({ behavior: "smooth" }); }}>Shared Documents</button><button className="button button-outline" disabled={!documents.length} onClick={() => setShareDocId("choose")}>Share Documents</button></div></section><section className="management-group"><h3>User Management</h3><div className="management-actions"><button className="button button-secondary" onClick={async () => { if (registeredUsers) { setRegisteredUsers(null); return; } try { setRegisteredUsers(await apiRequest("/admin/users")); } catch (err) { setError(err.message); } }}>{registeredUsers ? "Close / Hide Users" : "View Registered Users"}</button></div></section><section className="management-group"><h3>Activity Management</h3><div className="management-actions"><button className="button button-secondary" onClick={async () => { if (auditEntries) { setAuditEntries(null); return; } try { setAuditEntries(await apiRequest("/admin/audit")); } catch (err) { setError(err.message); } }}>Activity History</button></div></section><button className="button dashboard-logout" onClick={logout}>Logout</button></div>{registeredUsers && <div className="management-table"><div className="section-heading"><h3>Registered Users</h3><button className="text-button" onClick={() => setRegisteredUsers(null)}>Close / Hide</button></div><table className="data-table"><thead><tr><th>ID</th><th>Email</th><th>Role</th><th>Created Date</th></tr></thead><tbody>{registeredUsers.map((u) => <tr key={u.id}><td>{u.id}</td><td>{u.email}</td><td>{u.role}</td><td>{u.created_at || "?"}</td></tr>)}</tbody></table></div>}{auditEntries && <div className="management-table"><div className="section-heading"><h3>Activity History</h3><button className="button button-outline" onClick={async () => { try { setAuditIntegrity(await apiRequest("/admin/audit/verify")); } catch (err) { setError(err.message); } }}>Verify Audit Integrity</button></div><ActivityTable entries={auditEntries} />{auditIntegrity && <p className="integrity-result">{auditIntegrity.ok ? "Audit hash chain is valid" : "Audit hash chain is invalid"}</p>}</div>}</section><div className="overview"><div className="overview-card"><span className="overview-icon">▤</span><span><b>{documents.length}</b><small>My documents</small></span></div><div className="overview-card"><span className="overview-icon neutral">⇆</span><span><b>{sharedDocuments.length}</b><small>Shared with me</small></span></div><div className="trust-caption"><Shield /> Access is checked on every request</div></div>
        <section className="documents-panel" id="document-list-panel"><div className="section-heading"><div><h2>Documents</h2><p>Manage your files and shared access.</p></div><span className="count">{list.length} files</span></div>
          <div className="tabs" role="tablist" aria-label="Dashboard sections"><button role="tab" aria-selected={activeTab === "my-docs"} className={activeTab === "my-docs" ? "tab active" : "tab"} onClick={() => setActiveTab("my-docs")}>My documents <span>{documents.length}</span></button><button role="tab" aria-selected={activeTab === "shared-with-me"} className={activeTab === "shared-with-me" ? "tab active" : "tab"} onClick={() => { setActiveTab("shared-with-me"); if (!sharedDocsLoaded) loadSharedDocs(); }}>Shared with me <span>{sharedDocuments.length}</span></button><button role="tab" aria-selected={activeTab === "activity"} className={activeTab === "activity" ? "tab active" : "tab"} onClick={async () => { setActiveTab("activity"); try { setAuditEntries(await apiRequest("/auth/activity")); } catch (err) { setError(err.message); } }}>Activity History</button>{user.role === "admin" && <button role="tab" aria-selected={activeTab === "users"} className={activeTab === "users" ? "tab active" : "tab"} onClick={async () => { setActiveTab("users"); try { setRegisteredUsers(await apiRequest("/admin/users")); } catch (err) { setError(err.message); } }}>User Management</button>}</div>
          {activeTab === "activity" ? <ActivityTable entries={auditEntries || []} /> : activeTab === "users" ? <table className="data-table"><thead><tr><th>ID</th><th>Email</th><th>Role</th><th>Created At</th></tr></thead><tbody>{registeredUsers?.map((u) => <tr key={u.id}><td>{u.id}</td><td>{u.email}</td><td>{u.role}</td><td>{u.created_at || "—"}</td></tr>)}</tbody></table> : filtered.length === 0 ? <div className="empty-state"><span className="empty-icon">{query ? "⌕" : activeTab === "my-docs" ? "▤" : "⇆"}</span><h3>{query ? "No matching documents" : activeTab === "my-docs" ? "Your vault is ready" : "Nothing has been shared with you"}</h3><p>{query ? "Try searching for another filename." : activeTab === "my-docs" ? "You have not uploaded any documents yet." : "Documents shared with you will appear here."}</p>{activeTab === "my-docs" && !query && <button className="button button-primary" onClick={() => setPage("upload")}>＋ Upload your first document</button>}</div> :
            <div className="document-list">{filtered.map((doc) => <article className="document-row" key={doc.id}><div className="document-details"><span className="file-mark">FILE</span><div><h3 title={doc.filename}>{doc.filename}</h3><p>{size(doc.size)} <i>·</i> Added {date(doc.created_at)}</p></div></div><div className="document-actions"><button className="button button-secondary button-sm" onClick={() => handleDownload(doc)}>↓ Download</button>{activeTab === "my-docs" && doc.owner_id === user.id && <><button className="button button-outline button-sm" onClick={() => setShareDocId(doc.id)}>Share</button><button className="button button-danger button-sm" onClick={() => handleDelete(doc.id)}>Delete</button></>}</div></article>)}</div>}
        </section></>}
    </main>
    <footer className="footer"><span><Shield /> TrustVault</span><span>Private by design</span></footer>

    {shareDocId && <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) setShareDocId(null); }}><section className="share-modal" role="dialog" aria-modal="true" aria-labelledby="share-title"><div className="modal-heading"><div><span className="eyebrow">DOCUMENT ACCESS</span><h2 id="share-title">Share document</h2><p>Choose who can access this file.</p></div><button className="close-button" aria-label="Close" onClick={() => setShareDocId(null)}>×</button></div>
      <form onSubmit={handleShare}>{shareDocId === "choose" && <label className="field"><span>Document</span><select required value={shareDocId === "choose" ? "" : shareDocId} onChange={(e) => setShareDocId(Number(e.target.value))}><option value="" disabled>Select a document</option>{documents.filter((d) => d.owner_id === user.id).map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}</select></label>}<label className="field"><span>Email address</span><input type="email" placeholder="colleague@example.com" required value={shareEmail} onChange={(e) => setShareEmail(e.target.value)} /></label>
        <fieldset className="permission-options"><legend>Permission level</legend><label className={shareLevel === "read" ? "permission-card selected" : "permission-card"}><input type="radio" name="permission" value="read" checked={shareLevel === "read"} onChange={() => setShareLevel("read")} /><span className="radio-dot" /><span><b>Read</b><small>View and download only</small></span></label><label className={shareLevel === "edit" ? "permission-card selected" : "permission-card"}><input type="radio" name="permission" value="edit" checked={shareLevel === "edit"} onChange={() => setShareLevel("edit")} /><span className="radio-dot" /><span><b>Edit</b><small>Modify document content</small></span></label></fieldset>
        <div className="modal-actions"><button className="button button-quiet" type="button" onClick={() => setShareDocId(null)}>Done</button><button className="button button-primary" disabled={sharing}>{sharing ? "Saving…" : "Grant access"}</button></div></form>
      <div className="access-list"><div className="access-title"><h3>Who has access</h3><span>{shares.length}</span></div>{sharesLoading ? <p className="access-empty">Loading access list…</p> : shares.length === 0 ? <p className="access-empty">No one else has access yet.</p> : shares.map((grant) => <div className="grant-row" key={grant.id}><span className="grant-avatar">{grant.user_email[0]?.toUpperCase()}</span><span className="grant-user"><b>{grant.user_email}</b><small>{grant.level === "edit" ? "Can edit" : "Can read"}</small></span><button className="revoke-button" onClick={() => revoke(grant.user_id)}>Revoke</button></div>)}</div>
    </section></div>}
  </div>;
}



