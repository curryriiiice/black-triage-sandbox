import json

import prefetch_context as pc

REPLAY_BODY = (
    '<!-- triage-replay: {"case_id": "c1", "original_created_at": "2025-10-06T12:00:00Z", '
    '"original_author_association": "NONE"} -->\n'
    "**Describe the bug**\nBlack crashes with fmt: skip\n\n"
    "```python\nif x: pass  # fmt: skip\n```\n\n"
    "```sh\n$ black file.py --preview --target-version py312\n```\n\n"
    "- Black's version: 25.9.0\n"
)

PYPI = {"releases": {
    "25.1.0": [{"upload_time_iso_8601": "2025-01-29T10:00:00Z"}],
    "25.9.0": [{"upload_time_iso_8601": "2025-09-18T10:00:00Z"}],
    "25.11.0": [{"upload_time_iso_8601": "2025-11-09T10:00:00Z"}],
    "26.1a1": [{"upload_time_iso_8601": "2025-12-07T10:00:00Z"}],
    "19.3b0": [{"upload_time_iso_8601": "2019-03-14T10:00:00Z"}],
    "0.0": [],
}}


def issue(number=10, body=REPLAY_BODY, assoc="OWNER", labels=(), **kw):
    d = {"number": number, "title": "Crash with fmt: skip in preview", "body": body,
         "state": "open", "author_association": assoc, "created_at": "2026-10-20T00:00:00Z",
         "user": {"login": "someone", "type": "User"},
         "labels": [{"name": n} for n in labels]}
    d.update(kw)
    return d


def test_replay_header_parsed_and_stripped():
    meta, body = pc.parse_replay_header(REPLAY_BODY)
    assert meta["original_author_association"] == "NONE"
    assert "triage-replay" not in body and body.startswith("**Describe the bug**")


def test_malformed_replay_header_is_still_stripped():
    meta, body = pc.parse_replay_header("<!-- triage-replay: {not json} -->\nhello")
    assert meta is None and body == "hello"


def test_code_blocks_and_hints():
    _, body = pc.parse_replay_header(REPLAY_BODY)
    blocks = pc.extract_code_blocks(body)
    assert [b["lang"] for b in blocks] == ["python", "sh"]
    assert blocks[0]["code"] == "if x: pass  # fmt: skip\n"
    hints = pc.extract_hints(body)
    assert hints["reported_version"] == "25.9.0"
    assert "--preview" in hints["flags_seen_in_commands"]
    assert hints["mentions_preview"] is True


def test_releases_as_of_excludes_future_and_prereleases():
    rel = pc.releases_as_of(PYPI, "2025-10-06T12:00:00Z")
    assert [r["version"] for r in rel] == ["25.1.0", "25.9.0"]


def test_decide_skip_rules():
    assert pc.decide_skip(issue(), "MEMBER", False).startswith("issue was opened by a maintainer")
    assert "bot" in pc.decide_skip(issue(), "NONE", True)
    assert "pull request" in pc.decide_skip(issue(pull_request={}), "NONE", False)
    assert "not open" in pc.decide_skip(issue(state="closed"), "NONE", False)
    assert "triage labels" in pc.decide_skip(issue(labels=["C: crash"]), "NONE", False)
    # the template-applied type label alone does not count as triaged
    assert pc.decide_skip(issue(labels=["T: bug"]), "NONE", False) is None


def test_replay_mode_uses_header_only_when_enabled():
    ctx, _ = pc.build_context(issue(), [], [], PYPI, replay_mode=True)
    assert ctx["skip"] is False and ctx["issue"]["author_association"] == "NONE"
    assert ctx["issue"]["created_at"] == "2025-10-06T12:00:00Z"
    assert ctx["latest_black_release_as_of_issue"] == "25.9.0"
    assert "triage-replay" not in ctx["issue"]["body"]
    # Production mode ignores a (possibly forged) header: real association OWNER -> skip
    ctx2, _ = pc.build_context(issue(), [], [], PYPI, replay_mode=False)
    assert ctx2["skip"] is True and "maintainer" in ctx2["skip_reason"]
    assert "triage-replay" not in ctx2["issue"]["body"]


def test_rank_duplicates_only_earlier_issues_and_no_prs():
    me = issue(number=10)
    pool = [
        {"number": 4, "title": "Crash with fmt: skip in preview mode", "body": "fmt: skip crash",
         "state": "open", "labels": []},
        {"number": 12, "title": "Crash with fmt: skip in preview", "body": "later issue",
         "state": "open", "labels": []},
        {"number": 5, "title": "Crash with fmt: skip", "body": "", "state": "open",
         "labels": [], "pull_request": {}},
        {"number": 3, "title": "Docs typo in README", "body": "typo", "state": "open",
         "labels": []},
    ]
    _, body = pc.parse_replay_header(REPLAY_BODY)
    cands = pc.rank_duplicates(me, body, pool)
    assert [c["number"] for c in cands] == [4]
    assert "fmt: skip" in cands[0]["shared_signals"]


