<!-- triage-replay: {"case_id": "c14", "original_created_at": "2026-05-06T09:37:19Z", "original_author_association": "NONE"} -->
black fails with the following error when parsing valid f string:

```
Black produced invalid code: f-string: expecting '}'
```

`f"Processing {data['type']}: {data['id']}"`

This is a valid f-string so it should be handled correctly.

Note that `f"Processing {data["type"]}: {data["id"]}"` is fine
