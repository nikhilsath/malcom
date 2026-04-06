import hmac
import hashlib
import json

from backend.services.github_webhook import verify_signature, extract_delivery_id, normalize_github_event


def test_verify_signature_valid():
    secret = "supersecret"
    body = b'{"ref": "refs/heads/main", "repository": {"name": "repo", "owner": {"login": "alice"}}}'
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    headers = {"x-hub-signature-256": f"sha256={expected}"}
    assert verify_signature(headers, body, secret) is True


def test_verify_signature_invalid():
    secret = "supersecret"
    body = b'{}'
    headers = {"x-hub-signature-256": "sha256=deadbeef"}
    assert verify_signature(headers, body, secret) is False


def test_extract_delivery_id_present():
    headers = {"x-github-delivery": "delivery-123"}
    assert extract_delivery_id(headers) == "delivery-123"


def test_extract_delivery_id_missing():
    headers = {}
    assert extract_delivery_id(headers) is None


def test_normalize_push_event_minimal():
    payload = {
        "ref": "refs/heads/main",
        "repository": {"name": "repo", "owner": {"login": "alice"}},
        "commits": [
            {"id": "c1", "added": ["a.txt"], "modified": ["b.txt"], "removed": []}
        ],
        "pusher": {"name": "alice"},
    }
    normalized, metadata = normalize_github_event(payload, "push")
    assert normalized["event_type"] == "push"
    assert metadata["owner"] == "alice"
    assert metadata["repo"] == "repo"
    assert metadata["ref"] == "refs/heads/main"
    assert "b.txt" in metadata["paths"]


def test_normalize_pull_request_event_minimal():
    payload = {
        "action": "opened",
        "pull_request": {"head": {"ref": "feature-1"}, "number": 5},
        "repository": {"name": "repo2", "owner": {"login": "bob"}},
        "sender": {"login": "bob"},
    }
    normalized, metadata = normalize_github_event(payload, "pull_request")
    assert normalized["event_type"] == "pull_request"
    assert metadata["owner"] == "bob"
    assert metadata["repo"] == "repo2"
    assert metadata["ref"] == "feature-1"
