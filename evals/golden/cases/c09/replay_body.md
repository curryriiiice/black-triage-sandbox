<!-- triage-replay: {"case_id": "c09", "original_created_at": "2026-02-18T18:26:47Z", "original_author_association": "NONE"} -->
<!--
Please make sure that the bug is not already fixed either in newer versions or the
current development version. To confirm this, you have three options:

1. Update Black's version if a newer release exists: `pip install -U black`
2. Use the online formatter at <https://black.vercel.app/?version=main>, which will use
   the latest main branch.
3. Or run _Black_ on your machine:
   - create a new virtualenv (make sure it's the same Python version);
   - clone this repository;
   - run `pip install -e .[d]`;
   - run `pip install --group tests`
   - make sure it's sane by running `python -m pytest -n auto`; and
   - run `black` like you did last time.
-->

**Describe the bug**

Running Black on the example code below introduces a change in the meaning of the code.

**To Reproduce**

For example, take this code:

```python
assert (
    # my comment
    my_var == 999 if abc == "TEST" else 0
)
```

Black updates it to:

```python
assert (
    # my comment
    my_var == 999
    if abc == "TEST"
    else 0
)
```

This introduces a bug:
- Original code: when `abc == "TEST"` this results in `assert my_var == 0`
- Updated code: when `abc == "TEST"` this results in `assert 0`

**Expected behavior**

Adding parentheses would fix it. For example:

```python
assert (
    # my comment
    my_var == (
        999 if abc == "TEST" else 0
    )
)
```

**Environment**

- Black's version: 25.11.0
- OS and Python version: MacOS, Python 3.9.6

**Additional context**

<!-- Add any other context about the problem here. -->

