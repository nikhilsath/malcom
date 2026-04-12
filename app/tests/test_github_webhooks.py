import hmac
import hashlib
import json

from backend.services import github_webhook
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


def test_dispatch_normalized_event_matches_enabled_github_automation(monkeypatch):
    connection = object()
    logger = object()
    normalized_event = {
        "source": "github",
        "event_type": "push",
        "metadata": {"owner": "alice", "repo": "repo", "ref": "refs/heads/main", "paths": ["src/app.py"]},
    }
    metadata = {"owner": "alice", "repo": "repo", "ref": "refs/heads/main", "paths": ["src/app.py"]}
    automation_rows = [
        {
            "id": "match",
            "trigger_config_json": json.dumps(
                {
                    "github_owner": "alice",
                    "github_repo": "repo",
                    "github_event_type": "push",
                    "github_branch_filter": "main",
                    "github_path_filter": "src/*.py",
                }
            ),
        },
        {
            "id": "wrong_owner",
            "trigger_config_json": json.dumps(
                {
                    "github_owner": "bob",
                    "github_repo": "repo",
                    "github_event_type": "push",
                }
            ),
        },
        {
            "id": "wrong_path",
            "trigger_config_json": json.dumps(
                {
                    "github_owner": "alice",
                    "github_repo": "repo",
                    "github_event_type": "push",
                    "github_path_filter": "docs/*.md",
                }
            ),
        },
    ]
    dispatched: list[tuple[str, str, dict[str, object], object, object]] = []

    monkeypatch.setattr(github_webhook, "fetch_all", lambda *_args, **_kwargs: automation_rows)
    monkeypatch.setattr(
        github_webhook,
        "execute_automation_definition",
        lambda conn, log, **kwargs: dispatched.append(
            (kwargs["automation_id"], kwargs["trigger_type"], kwargs["payload"], kwargs["root_dir"], kwargs["database_url"])
        ),
    )
    monkeypatch.setattr(github_webhook, "write_application_log", lambda *_args, **_kwargs: None)

    matched = github_webhook.dispatch_normalized_event(
        connection,
        logger,
        normalized_event,
        metadata,
        root_dir=None,
        database_url=None,
    )

    assert matched == 1
    assert dispatched == [("match", "github", normalized_event, None, None)]


def test_dispatch_normalized_event_skips_when_event_type_does_not_match(monkeypatch):
    connection = object()
    logger = object()
    normalized_event = {"source": "github", "event_type": "pull_request", "metadata": {}}
    metadata = {"owner": "alice", "repo": "repo", "ref": "refs/heads/main", "paths": ["src/app.py"]}
    automation_rows = [
        {
            "id": "push-only",
            "trigger_config_json": json.dumps(
                {
                    "github_owner": "alice",
                    "github_repo": "repo",
                    "github_event_type": "push",
                    "github_branch_filter": "main",
                }
            ),
        }
    ]
    dispatched: list[dict[str, object]] = []

    monkeypatch.setattr(github_webhook, "fetch_all", lambda *_args, **_kwargs: automation_rows)
    monkeypatch.setattr(github_webhook, "execute_automation_definition", lambda conn, log, **kwargs: dispatched.append(kwargs))
    monkeypatch.setattr(github_webhook, "write_application_log", lambda *_args, **_kwargs: None)

    matched = github_webhook.dispatch_normalized_event(
        connection,
        logger,
        normalized_event,
        metadata,
        root_dir=None,
        database_url=None,
    )

    assert matched == 0
    assert dispatched == []
