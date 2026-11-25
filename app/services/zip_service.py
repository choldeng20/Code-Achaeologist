import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

MAX_FILES = 5000
MAX_UNCOMPRESSED_SIZE = 100 * 1024 * 1024


class ZipValidationError(Exception):
    """Raised when an uploaded ZIP archive fails validation."""


def get_zip_paths(uploaded_file):
    try:
        with zipfile.ZipFile(uploaded_file) as archive:
            return _validated_paths(archive)
    except zipfile.BadZipFile as error:
        raise ZipValidationError(
            "The uploaded file is not a valid ZIP."
        ) from error


def _validated_paths(archive):
    entries = archive.infolist()
    if len(entries) > MAX_FILES:
        raise ZipValidationError("ZIP contains too many files.")

    total_size = 0
    paths = []

    for entry in entries:
        name = entry.filename

        if "\\" in name:
            raise ZipValidationError("ZIP contains an unsafe path.")

        path = PurePosixPath(name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or re.match(r"^[A-Za-z]:", name)
        ):
            raise ZipValidationError("ZIP contains an unsafe path.")

        mode = entry.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ZipValidationError("ZIP contains a symbolic link.")

        if entry.flag_bits & 0x1:
            raise ZipValidationError("Encrypted ZIP files are not supported.")

        if not name or entry.is_dir():
            continue

        total_size += entry.file_size
        if total_size > MAX_UNCOMPRESSED_SIZE:
            raise ZipValidationError("ZIP contents are too large.")

        paths.append(str(path))

    return paths


def extract_zip(uploaded_file, destination, strip_top_level=False):
    """Safely extract a validated archive beneath destination."""
    paths = get_zip_paths(uploaded_file)
    common_root = None
    if strip_top_level and paths:
        path_parts = [PurePosixPath(path).parts for path in paths]
        first_parts = {parts[0] for parts in path_parts if len(parts) > 1}
        if len(first_parts) == 1 and all(len(parts) > 1 for parts in path_parts):
            common_root = first_parts.pop()

    uploaded_file.seek(0)
    root = Path(destination).resolve()
    root.mkdir(parents=True, exist_ok=True)
    total_extracted = 0

    try:
        with zipfile.ZipFile(uploaded_file) as archive:
            for entry in archive.infolist():
                if not entry.filename or entry.filename.endswith("/"):
                    continue
                parts = PurePosixPath(entry.filename).parts
                if common_root is not None:
                    parts = parts[1:]
                if not parts:
                    continue

                target = root.joinpath(*parts).resolve()
                if root not in target.parents:
                    raise ZipValidationError("ZIP contains an unsafe path.")

                target.parent.mkdir(parents=True, exist_ok=True)
                written = 0
                with archive.open(entry) as source, target.open("wb") as output:
                    while True:
                        remaining = MAX_UNCOMPRESSED_SIZE - total_extracted
                        chunk = source.read(min(65536, remaining + 1))
                        if not chunk:
                            break
                        written += len(chunk)
                        total_extracted += len(chunk)
                        if written > entry.file_size or total_extracted > MAX_UNCOMPRESSED_SIZE:
                            raise ZipValidationError("ZIP contents are too large.")
                        output.write(chunk)
                if written != entry.file_size:
                    raise ZipValidationError("The uploaded file is not a valid ZIP.")
    except zipfile.BadZipFile as error:
        raise ZipValidationError(
            "The uploaded file is not a valid ZIP."
        ) from error

    return root
