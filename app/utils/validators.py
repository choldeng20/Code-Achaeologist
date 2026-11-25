from urllib.parse import unquote, urlsplit


def parse_github_url(url):
    if not isinstance(url, str):
        return None

    try:
        parsed = urlsplit(url.strip())
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return None

    if (
        parsed.scheme != "https"
        or host != "github.com"
        or port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        return None

    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        return None

    owner, repo = parts[:2]
    owner = unquote(owner)
    repo = unquote(repo)
    if repo.endswith(".git"):
        repo = repo[:-4]

    if not owner or not repo or owner in {".", ".."} or repo in {".", ".."}:
        return None

    branch = None
    if len(parts) > 2:
        if len(parts) < 4 or parts[2] != "tree":
            return None
        branch_parts = [unquote(part) for part in parts[3:]]
        if not all(branch_parts):
            return None
        branch = "/".join(branch_parts)

    return owner, repo, branch


def validate_github_url(url):
    """Return repository owner and name for supported GitHub URLs."""
    parsed = parse_github_url(url)
    return parsed[:2] if parsed else None
