<!-- triage-replay: {"case_id": "c04", "original_created_at": "2025-11-29T15:45:43Z", "original_author_association": "COLLABORATOR"} -->
2023: upstream-issue-3407
2024: upstream-issue-4042
2025: upstream-issue-4522
Ruff: https://github[.]com/astral-sh/ruff/issues/20482

As always, the ideal is for all preview features to be stabilized, not including the unstable ones.

---

Ordered by most controversial to least:

<details>
<summary>multiline_string_handling (upstream-issue-1879)</summary>
Make expressions involving multiline strings more compact.

**Input**
```py
textwrap.dedent(
    """\
    This is a
    multiline string
"""
)

MULTILINE = """
foobar
""".replace(
    "\n", ""
)
```

**Output (off)**
*unchanged*

**Output (on)**
```py
textwrap.dedent("""\
    This is a
    multiline string
""")

MULTILINE = """
foobar
""".replace("\n", "")
```

Fairly controversial. There were some issues in upstream-issue-4159 that were never fully fixed. Additionally, it's only been in preview since v25.11 (but the issues were resolved as-best-as-possible since v25.9).
However, we haven't gotten any further feedback since then. I think the current state is an improvement overall and we probably won't be able to do much else.
IMO, we should at least include it in the first v26 beta to get user feedback, even if we don't plan on stabilizing it.
</details>

<details>
<summary>wrap_long_dict_values_in_parens (upstream-issue-3440)</summary>
Add parentheses around long values in dictionaries.

**Input**
```py
my_dict = {
    "a key in my dict": a_very_long_variable * and_a_very_long_function_call() / 100000.0
}
```

**Output (off)**
*unchanged*

**Output (on)**
```py
my_dict = {
    "a key in my dict": (
        a_very_long_variable * and_a_very_long_function_call() / 100000.0
    )
}
```

Could cause a lot of churn. Adds more parentheses and lines to reduce line length. Deferred in 2023 and 2024, then moved to unstable until 25.1, when the issues with it were resolved and it was moved to preview. Ruff has already decided this to be a non-priority (https://github[.]com/astral-sh/ruff/issues/12856, upstream-issue-4123).
</details>

<details>
<summary>wrap_comprehension_in (upstream-issue-4699)</summary>
Wrap the `in` clause of list and dictionary comprehensions across lines if it would otherwise exceed the maximum line length.

**Input**
```py
[a for graph_path_expression in refined_constraint.condition_as_predicate.variables]
```

**Output (off)**
```py
[
    a
    for graph_path_expression in refined_constraint.condition_as_predicate.variables
]
```

**Output (on)**
```py
[
    a
    for graph_path_expression in (
        refined_constraint.condition_as_predicate.variables
    )
]
```

Could cause a lot of churn. Adds more parentheses and lines to reduce line length. Ruff has already decided this to be a non-priority (upstream-issue-4123).
</details>

<details>
<summary>remove_parens_from_assignment_lhs (upstream-issue-4865)</summary>
Remove unnecessary parentheses from the left-hand side of assignments while preserving magic trailing commas and intentional multiline formatting.

**Input**
```py
(c, *_) = a()
```

**Output (off)**
*unchanged*

**Output (on)**
```py
c, *_ = a()
```

An unobjective change, but can cause lots of churn, and was added *very* recently (25.12).
</details>

<details>
<summary>fix_type_expansion_split (upstream-issue-4777)</summary>
Fix type expansions split in generic functions.

**Input**
```py
def func1[T: (int, str)](a,): ...
```

**Output (off)**
```py
def func1[
    T: (int, str)
](a,): ...
```

**Output (on)**
```py
def func1[T: (int, str)](
    a,
): ...
```

Causes a good amount of changes, but should be fairly objective.
</details>

<details>
<summary>standardize_type_comments (upstream-issue-4645)</summary>
Format type comments which have zero or more spaces between `#` and `type:` or between `type:` and value to `# type: (value)`.

**Input**
```py
#       type:     ignore
```

**Output (off)**
*unchanged*

**Output (on)**
```py
# type: ignore
```

Causes changes, but they are minimal, localized, and objective.
</details>

<details>
<summary>always_one_newline_after_import (upstream-issue-4489)</summary>
Always force one blank line after import statements, except when the line after the import is a comment or an import statement.

**Input**
```py
from middleman.authentication import validate_oauth_token


logger = logging.getLogger(__name__)
```

**Output (off)**
*unchanged*

**Output (on)**
```py
from middleman.authentication import validate_oauth_token

logger = logging.getLogger(__name__)
```

Only changes one part of each file, and changes are minimal and objective. Was deferred in 2025, just because it was new.
</details>

<details>
<summary>remove_parens_around_except_types (upstream-issue-4720)</summary>
Remove parentheses around multiple exception types in `except` and `except*` without `as`. See PEP 758 for details.

**Input**
```py
try:
    ...
except (A, B, C):
    ...
```

**Output (off)**
*unchanged*

**Output (on)**
```py
try:
    ...
except A, B, C:
    ...
```

New feature introduced in & gated to Python 3.14. No changes in most codebases, which are under 3.14. When there are changes, they're minimal, localized, and objective.
</details>

<details>
<summary>fix_module_docstring_detection (upstream-issue-4764)</summary>
Fix module docstrings being treated as normal strings if preceded by comments.

**Input**
```py
# comment
"""
docstring
"""
from __future__ import annotations
```

**Output (off)**
*unchanged*

**Output (on)**
```py
# comment
"""
docstring
"""


from __future__ import annotations
```

Bug fix; only changes one thing per file at max.
</details>

<details>
<summary>normalize_cr_newlines (upstream-issue-4710)</summary>
Add `\r` style newlines to the potential newlines to normalize file newlines both from and to.

**Input**
```py
a[CR]
b[LF]
c[CR][LF]
#1[CR][LF]
```

**Output (off)**
```py
a[CR]
b[LF]
c[CR]
# 1[CR]
```

**Output (on)**
```py
a[CR]
b[CR]
c[CR]
# 1[CR]
```

Bug fix, was only ever found by Fuzz and shouldn't cause any noticable source code changes in practice.
</details>

<details>
<summary>fix_fmt_skip_in_one_liners (upstream-issue-4800)</summary>
Fix `# fmt: skip` behavior on one-liner declarations, such as `def foo(): return "mock" # fmt: skip`, where previously the declaration would have been incorrectly collapsed.

**Input**
```py
if True: print("this"); print("that") # fmt: skip
```

**Output (off)**
```py
if True:
    print("this"); print("that") # fmt: skip
```

**Output (on)**
*unchanged*

Purely a bug fix, shouldn't actually change any pre-formatted code.
</details>

---

Also, we should remember to regenerate `_width_table.py` for v26 (upstream-issue-4253).

IMO, everything `fix_type_expansion_split` and below should *definitely* be stabilized. I see arguments either way for the items above it. Discussion welcome!

