import io
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from app.services.zip_service import (
    ZipValidationError,
    extract_zip,
    get_zip_paths,
)


def make_zip(entries):
    uploaded_file = io.BytesIO()
    with zipfile.ZipFile(uploaded_file, "w") as archive:
        for name, contents in entries:
            if isinstance(contents, zipfile.ZipInfo):
                archive.writestr(contents, b"")
            else:
                archive.writestr(name, contents)
    uploaded_file.seek(0)
    return uploaded_file


class ZipServiceTests(unittest.TestCase):
    def test_returns_file_paths_and_skips_directories(self):
        uploaded_file = make_zip(
            [
                ("src/", b""),
                ("src/main.py", b"print('hello')"),
            ]
        )

        self.assertEqual(get_zip_paths(uploaded_file), ["src/main.py"])

    def test_extracts_validated_archive(self):
        uploaded_file = make_zip([("src/main.py", b"print('hello')")])
        with tempfile.TemporaryDirectory() as destination:
            extract_zip(uploaded_file, destination)

            extracted = Path(destination, "src", "main.py")
            self.assertEqual(extracted.read_bytes(), b"print('hello')")

    def test_can_strip_github_archive_root(self):
        uploaded_file = make_zip(
            [("owner-repo-sha/src/main.py", b"print('hello')")]
        )
        with tempfile.TemporaryDirectory() as destination:
            extract_zip(uploaded_file, destination, strip_top_level=True)

            extracted = Path(destination, "src", "main.py")
            self.assertEqual(extracted.read_bytes(), b"print('hello')")

    def test_rejects_unsafe_paths(self):
        for path in ("../secret.txt", "/secret.txt", "C:/secret.txt"):
            with self.subTest(path=path):
                with self.assertRaises(ZipValidationError):
                    get_zip_paths(make_zip([(path, b"data")]))

    def test_rejects_backslashes_in_original_zip_path(self):
        entry = Mock(
            filename="folder\\file.txt",
            external_attr=0,
            flag_bits=0,
            file_size=4,
        )
        entry.is_dir.return_value = False
        archive = Mock()
        archive.__enter__ = Mock(return_value=archive)
        archive.__exit__ = Mock(return_value=False)
        archive.infolist.return_value = [entry]

        with patch("app.services.zip_service.zipfile.ZipFile", return_value=archive):
            with self.assertRaisesRegex(ZipValidationError, "unsafe path"):
                get_zip_paths(io.BytesIO())

    def test_rejects_symbolic_links(self):
        entry = zipfile.ZipInfo("link")
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16

        with self.assertRaisesRegex(ZipValidationError, "symbolic link"):
            get_zip_paths(make_zip([("link", entry)]))

    def test_rejects_too_many_entries(self):
        uploaded_file = make_zip([("one", b""), ("two", b"")])

        with patch("app.services.zip_service.MAX_FILES", 1):
            with self.assertRaisesRegex(ZipValidationError, "too many"):
                get_zip_paths(uploaded_file)

    def test_rejects_excessive_uncompressed_size(self):
        uploaded_file = make_zip([("file.txt", b"too large")])

        with patch("app.services.zip_service.MAX_UNCOMPRESSED_SIZE", 4):
            with self.assertRaisesRegex(ZipValidationError, "too large"):
                get_zip_paths(uploaded_file)

    def test_rejects_invalid_zip(self):
        with self.assertRaisesRegex(ZipValidationError, "not a valid ZIP"):
            get_zip_paths(io.BytesIO(b"not a zip"))


if __name__ == "__main__":
    unittest.main()
