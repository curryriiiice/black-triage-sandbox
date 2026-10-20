<!-- triage-replay: {"case_id": "c06", "original_created_at": "2026-01-07T19:30:39Z", "original_author_association": "NONE"} -->
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
   - run `pip install -r test_requirements.txt`
   - make sure it's sane by running `python -m pytest`; and
   - run `black` like you did last time.
-->

**Describe the bug**

<!-- A clear and concise description of what the bug is. -->
When my code contains a multi-line expression that's concatenated using backslash (`\`) and no indentation, black cannot parse my code

**To Reproduce**

<!--
Minimal steps to reproduce the behavior with source code and Black's configuration.
-->

For example, take this code:

```python
if True:
    foo = 1+\
2
    print(foo)
```

And run it with these arguments:

```sh
$ black file.py --target-version py313
```

The resulting error is:

> error: cannot format file.py: Cannot parse for target version Python 3.13: 3:0: 2

**Expected behavior**

<!-- A clear and concise description of what you expected to happen. -->
The file should be formatted to:
```
if True:
    foo = 1 + 2
    print(foo)
```

**Environment**

<!-- Please complete the following information: -->

- Black's version: 25.12.0
- OS and Python version: Debian 13, Python (CPython) 3.14.2

**Additional context**

<!-- Add any other context about the problem here. -->

