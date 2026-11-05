import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_token(email: str, password: str = "password123") -> str:
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_sharing_lifecycle():
    # 1. Login as Alice (owner) and upload a document to test with
    alice_token = get_token("alice@example.com")
    alice_headers = {"Authorization": f"Bearer {alice_token}"}

    file_content = b"sample content for sharing tests"
    upload_res = client.post(
        "/documents",
        headers=alice_headers,
        files={"file": ("share_test.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 2. Login as Bob (no permissions yet)
    bob_token = get_token("bob@example.com")
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # Bob should not see it in his document list
    docs_res = client.get("/documents", headers=bob_headers)
    assert docs_res.status_code == 200
    assert not any(d["id"] == doc_id for d in docs_res.json())

    # Bob cannot download it
    dl_res = client.get(f"/documents/{doc_id}/download", headers=bob_headers)
    assert dl_res.status_code == 403

    # 3. Alice shares the document with Bob
    share_res = client.post(
        f"/documents/{doc_id}/share",
        headers=alice_headers,
        json={"user_email": "bob@example.com", "level": "read"},
    )
    assert share_res.status_code == 200
    assert share_res.json()["level"] == "read"
    assert share_res.json()["user_email"] == "bob@example.com"
    bob_user_id = share_res.json()["user_id"]

    # 4. Bob can now see and download the document
    docs_res_after = client.get("/documents", headers=bob_headers)
    assert docs_res_after.status_code == 200
    assert any(d["id"] == doc_id for d in docs_res_after.json())

    bob_dl_res = client.get(f"/documents/{doc_id}/download", headers=bob_headers)
    assert bob_dl_res.status_code == 200
    assert bob_dl_res.content == file_content

    # 5. Bob (read-only) CANNOT delete or re-share it
    bob_del_res = client.delete(f"/documents/{doc_id}", headers=bob_headers)
    assert bob_del_res.status_code == 403

    bob_reshare_res = client.post(
        f"/documents/{doc_id}/share",
        headers=bob_headers,
        json={"user_email": "carol@example.com", "level": "read"},
    )
    assert bob_reshare_res.status_code == 403

    # 6. Alice views shares and revokes Bob's access
    shares_list_res = client.get(f"/documents/{doc_id}/shares", headers=alice_headers)
    assert shares_list_res.status_code == 200
    assert any(s["user_email"] == "bob@example.com" for s in shares_list_res.json())

    revoke_res = client.delete(
        f"/documents/{doc_id}/share/{bob_user_id}", headers=alice_headers
    )
    assert revoke_res.status_code == 204

    # 7. Bob immediately loses access
    revoked_list = client.get("/documents", headers=bob_headers)
    assert not any(d["id"] == doc_id for d in revoked_list.json())

    revoked_dl = client.get(f"/documents/{doc_id}/download", headers=bob_headers)
    assert revoked_dl.status_code == 403

    # Clean up: Alice deletes the test document
    clean_res = client.delete(f"/documents/{doc_id}", headers=alice_headers)
    assert clean_res.status_code == 204