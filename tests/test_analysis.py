import io
import unittest
import zipfile
from unittest.mock import patch

import requests

from app import create_app


def github_http_error(status_code, headers=None, body=""):
    response = requests.Response()
    response.status_code = status_code
    response.headers.update(headers or {})
    response._content = body.encode("utf-8")
    return requests.HTTPError(response=response)


def make_github_archive():
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr(
            "owner-repo-sha/src/main.py",
            "import json\n\ndef main():\n    return json.dumps({})\n",
        )
    archive.seek(0)
    return archive.getvalue()


class AnalysisRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_homepage_returns_api_status_json(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "status": "ok",
                "message": "API is running. Frontend: http://127.0.0.1:5173/",
            },
        )

    def test_request_body_size_is_limited_to_10_mib(self):
        self.assertEqual(
            self.client.application.config["MAX_CONTENT_LENGTH"],
            10 * 1024 * 1024,
        )

    def test_analyze_github_returns_repository_analysis(self):
        repository = {
            "name": "repo",
            "owner": {"login": "owner"},
            "description": "A test repository",
            "stargazers_count": 12,
            "default_branch": "trunk",
        }
        tree = {
            "tree": [
                {"path": "src/main.py", "type": "blob"},
                {"path": "src", "type": "tree"},
            ]
        }

        with (
            patch(
                "app.routes.analysis.github.get_repository",
                return_value=repository,
            ) as get_repository,
            patch(
                "app.routes.analysis.github.get_repository_files",
                return_value=tree,
            ) as get_files,
            patch(
                "app.routes.analysis.github.get_repository_archive",
                return_value=make_github_archive(),
            ) as get_archive,
        ):
            response = self.client.post(
                "/api/analyze/github",
                json={"repo_url": "https://github.com/owner/repo.git/"},
            )

        get_repository.assert_called_once_with("owner", "repo")
        get_files.assert_called_once_with("owner", "repo", "trunk")
        get_archive.assert_called_once_with("owner", "repo", "trunk")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["repository"]["analysis"]["total_files"], 1)
        self.assertEqual(
            payload["repository"]["analysis"]["languages"],
            {"Python": 1},
        )
        self.assertEqual(payload["python"]["summary"]["functions"], 1)
        self.assertEqual(payload["python"]["files"][0]["path"], "src/main.py")
        self.assertIn("longest_functions", payload["python"]["summary"])
        self.assertEqual(payload["repository"]["default_branch"], "trunk")

    def test_analyze_github_rejects_missing_or_invalid_url(self):
        missing = self.client.post("/api/analyze/github", json={})
        invalid = self.client.post(
            "/api/analyze/github",
            json={"repo_url": "https://example.com/owner/repo"},
        )

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("Unsupported GitHub URL", invalid.get_json()["error"])

    def test_analyze_github_reports_repository_not_found(self):
        with patch(
            "app.routes.analysis.github.get_repository",
            side_effect=github_http_error(404),
        ):
            response = self.client.post(
                "/api/analyze/github",
                json={"repo_url": "https://github.com/owner/missing"},
            )

        self.assertEqual(response.status_code, 404)
        self.assertIn("repository not found", response.get_json()["error"])

    def test_analyze_github_reports_rate_limit(self):
        with patch(
            "app.routes.analysis.github.get_repository",
            side_effect=github_http_error(
                403,
                {"X-RateLimit-Remaining": "0"},
            ),
        ):
            response = self.client.post(
                "/api/analyze/github",
                json={"repo_url": "https://github.com/owner/repo"},
            )

        self.assertEqual(response.status_code, 429)
        self.assertIn("rate limit", response.get_json()["error"])

    def test_analyze_github_reports_forbidden_without_rate_limit(self):
        with patch(
            "app.routes.analysis.github.get_repository",
            side_effect=github_http_error(403),
        ):
            response = self.client.post(
                "/api/analyze/github",
                json={"repo_url": "https://github.com/owner/repo"},
            )

        self.assertEqual(response.status_code, 403)
        self.assertIn("denied access", response.get_json()["error"])

    def test_analyze_github_reports_network_errors(self):
        with patch(
            "app.routes.analysis.github.get_repository",
            side_effect=requests.Timeout(),
        ):
            response = self.client.post(
                "/api/analyze/github",
                json={"repo_url": "https://github.com/owner/repo"},
            )

        self.assertEqual(response.status_code, 502)
        self.assertIn("Network error", response.get_json()["error"])

    def test_analyze_github_reports_unsupported_branch(self):
        repository = {"default_branch": "trunk"}
        with (
            patch(
                "app.routes.analysis.github.get_repository",
                return_value=repository,
            ),
            patch(
                "app.routes.analysis.github.get_repository_files",
                side_effect=github_http_error(404),
            ) as get_files,
        ):
            response = self.client.post(
                "/api/analyze/github",
                json={
                    "repo_url": (
                        "https://github.com/owner/repo/tree/feature/missing"
                    ),
                },
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(get_files.call_args.args, ("owner", "repo", "feature/missing"))
        self.assertIn("branch 'feature/missing' not found", response.get_json()["error"])

    def test_analyze_github_accepts_trailing_slash_git_and_tree_branch(self):
        repository = {
            "name": "repo",
            "owner": {"login": "owner"},
            "description": "A test repository",
            "stargazers_count": 12,
            "default_branch": "trunk",
        }
        tree = {"tree": []}
        with (
            patch(
                "app.routes.analysis.github.get_repository",
                return_value=repository,
            ),
            patch(
                "app.routes.analysis.github.get_repository_files",
                return_value=tree,
            ) as get_files,
            patch(
                "app.routes.analysis.github.get_repository_archive",
                return_value=make_github_archive(),
            ) as get_archive,
        ):
            response = self.client.post(
                "/api/analyze/github",
                json={
                    "repo_url": "https://github.com/owner/repo.git/tree/feature/one/",
                },
            )

        self.assertEqual(response.status_code, 200)
        get_files.assert_called_once_with("owner", "repo", "feature/one")
        get_archive.assert_called_once_with("owner", "repo", "feature/one")

    def test_analyze_zip_returns_file_analysis(self):
        uploaded_file = io.BytesIO()
        with zipfile.ZipFile(uploaded_file, "w") as archive:
            archive.writestr(
                "nested/src/main.py",
                "class Worker:\n"
                "    def run(self, items):\n"
                "        if items:\n"
                "            for item in items:\n"
                "                print(item)\n"
                "def greet():\n"
                "    return 'hello'\n",
            )
            archive.writestr("nested/broken.py", "def broken(:\n")
        uploaded_file.seek(0)

        response = self.client.post(
            "/api/analyze/zip",
            data={"file": (uploaded_file, "project.zip")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["source"], "zip")
        self.assertEqual(payload["analysis"]["languages"], {"Python": 2})
        self.assertEqual(payload["python"]["summary"]["classes"], 1)
        self.assertEqual(payload["python"]["summary"]["methods"], 1)
        self.assertEqual(payload["python"]["summary"]["functions"], 1)
        self.assertEqual(payload["python"]["summary"]["parse_errors"], 1)
        broken_file = next(
            file for file in payload["python"]["files"]
            if file["path"] == "nested/broken.py"
        )
        self.assertIn("SyntaxError", broken_file["error"])
        self.assertIn(
            "nested/src/main.py",
            [file["path"] for file in payload["python"]["files"]],
        )

    def test_analyze_zip_without_python_files_returns_empty_python_summary(self):
        uploaded_file = io.BytesIO()
        with zipfile.ZipFile(uploaded_file, "w") as archive:
            archive.writestr("README.txt", "No Python here")
        uploaded_file.seek(0)

        response = self.client.post(
            "/api/analyze/zip",
            data={"file": (uploaded_file, "project.zip")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["python"]["summary"]["python_files"], 0)
        self.assertEqual(response.get_json()["python"]["files"], [])

    def test_analyze_zip_rejects_missing_or_non_zip_upload(self):
        missing = self.client.post("/api/analyze/zip")
        non_zip = self.client.post(
            "/api/analyze/zip",
            data={"file": (io.BytesIO(b"data"), "project.txt")},
            content_type="multipart/form-data",
        )

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(non_zip.status_code, 400)

    def test_analyze_zip_rejects_invalid_archive(self):
        response = self.client.post(
            "/api/analyze/zip",
            data={"file": (io.BytesIO(b"not a zip"), "project.zip")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("not a valid ZIP", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
