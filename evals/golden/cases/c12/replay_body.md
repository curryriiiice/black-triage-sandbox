<!-- triage-replay: {"case_id": "c12", "original_created_at": "2026-03-19T11:55:39Z", "original_author_association": "NONE"} -->
## Bug Description
Black produces different code on the second pass of the formatter when processing files with long type annotations and comments. This violates the idempotency guarantee.

## Expected Behavior
Black should produce identical output on consecutive passes.

Related to upstream-issue-4733.
