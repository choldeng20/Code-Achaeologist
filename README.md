# Code Archaeologist

Code Archaeologist is a local web app for exploring a repository without
manually opening every file. Give it a GitHub repository URL or upload a ZIP,
then review the repository's file layout, language mix, and Python structure in
one dashboard.

The backend analyzes source locally. Python files are parsed with Python's
`ast` module; their code is not imported or executed.

## What you'll see

- **Repository overview:** total file and directory counts, plus detected
  languages.
- **File browser:** search and expand the repository tree to find files.
- **Python structure:** Python file and line counts, classes, top-level
  functions, class methods, and parse errors.
- **Python insights:** docstring coverage, the longest and most complex
  functions or methods, and the most-imported modules.

The function lists show at most five entries each. Complexity is a
cyclomatic-style estimate based on branching constructs; it is a navigation
aid, not a quality or security score. Docstring coverage is calculated across
top-level functions and direct class methods.

The language scanner recognizes Python, JavaScript, TypeScript, HTML, CSS,
Java, C++, C, PHP, Go, Ruby, Rust, and SQL. Common generated and environment
directories such as `.git`, `node_modules`, virtual environments, `dist`,
`build`, and `__pycache__` are skipped.

## Requirements

- Python 3.9 or newer
- Node.js and npm

## Install

From the project root, create a virtual environment and install the backend
dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Install the frontend dependencies:

```powershell
cd frontend
npm install
cd ..
```

### Optional GitHub token

Public repositories can be analyzed without a token. GitHub may rate-limit
unauthenticated requests; to use a token, create a local `.env` file and add:

```text
GITHUB_TOKEN=your_github_token
```

Keep `.env` private. It is ignored by Git and should never be committed.

## Run locally

Start the Flask API in one terminal from the project root:

```powershell
python run.py
```

Start the Vite frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

Open [http://127.0.0.1:5173/](http://127.0.0.1:5173/). Vite forwards `/api`
requests to the Flask API at `http://127.0.0.1:5000`.

## Analyze a repository

### GitHub

Paste a repository URL into the GitHub form. Supported forms include:

```text
https://github.com/owner/repository
https://github.com/owner/repository.git
https://github.com/owner/repository/
https://github.com/owner/repository/tree/branch-name
```

For branch names containing slashes, include the full path after `/tree/`, for
example `/tree/feature/new-endpoint`. If no branch is specified, the app uses
the repository's default branch reported by GitHub.

### ZIP upload

Choose a `.zip` archive from the upload form. The archive is checked for unsafe
paths, symbolic links, encryption, and size limits before extraction. Uploads
are limited to 10 MiB, archives to 5,000 entries, and extracted contents to
100 MiB. Python analysis is limited to 500 files, with individual Python
files limited to 1,000,000 bytes.

If a Python file has a syntax error, it is reported as a parse error; it does
not prevent analysis of the other files. The Python structure panel is hidden
when no Python files are found.

## API

- `GET /` returns a JSON API status message.
- `POST /api/analyze/github` accepts JSON such as
  `{"repo_url": "https://github.com/owner/repository"}`.
- `POST /api/analyze/zip` accepts a multipart upload with the field name
  `file`.

Successful analysis responses include repository file/language data and a
top-level `python` result containing `summary` and per-file details.

## Tests and checks

Run the backend unit tests from the project root:

```powershell
python -m unittest discover -s tests
```

Run frontend lint and build checks from `frontend`:

```powershell
npm.cmd run lint
npm.cmd run build
```

In PowerShell, use `npm.cmd` if the execution policy blocks `npm.ps1`.
