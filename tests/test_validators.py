import unittest

from app.utils.validators import parse_github_url, validate_github_url


class GitHubUrlValidationTests(unittest.TestCase):
    def test_accepts_repository_url_with_git_suffix(self):
        self.assertEqual(
            parse_github_url("https://github.com/kavoo7/full-stack-project.git"),
            ("kavoo7", "full-stack-project", None),
        )

    def test_accepts_repository_url_with_trailing_slash(self):
        self.assertEqual(
            parse_github_url("https://github.com/owner/repo/"),
            ("owner", "repo", None),
        )

    def test_parses_branch_path_including_slashes(self):
        self.assertEqual(
            parse_github_url(
                "https://github.com/owner/repo/tree/feature/new-endpoint"
            ),
            ("owner", "repo", "feature/new-endpoint"),
        )

    def test_rejects_unsupported_github_path(self):
        self.assertIsNone(
            parse_github_url("https://github.com/owner/repo/blob/main/file.py")
        )
        self.assertIsNone(
            parse_github_url("https://example.com/owner/repo")
        )

    def test_legacy_validator_still_returns_owner_and_repository(self):
        self.assertEqual(
            validate_github_url(
                "https://github.com/owner/repo/tree/main"
            ),
            ("owner", "repo"),
        )


if __name__ == "__main__":
    unittest.main()
