<!-- triage-replay: {"case_id": "c16", "original_created_at": "2026-07-22T03:11:12Z", "original_author_association": "NONE"} -->
### Describe the bug

With `--target-version py314`, Black rewrites a parenthesized `except` tuple into the Python-2 `except A, B:` form, which is a **`SyntaxError` in Python 3**. Black therefore emits source it cannot itself re-parse. The bug is specific to the `py314` target — `py313` and the default (no target) leave the code unchanged.

### To Reproduce

Given `bug.py`:

```python
try:
    pass
except (ValueError, TypeError):
    pass
```

Run:

```console
$ black --target-version py314 bug.py
```

Result — the file is rewritten to:

```python
try:
    pass
except ValueError, TypeError:
    pass
```

which no longer parses under Python 3:

```console
$ python -c "import ast; ast.parse(open('bug.py').read())"
  File "<unknown>", line 3
    except ValueError, TypeError:
                     ^
SyntaxError: multiple exception types must be parenthesized
```

Three-or-more-element tuples are affected too (`except (A, B, C):` → `except A, B, C:`).

### Expected behavior

`except (ValueError, TypeError):` is left unchanged. The parentheses are **required** in Python 3 and must never be removed.

### Environment

- Black version: **26.3.1** (from PyPI; `black --version` reports `black, 26.3.1 (compiled: yes)`)
- OS: Linux
- Python: CPython 3.14.6

### Additional context

- Deterministic on a cache miss. Because Black caches results by file mtime/size, a second run on an unchanged file may report "unchanged" without reformatting — clearing `~/.cache/black` (or editing the file) reproduces it every time.
- Not reproducible with `--target-version py313` or with no `--target-version` (defaults).
- Reproduces via the CLI flag alone; a `[tool.black] target-version = ["py314"]` in `pyproject.toml` triggers it identically.
- Impact: `black`/`black --check` in a py314-targeted project can silently turn valid source into a `SyntaxError`.

