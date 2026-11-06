import React, { useState, useEffect } from "react";
import { apiRequest, apiUrl, downloadFile, getToken, setToken, clearToken } from "./api";

export default function App() {
  const [user, setUser] = useState(null);
  const [authMode, setAuthMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [documents, setDocuments] = useState([]);
  const [sharedDocuments, setSharedDocuments] = useState([]);
  const [sharedDocsLoaded, setSharedDocsLoaded] = useState(false);
  const [activeTab, setActiveTab] = useState('my-docs');
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [shareDocId, setShareDocId] = useState(null);
  const [shareEmail, setShareEmail] = useState("");
  const [shareLevel, setShareLevel] = useState("read");

  useEffect(() => {
    if (getToken()) {
      fetchUser();
    }
  }, []);

  async function fetchUser() {
    try {
      const u = await apiRequest("/auth/me");
      setUser(u);
      loadDocs();
    } catch {
      clearToken();
      setUser(null);
    }
  }

  async function loadDocs() {
    try {
      const docs = await apiRequest("/documents");
      setDocuments(docs);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadSharedDocs() {
    try {
      const docs = await apiRequest("/documents/shared-with-me");
      setSharedDocuments(docs);
      setSharedDocsLoaded(true);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAuth(e) {
    e.preventDefault();
    setError("");
    try {
      if (authMode === "register") {
        await apiRequest("/auth/register", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
      }
      const data = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setToken(data.access_token);
      setEmail("");
      setPassword("");
      await fetchUser();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      await apiRequest("/documents", { method: "POST", body: formData });
      await loadDocs();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function handleDelete(docId) {
    if (!confirm("Are you sure you want to delete this document?")) return;
    try {
      await apiRequest(`/documents/${docId}`, { method: "DELETE" });
      setDocuments((current) => current.filter((doc) => doc.id !== docId));
      setSharedDocuments((current) => current.filter((doc) => doc.id !== docId));
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDownload(doc) {
    setError("");
    try {
      await downloadFile(doc.id, doc.filename);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleShare(e) {
    e.preventDefault();
    setError("");
    try {
      const response = await fetch(apiUrl(`/documents/${shareDocId}/share`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ user_email: shareEmail, level: shareLevel }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.detail || "Failed to share document");
      }
      setShareDocId(null);
      setShareEmail("");
      alert("Document shared successfully!");
    } catch (err) {
      setError(err.message);
    }
  }

  function handleLogout() {
    clearToken();
    setUser(null);
    setDocuments([]);
    setSharedDocuments([]);
    setSharedDocsLoaded(false);
    setActiveTab('my-docs');
  }

  if (!user) {
    return (
      <div style={{ maxWidth: 400, margin: "80px auto", fontFamily: "system-ui, sans-serif", padding: 24, border: "1px solid #ddd", borderRadius: 8, boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
          <span style={{ fontSize: 24 }}>🔒</span>
          <h2 style={{ margin: 0 }}>TrustVault</h2>
        </div>
        {error && <div style={{ color: "red", marginBottom: 12, fontSize: 14 }}>{error}</div>}
        <form onSubmit={handleAuth} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <input
            type="email"
            placeholder="Email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ padding: 10, borderRadius: 4, border: "1px solid #ccc" }}
          />
          <input
            type="password"
            placeholder="Password (min 8 chars)"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ padding: 10, borderRadius: 4, border: "1px solid #ccc" }}
          />
          <button type="submit" style={{ padding: 10, background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: "bold" }}>
            {authMode === "login" ? "Log In" : "Register"}
          </button>
        </form>
        <p style={{ marginTop: 16, textAlign: "center", fontSize: 14 }}>
          {authMode === "login" ? "No account? " : "Already have an account? "}
          <button
            onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}
            style={{ background: "none", border: "none", color: "#2563eb", cursor: "pointer", textDecoration: "underline" }}
          >
            {authMode === "login" ? "Register" : "Log In"}
          </button>
        </p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 800, margin: "40px auto", fontFamily: "system-ui, sans-serif", padding: "0 16px" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #eee", paddingBottom: 16, marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 24 }}>🔒</span>
          <h1 style={{ margin: 0, fontSize: 24 }}>TrustVault</h1>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 14, color: "#666" }}>{user.email} ({user.role})</span>
          <button onClick={handleLogout} style={{ padding: "6px 12px", border: "1px solid #ccc", background: "#fff", borderRadius: 4, cursor: "pointer" }}>
            🚪 Logout
          </button>
        </div>
      </header>

      {error && <div style={{ color: "red", marginBottom: 16, padding: 8, background: "#fee2e2", borderRadius: 4 }}>{error}</div>}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>Documents</h2>
        <label style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 16px", background: "#2563eb", color: "#fff", borderRadius: 4, cursor: "pointer", fontWeight: "bold" }}>
          📤 {uploading ? "Uploading..." : "Upload File"}
          <input type="file" onChange={handleUpload} disabled={uploading} style={{ display: "none" }} />
        </label>
      </div>

      <div role="tablist" aria-label="Document lists" style={{ display: "flex", gap: 8, borderBottom: "1px solid #eee", marginBottom: 16 }}>
        <button role="tab" aria-selected={activeTab === 'my-docs'} onClick={() => setActiveTab('my-docs')} style={{ padding: "8px 12px", border: 0, borderBottom: activeTab === 'my-docs' ? "2px solid #2563eb" : "2px solid transparent", background: "none", color: activeTab === 'my-docs' ? "#2563eb" : "#666", cursor: "pointer", fontWeight: activeTab === 'my-docs' ? "bold" : "normal" }}>
          My Documents
        </button>
        <button role="tab" aria-selected={activeTab === 'shared-with-me'} onClick={() => { setActiveTab('shared-with-me'); if (!sharedDocsLoaded) loadSharedDocs(); }} style={{ padding: "8px 12px", border: 0, borderBottom: activeTab === 'shared-with-me' ? "2px solid #2563eb" : "2px solid transparent", background: "none", color: activeTab === 'shared-with-me' ? "#2563eb" : "#666", cursor: "pointer", fontWeight: activeTab === 'shared-with-me' ? "bold" : "normal" }}>
          Shared with Me
        </button>
      </div>

      <div style={{ border: "1px solid #eee", borderRadius: 6, overflow: "hidden" }}>
        {(activeTab === 'my-docs' ? documents : sharedDocuments).length === 0 ? (
          <div style={{ padding: 32, textAlign: "center", color: "#888" }}>{activeTab === 'my-docs' ? "No documents available. Upload one to get started." : "No documents have been shared with you."}</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
            <thead style={{ background: "#f8fafc", borderBottom: "1px solid #eee" }}>
              <tr>
                <th style={{ padding: 12 }}>Name</th>
                <th style={{ padding: 12 }}>Size</th>
                <th style={{ padding: 12 }}>Uploaded</th>
                <th style={{ padding: 12, textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {(activeTab === 'my-docs' ? documents : sharedDocuments).map((doc) => (
                <tr key={doc.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: 12 }}>📄 {doc.filename}</td>
                  <td style={{ padding: 12 }}>{(doc.size / 1024).toFixed(1)} KB</td>
                  <td style={{ padding: 12 }}>{new Date(doc.created_at).toLocaleDateString()}</td>
                  <td style={{ padding: 12, textAlign: "right" }}>
                    <button onClick={() => handleDownload(doc)} title="Download" aria-label={`Download ${doc.filename}`} style={{ marginRight: 8, border: "none", background: "none", cursor: "pointer", fontSize: 16 }}>
                      📥
                    </button>
                    {doc.owner_id === user.id && (
                      <>
                        <button onClick={() => setShareDocId(doc.id)} title="Share" style={{ marginRight: 8, border: "none", background: "none", cursor: "pointer", fontSize: 16 }}>
                          🔗
                        </button>
                        <button onClick={() => handleDelete(doc.id)} title="Delete" style={{ border: "none", background: "none", cursor: "pointer", fontSize: 16 }}>
                          🗑️
                        </button>
                      </>
                    )}
                    {doc.owner_id !== user.id && (
                      <>
                        <button type="button" title="Only the owner can share this document" aria-label={`Share ${doc.filename}`} disabled style={{ marginRight: 8, border: "none", background: "none", cursor: "not-allowed", opacity: 0.4, fontSize: 16 }}>Share</button>
                        <button type="button" title="Only the owner can delete this document" aria-label={`Delete ${doc.filename}`} disabled style={{ border: "none", background: "none", cursor: "not-allowed", opacity: 0.4, fontSize: 16 }}>Delete</button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {shareDocId && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ background: "#fff", padding: 24, borderRadius: 8, width: 340 }}>
            <h3 style={{ marginTop: 0 }}>Share Document</h3>
            <form onSubmit={handleShare} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <input
                type="email"
                placeholder="Target email"
                required
                value={shareEmail}
                onChange={(e) => setShareEmail(e.target.value)}
                style={{ padding: 8, borderRadius: 4, border: "1px solid #ccc" }}
              />
              <select value={shareLevel} onChange={(e) => setShareLevel(e.target.value)} style={{ padding: 8, borderRadius: 4, border: "1px solid #ccc" }}>
                <option value="read">Read Only</option>
                <option value="edit">Edit Permission</option>
              </select>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
                <button type="button" onClick={() => setShareDocId(null)} style={{ padding: "6px 12px", border: "1px solid #ccc", background: "#fff", borderRadius: 4, cursor: "pointer" }}>
                  Cancel
                </button>
                <button type="submit" style={{ padding: "6px 12px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}>
                  Share
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
