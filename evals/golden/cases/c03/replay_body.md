<!-- triage-replay: {"case_id": "c03", "original_created_at": "2025-11-11T05:20:43Z", "original_author_association": "NONE"} -->
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

**To Reproduce**

<!--
Minimal steps to reproduce the behavior with source code and Black's configuration.
-->

For example, take this code:

```python
[
    (1, 2),
    # # fmt: off
    # (3,
    #    4),
    # # fmt: on
    (5, 6),
]
```

And run it with these arguments:

```sh
$ black file.py
```

The resulting error is:

> error: cannot format file.py: INTERNAL ERROR: Black 25.11.0 on Python (CPython) 3.11.13 produced different code on the second pass of the formatter.  Please report a bug on https://github[.]com/psf/black/issues.  This diff might be helpful: /tmp/blk_wtxhgk34.log
>
> Oh no! 💥 💔 💥
> 1 file failed to reformat.

The error is most likely caused by the inclusion of a set of commented lines that include `# # fmt: off` and `# # fmt: on`. Removing one or both of these lines does not cause the error.

**Expected behavior**

<!-- A clear and concise description of what you expected to happen. -->

I would expect no errors and in fact, this does not occur in previous versions. Is this new behaviour expected?

**Environment**

<!-- Please complete the following information: -->

- Black's version: <!-- e.g. [main] --> 25.11.0
- OS and Python version: <!-- e.g. [Linux/Python 3.7.4rc1] --> Linux/Ubuntu 24.04.2 LTS/Python 3.11.13

<!-- Add any other context about the problem here. -->

