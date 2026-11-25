import unittest
from unittest.mock import Mock, patch

from app.services.github_service import GITHUB_API, GitHubService


class GitHubServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = GitHubService()

    @patch("app.services.github_service.requests.get")
    def test_get_repository_returns_json(self, get):
        response = Mock()
        response.json.return_value = {"full_name": "owner/repo"}
        get.return_value = response

        result = self.service.get_repository("owner", "repo")

        self.assertEqual(result, {"full_name": "owner/repo"})
        get.assert_called_once_with(
            f"{GITHUB_API}/repos/owner/repo",
            headers=self.service.headers,
            timeout=15,
        )
        response.raise_for_status.assert_called_once_with()

    @patch("app.services.github_service.requests.get")
    def test_get_repository_files_uses_recursive_tree_endpoint(self, get):
        response = Mock()
        response.json.return_value = {"tree": []}
        get.return_value = response

        result = self.service.get_repository_files("owner", "repo", "main")

        self.assertEqual(result, {"tree": []})
        get.assert_called_once_with(
            f"{GITHUB_API}/repos/owner/repo/git/trees/main?recursive=1",
            headers=self.service.headers,
            timeout=30,
        )
        response.raise_for_status.assert_called_once_with()

    @patch("app.services.github_service.requests.get")
    def test_get_repository_archive_uses_zipball_endpoint(self, get):
        response = Mock()
        response.content = b"archive"
        get.return_value = response

        result = self.service.get_repository_archive("owner", "repo", "feature/name")

        self.assertEqual(result, b"archive")
        get.assert_called_once_with(
            f"{GITHUB_API}/repos/owner/repo/zipball/feature%2Fname",
            headers=self.service.headers,
            timeout=60,
        )
        response.raise_for_status.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
