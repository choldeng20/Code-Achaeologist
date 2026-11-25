from io import BytesIO
from tempfile import TemporaryDirectory

import requests
from flask import Blueprint, jsonify, request

from app.services.ast_service import analyze_directory
from app.services.github_service import GitHubService
from app.services.scanner_service import analyze_files
from app.services.zip_service import ZipValidationError, extract_zip, get_zip_paths
from app.utils.validators import parse_github_url

analysis = Blueprint("analysis", __name__)
github = GitHubService()


def _is_rate_limit_error(error):
    response = error.response
    if response is None:
        return False
    if response.status_code == 429:
        return True

    headers = response.headers
    body = response.text.lower()
    return (
        response.status_code == 403
        and (
            headers.get("X-RateLimit-Remaining") == "0"
            or "rate limit" in body
            or "secondary rate" in body
        )
    )


def _github_http_error(error, operation, branch=None):
    response = error.response
    status_code = response.status_code if response is not None else None

    if _is_rate_limit_error(error):
        return jsonify({
            "error": "GitHub API rate limit exceeded. Try again later or configure GITHUB_TOKEN.",
        }), 429
    if status_code == 404:
        if operation == "repository":
            message = "GitHub repository not found (HTTP 404). Check the owner and repository name."
        else:
            message = f"GitHub branch '{branch}' not found (HTTP 404)."
        return jsonify({"error": message}), 404
    if status_code == 403:
        return jsonify({
            "error": "GitHub denied access to this resource (HTTP 403).",
        }), 403

    status = f"HTTP {status_code}" if status_code is not None else "unknown HTTP status"
    return jsonify({"error": f"GitHub API request failed ({status})."}), 502


@analysis.get("/")
def index():
    return jsonify({
        "status": "ok",
        "message": "API is running. Frontend: http://127.0.0.1:5173/",
    }), 200


@analysis.post("/api/analyze/github")
def analyze_github():
    data = request.get_json(silent=True)
    repo_url = data.get("repo_url") if isinstance(data, dict) else None

    if not isinstance(repo_url, str):
        return jsonify({"error": "Repository URL is required"}), 400

    parsed = parse_github_url(repo_url)
    if not parsed:
        return jsonify({
            "error": (
                "Unsupported GitHub URL. Use https://github.com/<owner>/<repo>, "
                "optionally with .git, a trailing slash, or /tree/<branch>."
            ),
        }), 400

    owner, repo, requested_branch = parsed
    operation = "repository"
    branch = None

    try:
        repository = github.get_repository(owner, repo)
        branch = requested_branch or repository["default_branch"]
        operation = "branch"
        tree = github.get_repository_files(owner, repo, branch)
        paths = [
            item["path"]
            for item in tree.get("tree", [])
            if item["type"] == "blob"
        ]
        analysis_result = analyze_files(paths)
        operation = "archive"
        archive = github.get_repository_archive(owner, repo, branch)
        with TemporaryDirectory() as extracted_root:
            extract_zip(
                BytesIO(archive),
                extracted_root,
                strip_top_level=True,
            )
            python_result = analyze_directory(
                extracted_root,
                analysis_result["files"],
            )

        return jsonify({
            "success": True,
            "python": python_result,
            "repository": {
                "name": repository["name"],
                "owner": repository["owner"]["login"],
                "description": repository["description"],
                "stars": repository["stargazers_count"],
                "default_branch": branch,
                "analysis": analysis_result,
            },
        }), 200
    except requests.HTTPError as error:
        return _github_http_error(error, operation, branch)
    except requests.RequestException as error:
        return jsonify({
            "error": (
                f"Network error connecting to GitHub "
                f"({type(error).__name__}). Check your connection and try again."
            ),
        }), 502
    except ZipValidationError as error:
        return jsonify({
            "error": f"GitHub repository archive could not be analyzed: {error}",
        }), 502


@analysis.post("/api/analyze/zip")
def analyze_zip():
    uploaded_file = request.files.get("file")

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"error": "Please upload a ZIP file"}), 400

    if not uploaded_file.filename.lower().endswith(".zip"):
        return jsonify({"error": "Only ZIP files are supported"}), 400

    try:
        paths = get_zip_paths(uploaded_file.stream)
        analysis_result = analyze_files(paths)
        uploaded_file.stream.seek(0)
        with TemporaryDirectory() as extracted_root:
            extract_zip(uploaded_file.stream, extracted_root)
            python_result = analyze_directory(
                extracted_root,
                analysis_result["files"],
            )

        return jsonify({
            "success": True,
            "source": "zip",
            "python": python_result,
            "analysis": analysis_result,
        }), 200
    except ZipValidationError as error:
        return jsonify({"error": str(error)}), 400
