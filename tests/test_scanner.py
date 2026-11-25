import unittest

from app.services import scanner_service


class ScannerServiceTests(unittest.TestCase):
    def test_analyze_files_counts_languages_and_directories(self):
        result = scanner_service.analyze_files(
            ["src/main.py", "src/ui/app.js", "README.md"]
        )

        self.assertEqual(result["total_files"], 3)
        self.assertEqual(result["total_directories"], 2)
        self.assertEqual(result["languages"], {"Python": 1, "JavaScript": 1})
        self.assertEqual(result["files"], ["src/main.py", "src/ui/app.js", "README.md"])
        self.assertFalse(result["truncated"])

    def test_analyze_files_skips_ignored_directories(self):
        result = scanner_service.analyze_files(
            ["src/main.py", "node_modules/package/index.js", ".git/config"]
        )

        self.assertEqual(result["total_files"], 1)
        self.assertEqual(result["languages"], {"Python": 1})

    def test_analyze_files_truncates_file_listing(self):
        result = scanner_service.analyze_files(
            [f"file_{index}.py" for index in range(501)]
        )

        self.assertEqual(result["total_files"], 501)
        self.assertEqual(len(result["files"]), 500)
        self.assertTrue(result["truncated"])


if __name__ == "__main__":
    unittest.main()