def test_main_offline_writes_context_and_noop(tmp_path, monkeypatch):
    f = tmp_path / "in"
    f.mkdir()
    (f / "issue.json").write_text(json.dumps(issue(assoc="COLLABORATOR", body="hi")))
    (f / "labels.json").write_text(json.dumps([{"name": "C: crash"}]))
    (f / "issues.json").write_text("[]")
    (f / "pypi.json").write_text(json.dumps(PYPI))
    outputs = tmp_path / "safeoutputs" / "outputs.jsonl"
    monkeypatch.setenv("GH_AW_SAFE_OUTPUTS", str(outputs))
    monkeypatch.setenv("TRIAGE_REPLAY_MODE", "false")
    out = tmp_path / "triage"
    rc = pc.main(["--out", str(out), "--issue-json", str(f / "issue.json"),
                  "--labels-json", str(f / "labels.json"), "--issues-json",
                  str(f / "issues.json"), "--pypi-json", str(f / "pypi.json")])
    assert rc == 0
    ctx = json.loads((out / "context.json").read_text())
    assert ctx["skip"] is True
    noop = json.loads(outputs.read_text().splitlines()[0])
    assert noop["type"] == "noop" and "maintainer" in noop["message"]
    assert "untrusted" in (out / "context.md").read_text()
    assert (out / "skill_audit.jsonl").exists()


def test_main_offline_no_noop_for_external_issue(tmp_path, monkeypatch):
    f = tmp_path / "issue.json"
    f.write_text(json.dumps(issue(number=7)))
    for name, data in (("l.json", []), ("i.json", []), ("p.json", PYPI)):
        (tmp_path / name).write_text(json.dumps(data))
    outputs = tmp_path / "outputs.jsonl"
    monkeypatch.setenv("GH_AW_SAFE_OUTPUTS", str(outputs))
    monkeypatch.setenv("TRIAGE_REPLAY_MODE", "true")
    out = tmp_path / "triage"
    pc.main(["--out", str(out), "--issue-json", str(f), "--labels-json", str(tmp_path / "l.json"),
             "--issues-json", str(tmp_path / "i.json"), "--pypi-json", str(tmp_path / "p.json")])
    assert not outputs.exists()
    assert (out / "blocks" / "block_1.txt").read_text() == "if x: pass  # fmt: skip\n"


INLINE_BODY = (
    "black fails when parsing a valid f string:\n\n"
    "```\nBlack produced invalid code: f-string: expecting '}'\n```\n\n"
    "`f\"Processing {data['type']}: {data['id']}\"`\n\n"
    "I ran `black --preview x.py` with `pyproject.toml` on `25.9.0`; also `x = 1` is fine.\n"
)


def test_inline_snippets_extracted_with_heuristics():
    snips = pc.extract_inline_snippets(INLINE_BODY)
    assert [s["code"] for s in snips] == ["f\"Processing {data['type']}: {data['id']}\"\n",
                                          "x = 1\n"]
    assert snips[0]["file"] == "inline_1.txt"


def test_inline_spans_inside_fences_ignored():
    body = "```python\nx = `y = 1`\n```\n"
    assert pc.extract_inline_snippets(body) == []


def test_looks_like_python_rejects_non_code():
    for t in ("--preview", "pyproject.toml", "26.1.0", "black file.py", "fmt: skip", "foo",
              "https://example.org/a", "src/black/linegen.py"):
        assert not pc.looks_like_python(t), t
    for t in ("print(x)", "except (A, B):", "a[1:2]", "r'\\d+'", "x = 1"):
        assert pc.looks_like_python(t), t


def test_main_writes_inline_files(tmp_path, monkeypatch):
    f = tmp_path / "issue.json"
    f.write_text(json.dumps(issue(number=8, body=INLINE_BODY, assoc="NONE")))
    for name, data in (("l.json", []), ("i.json", []), ("p.json", PYPI)):
        (tmp_path / name).write_text(json.dumps(data))
    monkeypatch.delenv("GH_AW_SAFE_OUTPUTS", raising=False)
    monkeypatch.setenv("TRIAGE_REPLAY_MODE", "false")
    out = tmp_path / "triage"
    pc.main(["--out", str(out), "--issue-json", str(f), "--labels-json", str(tmp_path / "l.json"),
             "--issues-json", str(tmp_path / "i.json"), "--pypi-json", str(tmp_path / "p.json")])
    assert (out / "blocks" / "inline_1.txt").read_text().startswith('f"Processing')
    assert (out / "blocks" / "block_1.txt").exists()
    ctx = json.loads((out / "context.json").read_text())
    assert len(ctx["inline_snippets"]) == 2 and len(ctx["code_blocks"]) == 1
    assert "--inline N" in (out / "context.md").read_text()



def test_duplicate_pool_excludes_bot_and_agentic_workflow_issues():
    me = issue(number=10)
    _, body = pc.parse_replay_header(REPLAY_BODY)
    same = {"title": "Crash with fmt: skip in preview mode", "body": "fmt: skip crash",
            "state": "open"}
    pool = [
        dict(same, number=2, user={"login": "github-actions[bot]", "type": "Bot"}, labels=[]),
        dict(same, number=3, user={"login": "someone", "type": "User"},
             labels=[{"name": "agentic-workflows"}]),
        dict(same, number=4, user={"login": "github-actions", "type": "User"}, labels=[]),
        dict(same, number=5, user={"login": "reporter", "type": "User"}, labels=[]),
    ]
    assert [c["number"] for c in pc.rank_duplicates(me, body, pool)] == [5]
    assert pc.is_automation_issue(pool[0]) and pc.is_automation_issue(pool[1])
    assert not pc.is_automation_issue(pool[3])
