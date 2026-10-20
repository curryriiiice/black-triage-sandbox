<!-- triage-replay: {"case_id": "c10", "original_created_at": "2026-03-11T09:06:08Z", "original_author_association": "CONTRIBUTOR"} -->
**Is your feature request related to a problem? Please describe.**

Python 3.15 adds support for the `lazy` soft keyword:

* https://docs.python.org/3.15/whatsnew/3.15.html#whatsnew315-lazy-imports
* https://peps.python.org/pep-0810/

This has now available for testing in Python 3.15.0a7:

* https://discuss.python.org/t/python-3-15-0-alpha-7/106475

<!-- A clear and concise description of what the problem is.
e.g. I'm always frustrated when [...] -->

**Describe the solution you'd like**

Add support for the `lazy` soft keyword.


<!-- A clear and concise description of what you want to
happen. -->

**Describe alternatives you've considered**

<!-- A clear and concise description of any
alternative solutions or features you've considered. -->

Wait for the next Ruff release? https://github[.]com/astral-sh/ruff/issues/21305

**Additional context**

<!-- Add any other context or screenshots about the feature request
here. -->

```python
lazy import random

if __name__ == "__main__":
    print(random.randint(1, 6))
```
```console
❯ black --version
black, 26.3.0 (compiled: yes)
Python (CPython) 3.14.3

❯ black 1.py
error: cannot format 1.py: Cannot parse: 1:5: lazy import random

Oh no! 💥 💔 💥
1 file failed to reformat.
```

