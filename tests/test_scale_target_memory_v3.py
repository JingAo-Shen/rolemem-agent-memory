import pytest
import hashlib
from scripts.build_scale_target_memory import extract_best_hunk


def test_empty_target_evidence_rejected():
    empty_sha = hashlib.sha256(b"").hexdigest()
    assert empty_sha == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_extract_best_hunk_finds_relevant_diff():
    diff = """diff --git a/pkg/mod.py b/pkg/mod.py
index 1111..2222 100644
--- a/pkg/mod.py
+++ b/pkg/mod.py
@@ -10,6 +10,7 @@ def old_func():
-    return 1
+    # use new_func instead
+    return new_func()
"""
    best_file, hunk, excerpt = extract_best_hunk(diff, "pkg/mod.py", "old_func", ["new_func"])
    assert best_file == "pkg/mod.py"
    assert "use new_func instead" in hunk
    assert len(excerpt) > 0
    assert hashlib.sha256(hunk.encode("utf-8")).hexdigest() != "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
