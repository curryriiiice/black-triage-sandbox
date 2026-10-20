<!-- triage-replay: {"case_id": "c05", "original_created_at": "2025-12-03T13:57:57Z", "original_author_association": "NONE"} -->
I am using the online formatter.

## Describe the bug

`black` failed with two ignores for type checkers.

## To Reproduce

```python
import pandas as pd


interval_td = pd.Interval(
    pd.Timedelta("1 days"), pd.Timedelta("2 days"), closed="neither"
)


_td = (  # pyright: ignore[reportOperatorIssue,reportUnknownVariableType]
    interval_td
    - pd.Interval(  # type: ignore[operator]
        pd.Timedelta(1, "ns"), pd.Timedelta(2, "ns")
    )
)
```

And run it with the online playground.

The resulting error is:

```text
INTERNAL ERROR: Black 25.1.1.dev28+g314f8cf on Python (CPython) 3.12.11 produced code that is not equivalent to the source.  Please report a bug on https://github[.]com/psf/black/issues.  This diff might be helpful: /tmp/blk_rf3407oy.log

--- src
+++ dst
@@ -215,8 +215,6 @@
                 keywords=
             )  # /Call
         )  # /BinOp
     )  # /Assign
     type_ignores=
-    TypeIgnore(
-    )  # /TypeIgnore
 )  # /Module
```

## Expected behavior

`black` should handle this.

## Environment

Online playground

## Additional context

None

