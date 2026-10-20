<!-- triage-replay: {"case_id": "c08", "original_created_at": "2026-02-02T17:04:28Z", "original_author_association": "NONE"} -->
**Describe the bug**

Historic behaviour:

```
❯ black --version && black --diff tests/test_cases/not_utf8.py
black, 23.9.1 (compiled: no)
Python (CPython) 3.13.5
All done! ✨ 🍰 ✨
1 file would be left unchanged.
```

```
❯ black --version && black --diff tests/test_cases/not_utf8.py
black, 25.12.0 (compiled: no)
Python (CPython) 3.13.5
All done! ✨ 🍰 ✨
1 file would be left unchanged.
```

New behaviour:

```
❯ black --version && black --diff tests/test_cases/not_utf8.py
black, 26.1.0 (compiled: no)
Python (CPython) 3.13.5
error: cannot format tests/test_cases/not_utf8.py: INTERNAL ERROR: Black 26.1.0 on Python (CPython) 3.13.5 produced code that is not equivalent to the source.  Please report a bug on https://github[.]com/psf/black/issues.  This diff might be helpful: /var/folders/_b/zf5p80v11bd2m2fq4j17z8mr0000gn/T/blk_9jeg_ijj.log

Oh no! 💥 💔 💥
1 file would fail to reformat.
```

```
❯ cat  /var/folders/_b/zf5p80v11bd2m2fq4j17z8mr0000gn/T/blk_9jeg_ijj.log
--- src
+++ dst
@@ -63,11 +63,11 @@
                 value=
                 Constant(
                     kind=
                     None,  # NoneType
                     value=
-                    'Initialize name instance.\n\n>>> fred = Name("FrÃ©dÃ©ric", "FranÃ§ois")\n>>> print(fred)',  # str
+                    'Initialize name instance.\n\n>>> fred = Name("FrÃ\x83Â\x83Ã\x82Â©dÃ\x83Â\x83Ã\x82Â©ric", "FranÃ\x83Â\x83Ã\x82Â§ois")\n>>> print(fred)',  # str
                 )  # /Constant
             )  # /Expr
             Assign(
                 targets=
                 Attribute(
```

Looks like a change in how non ASCII strings are represented?

**To Reproduce**

Using this file: https://github[.]com/peterjc/flake8-rst-docstrings/blob/master/tests/test_cases/not_utf8.py

This is a test case over five years old, as per the file header:

> This file is not using UTF-8, but Western European.
>
> It works fine using the Windows-1252 or iso-8859-1 encoding,
but not using UTF-8 which is the Python default.

**Expected behavior**

No error, no reformatting as in black 23.9.1 or black 25.12.0

**Environment**

- Black's version:  26.1.0
- OS and Python version: macOS / Python 3.13.5 

**Additional context**

Spotted by CI under Linux, see https://github[.]com/peterjc/flake8-rst-docstrings/pull/102
