import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.ast_service import analyze_directory, analyze_source


class AstServiceTests(unittest.TestCase):
    def test_source_line_count_excludes_trailing_newline(self):
        result = analyze_source("pass\n", "sample.py")

        self.assertEqual(result["lines"], 1)

    def test_empty_source_has_zero_lines(self):
        self.assertEqual(analyze_source("")["lines"], 0)

    def test_analyze_source_collects_imports_functions_and_classes(self):
        source = (
            "import os.path\n"
            "from collections import Counter\n"
            "\n"
            "def run(value, *, enabled=False):\n"
            "    return value\n"
            "\n"
            "class Worker(Base):\n"
            "    async def start(self, item):\n"
            "        return item\n"
        )

        result = analyze_source(source, "worker.py")

        self.assertEqual(result["path"], "worker.py")
        self.assertEqual(result["imports"], ["collections", "os.path"])
        self.assertEqual(result["functions"][0]["args"], ["value", "enabled"])
        self.assertEqual(result["classes"][0]["bases"], ["Base"])
        self.assertTrue(result["classes"][0]["methods"][0]["is_async"])

    def test_function_metadata_includes_end_line_length_and_complexity(self):
        result = analyze_source(
            "def inspect(items):\n"
            "    if items:\n"
            "        for item in items:\n"
            "            print(item)\n",
        )
        function = result["functions"][0]

        self.assertEqual(function["line"], 1)
        self.assertEqual(function["end_line"], 4)
        self.assertEqual(function["length"], 4)
        self.assertEqual(function["complexity"], 3)

    def test_async_method_metadata_includes_complexity(self):
        result = analyze_source(
            "class Worker:\n"
            "    async def start(self, ready):\n"
            "        if ready and self:\n"
            "            return True\n",
        )
        method = result["classes"][0]["methods"][0]

        self.assertTrue(method["is_async"])
        self.assertEqual(method["complexity"], 3)

    def test_docstring_summary_counts_functions_and_methods(self):
        result = analyze_source(
            '"""module"""\n'
            'def documented():\n    """Function docs."""\n    pass\n'
            "def undocumented():\n    pass\n"
            "class Worker:\n"
            '    def ready(self):\n        """Method docs."""\n        pass\n'
        )
        with tempfile.TemporaryDirectory() as root:
            Path(root, "sample.py").write_text(
                'def documented():\n    """Function docs."""\n    pass\n'
                "def undocumented():\n    pass\n"
                "class Worker:\n"
                '    def ready(self):\n        """Method docs."""\n        pass\n',
                encoding="utf-8",
            )
            summary = analyze_directory(root, ["sample.py"])["summary"]

        self.assertEqual(result["functions"][0]["has_docstring"], True)
        self.assertEqual(summary["undocumented_functions"], 1)
        self.assertEqual(summary["docstring_coverage"], 66.7)

    def test_summary_lists_longest_and_most_complex_functions(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "sample.py").write_text(
                "def short():\n    pass\n"
                "def branching(items):\n"
                "    if items:\n"
                "        for item in items:\n"
                "            print(item)\n",
                encoding="utf-8",
            )
            summary = analyze_directory(root, ["sample.py"])["summary"]

        self.assertEqual(summary["longest_functions"][0]["name"], "branching")
        self.assertEqual(summary["most_complex"][0]["complexity"], 3)
        self.assertEqual(summary["most_complex"][0]["path"], "sample.py")

    def test_summary_counts_imports_by_module(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "sample.py").write_text(
                "import json\nfrom json import dumps\n",
                encoding="utf-8",
            )
            Path(root, "other.py").write_text("import json\n", encoding="utf-8")
            summary = analyze_directory(root, ["sample.py", "other.py"])["summary"]

        self.assertEqual(summary["top_imports"], [{"name": "json", "files": 2}])

    def test_syntax_error_is_reported_without_raising(self):
        result = analyze_source("def broken(:\n", "broken.py")

        self.assertEqual(result["error"].split(":", 1)[0], "SyntaxError")

    def test_analyze_directory_summarizes_python_files(self):
        with tempfile.TemporaryDirectory() as root:
            project = Path(root)
            (project / "main.py").write_text(
                "import json\n\ndef main():\n    pass\n",
                encoding="utf-8",
            )
            (project / "readme.txt").write_text("ignored", encoding="utf-8")

            result = analyze_directory(root, ["main.py", "readme.txt"])

        self.assertEqual(result["summary"]["python_files"], 1)
        self.assertEqual(result["summary"]["functions"], 1)
        self.assertEqual(result["summary"]["total_lines"], 4)
        self.assertEqual(result["summary"]["top_imports"], [{"name": "json", "files": 1}])

    def test_analyze_directory_rejects_paths_outside_root(self):
        with tempfile.TemporaryDirectory() as root:
            result = analyze_directory(root, ["../outside.py"])

        self.assertEqual(
            result["files"][0]["error"],
            "Path is outside the repository",
        )

    def test_analyze_directory_limits_number_of_files(self):
        with tempfile.TemporaryDirectory() as root:
            project = Path(root)
            (project / "first.py").write_text("pass\n", encoding="utf-8")
            (project / "second.py").write_text("pass\n", encoding="utf-8")

            with patch("app.services.ast_service.MAX_FILES", 1):
                result = analyze_directory(root, ["first.py", "second.py"])

        self.assertEqual(result["summary"]["python_files"], 1)
        self.assertEqual(result["summary"]["skipped_files"], 1)


if __name__ == "__main__":
    unittest.main()
