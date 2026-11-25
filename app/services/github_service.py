import os
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_API = "https://api.github.com"


class GitHubService:
    def __init__(self):
        self.headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Code-Archaeologist",
        }

        token = os.getenv("GITHUB_TOKEN")
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def get_repository(self, owner, repo):
        url = f"{GITHUB_API}/repos/{owner}/{repo}"
        response = requests.get(url, headers=self.headers, timeout=15)
        response.raise_for_status()
        return response.json()

    def get_repository_files(self, owner, repo, branch):
        url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_repository_archive(self, owner, repo, branch):
        url = f"{GITHUB_API}/repos/{owner}/{repo}/zipball/{quote(branch, safe='')}"
        response = requests.get(url, headers=self.headers, timeout=60)
        response.raise_for_status()
        return response.content
