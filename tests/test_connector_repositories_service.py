"""Service-level unit tests for connector repository listing helpers."""
from __future__ import annotations

import json
import unittest
import urllib.error
from io import BytesIO
from unittest.mock import Mock, patch

from fastapi import HTTPException

from backend.services.connector_repositories import _list_github_repositories


class ListGithubRepositoriesTest(unittest.TestCase):
    def test_token_prefix_returns_fixture(self) -> None:
        repos = _list_github_repositories(access_token="token_fixture_value")
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["full_name"], "openai/malcom")
        self.assertEqual(repos[0]["owner"], "openai")
        self.assertTrue(repos[0]["private"])
        self.assertEqual(repos[0]["default_branch"], "main")

    def test_ghp_secret_prefix_returns_fixture(self) -> None:
        repos = _list_github_repositories(access_token="ghp_secret_test_value")
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["full_name"], "openai/malcom")

    def test_real_token_returns_parsed_repos(self) -> None:
        payload = [
            {
                "id": 42,
                "name": "my-repo",
                "full_name": "octocat/my-repo",
                "owner": {"login": "octocat"},
                "private": False,
                "default_branch": "main",
            },
        ]
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")
        ctx = Mock()
        ctx.__enter__ = Mock(return_value=mock_response)
        ctx.__exit__ = Mock(return_value=False)

        with patch("backend.services.connector_repositories.urllib.request.urlopen", return_value=ctx):
            repos = _list_github_repositories(access_token="ghp_real_token")

        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["full_name"], "octocat/my-repo")
        self.assertEqual(repos[0]["owner"], "octocat")
        self.assertFalse(repos[0]["private"])

    def test_items_missing_required_fields_are_skipped(self) -> None:
        payload = [
            {"id": 1, "name": "", "full_name": "octocat/my-repo", "owner": {"login": "octocat"}, "private": False, "default_branch": "main"},
            {"id": 2, "name": "good-repo", "full_name": "octocat/good-repo", "owner": {"login": "octocat"}, "private": False, "default_branch": "main"},
            "not-a-dict",
        ]
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")
        ctx = Mock()
        ctx.__enter__ = Mock(return_value=mock_response)
        ctx.__exit__ = Mock(return_value=False)

        with patch("backend.services.connector_repositories.urllib.request.urlopen", return_value=ctx):
            repos = _list_github_repositories(access_token="ghp_real_token")

        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["name"], "good-repo")

    def test_http_error_raises_conflict(self) -> None:
        http_error = urllib.error.HTTPError(
            url="https://api.github.com/user/repos",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=BytesIO(b'{"message":"Bad credentials"}'),
        )

        with patch("backend.services.connector_repositories.urllib.request.urlopen", side_effect=http_error):
            with self.assertRaises(HTTPException) as ctx:
                _list_github_repositories(access_token="ghp_bad_token")

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("Unable to list repositories", ctx.exception.detail)

    def test_url_error_raises_bad_gateway(self) -> None:
        url_error = urllib.error.URLError(reason="Connection refused")

        with patch("backend.services.connector_repositories.urllib.request.urlopen", side_effect=url_error):
            with self.assertRaises(HTTPException) as ctx:
                _list_github_repositories(access_token="ghp_real_token")

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("Unable to reach GitHub", ctx.exception.detail)

    def test_non_list_response_raises_bad_gateway(self) -> None:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"unexpected": "dict"}).encode("utf-8")
        ctx = Mock()
        ctx.__enter__ = Mock(return_value=mock_response)
        ctx.__exit__ = Mock(return_value=False)

        with patch("backend.services.connector_repositories.urllib.request.urlopen", return_value=ctx):
            with self.assertRaises(HTTPException) as exc_ctx:
                _list_github_repositories(access_token="ghp_real_token")

        self.assertEqual(exc_ctx.exception.status_code, 502)
        self.assertIn("unexpected response", exc_ctx.exception.detail)

    def test_malformed_json_raises_bad_gateway(self) -> None:
        mock_response = Mock()
        mock_response.read.return_value = b"not-json"
        ctx = Mock()
        ctx.__enter__ = Mock(return_value=mock_response)
        ctx.__exit__ = Mock(return_value=False)

        with patch("backend.services.connector_repositories.urllib.request.urlopen", return_value=ctx):
            with self.assertRaises(HTTPException) as exc_ctx:
                _list_github_repositories(access_token="ghp_real_token")

        self.assertEqual(exc_ctx.exception.status_code, 502)
        self.assertIn("malformed JSON", exc_ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
