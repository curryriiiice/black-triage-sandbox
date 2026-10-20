<!-- triage-replay: {"case_id": "c15", "original_created_at": "2026-07-01T05:53:22Z", "original_author_association": "NONE"} -->
**Is this related to a problem? Please describe.**
Two small wording issues in `docs/usage_and_configuration/the_basics.md`:

1. Line 600: "instead of **laborously** listing every file or directory" — 
   "laborously" is not a word; it should be "laboriously."

2. Line 501: "Unix-like (Linux, **MacOS**, etc.)" uses incorrect capitalization. 
   Apple's official branding is "macOS," and that's the spelling used consistently 
   everywhere else in the docs (docs/faq.md, docs/integrations/editors.md, 
   docs/usage_and_configuration/file_collection_and_discovery.md). This file is the 
   only place using "MacOS."

**Describe the solution you'd like**

```diff
- instead of laborously listing every file or directory. You can get started by heading
+ instead of laboriously listing every file or directory. You can get started by heading
```

```diff
- Unix-like (Linux, MacOS, etc.): `$XDG_CONFIG_HOME/black` (`~/.config/black` if the
+ Unix-like (Linux, macOS, etc.): `$XDG_CONFIG_HOME/black` (`~/.config/black` if the
```

**Describe alternatives you've considered**
None needed — these are direct text corrections with no ambiguity.

**Additional context**
Both are minor polish items but affect the same file, so bundling them into one PR/issue keeps the diff small and easy to review.
