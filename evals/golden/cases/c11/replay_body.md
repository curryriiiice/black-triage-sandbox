<!-- triage-replay: {"case_id": "c11", "original_created_at": "2026-03-16T10:11:59Z", "original_author_association": "NONE"} -->
**Describe the style change**

Minimizing diffs is nice but this can come at the cost of reduced code readability.
Notably, when reading code on a monitor, there is only so much screen real estate.
So the more lines the code is spread on, the more the user needs to scroll to read it and with the scrolling, the higher the cognitive load (need to remember parts that are not on screen).

One could argue that keeping brackets vertically aligned helps understand the code structure but modern IDEs already highlight this.

In the case of Black, there are many new lines with very few characters.
It would be good to have an option to move these with an adjacent line.

The rules could be:

- two options:
    - no-short-lines: bool, when true, this feature is activated
    - min-line-length: int
```
lines = sort(lines, len)  # sort lines by increasing length to process them by increasing length
for line in lines:
    if len(line) < min-line-length and line[0] in ("{", "}", "(", ")", "[", "]"):
        if the previous line has a training comma, remove it (no point)
        move line with the previous line
        if the previous line is now longer than max-line-length consider splitting it around a ":"
```
This does imply that max-line-length could be exceeded by min-line-length

**Original code**
These ten lines of code
```python
schema = Schema({
    Literal("a", description="lorem ipsum"):
        And([str], lambda x: len(x) >= 1 and len(x) <= 2),
    Literal("b", description="lorem ipsum"): And(str, len),
    Optional(
        Literal("c", description="lorem ipsum lorem ipsum lorem ipsum lorem ipsum"),
        default=""): str,
    Optional(
        Literal("d", description="lorem ipsum lorem ipsum lorem ipsum lorem ipsum"),
        default=1): str,
    Optional(
        Literal("e", description="lorem ipsum lorem ipsum lorem ipsum lorem ipsum"),
        default=1): And(int, lambda x: x >= -1)},
    ignore_extra_keys=True,
    description="lorem ipsum")
```

**Examples in the current _Black_ style**
End up taking twenty lines
```python
schema = Schema(
    {
        Literal("a", description="lorem ipsum"): And(
            [str], lambda x: len(x) >= 1 and len(x) <= 2
        ),
        Literal("b", description="lorem ipsum"): And(str, len),
        Optional(
            Literal("c", description="lorem ipsum lorem ipsum lorem ipsum lorem ipsum"),
            default="",
        ): str,
        Optional(
            Literal("d", description="lorem ipsum lorem ipsum lorem ipsum lorem ipsum"),
            default=1,
        ): str,
        Optional(
            Literal("e", description="lorem ipsum lorem ipsum lorem ipsum lorem ipsum"),
            default=1,
        ): And(int, lambda x: x >= -1),
    },
    ignore_extra_keys=True,
    description="lorem ipsum",
)
```

**Desired style**

Same as original code.

**Additional context**

There is a reddit topic with the similar issue https://www.reddit.com/r/learnpython/comments/s9ae7q/is_there_any_code_formatter_for_python_making/

