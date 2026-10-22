import json
import os

import pytest

import repro_black as rb

CTX = {"black_releases_as_of_issue": ["25.1.0", "25.9.0"],
       "latest_black_release_as_of_issue": "25.9.0",
       "issue": {"created_at": "2025-10-06T19:26:28Z"}}


def args(*argv):
    ap_ns = rb.argparse.Namespace(preview=False, unstable=False, enable_unstable_feature=None,
                                  target_version=None, line_length=None,
                                  skip_string_normalization=False,
                                  skip_magic_trailing_comma=False, pyi=False)
    for k, v in argv:
        setattr(ap_ns, k, v)
    return ap_ns


def test_black_args_allowlist():
    assert rb.build_black_args(args(("preview", True), ("target_version", ["py312"]))) == [
        "--preview", "--target-version", "py312"]
    with pytest.raises(SystemExit):
        rb.build_black_args(args(("target_version", ["py27; rm -rf /"])))
    with pytest.raises(SystemExit):
        rb.build_black_args(args(("enable_unstable_feature", ["x --config /etc/passwd"])))
    with pytest.raises(SystemExit):
        rb.build_black_args(args(("line_length", 0)))


@pytest.mark.parametrize("rc,stderr,expected", [
    (123, "Python 3.12 cannot parse code formatted for Python 3.14", "env_limit"),
    (123, "error: cannot format -: Cannot parse for target version", "parse_error"),
    (123, "INTERNAL ERROR: Black produced different code on the second pass", "unstable"),
    (123, "INTERNAL ERROR: Black produced invalid code: ...", "invalid_code"),
    (123, "INTERNAL ERROR: Black produced code that is not equivalent to the source",
     "not_equivalent"),
    (123, "Traceback ... KeyError", "crash"),
])
def test_classify_errors(rc, stderr, expected):
    assert rb.classify(rc, stderr, "x", "") == expected


def test_strip_preview():
    assert rb.strip_preview(["--preview", "--enable-unstable-feature", "x", "-l", "80",
                             "--unstable"]) == ["-l", "80"]


def test_classify_success():
    assert rb.classify(0, "", "x = 1\n", "x = 1\n") == "unchanged"
    assert rb.classify(0, "", "x=1\n", "x = 1\n") == "reformatted"


def test_resolve_version_refuses_hindsight():
    assert rb.resolve_version("as-of", CTX) == ("25.9.0", None)
    assert rb.resolve_version("25.1", CTX) == ("25.1.0", None)
    v, err = rb.resolve_version("26.10.1", CTX)
    assert v is None and "refusing to use hindsight" in err
    assert rb.resolve_version("main", CTX)[1]
    # fail closed when the trusted release list is missing or empty
    assert rb.resolve_version("25.9.0", {})[0] is None
    assert rb.resolve_version("25.9.0", None)[1].startswith("no trusted release list")


def test_only_prefetched_sources_accepted(tmp_path):
    (tmp_path / "context.json").write_text(json.dumps(CTX))
    with pytest.raises(SystemExit):
        rb.main(["--snippet-file", "/etc/hosts", "--version", "25.9.0",
                 "--triage-dir", str(tmp_path)])


def test_missing_cutoff_refuses(tmp_path):
    ctx = {k: v for k, v in CTX.items() if k != "issue"}
    (tmp_path / "context.json").write_text(json.dumps(ctx))
    (tmp_path / "blocks").mkdir()
    (tmp_path / "blocks" / "block_1.txt").write_text("x=1\n")
    assert rb.main(["--block", "1", "--version", "25.9.0", "--triage-dir", str(tmp_path)]) == 2
    rec = json.loads((tmp_path / "skill_audit.jsonl").read_text().splitlines()[-1])
    assert rec["outcome"] == "refused" and "creation date" in rec["error"]


def test_env_limit_when_target_newer_than_interpreter(tmp_path, monkeypatch):
    (tmp_path / "context.json").write_text(json.dumps(CTX))
    (tmp_path / "blocks").mkdir()
    (tmp_path / "blocks" / "block_1.txt").write_text("try:\n    pass\nexcept A, B:\n    pass\n")
    monkeypatch.setattr(rb, "ensure_black", lambda v, d, c: (tmp_path / "bin" / "black", []))
    stderr = ("error: cannot format -: failed to verify equivalence of the formatted output: "
              "Python 3.12 cannot parse code formatted for Python 3.14.")
    monkeypatch.setattr(rb, "run_black", lambda exe, a, src: (123, "", stderr))
    rb.main(["--block", "1", "--version", "25.9.0", "-t", "py314", "--triage-dir", str(tmp_path)])
    rec = json.loads((tmp_path / "skill_audit.jsonl").read_text().splitlines()[-1])
    assert rec["outcome"] == "env_limit"


def test_refused_version_is_audited(tmp_path, capsys):
    (tmp_path / "context.json").write_text(json.dumps(CTX))
    (tmp_path / "blocks").mkdir()
    (tmp_path / "blocks" / "block_1.txt").write_text("x=1\n")
    assert rb.main(["--block", "1", "--version", "26.10.1", "--triage-dir", str(tmp_path)]) == 2
    rec = json.loads((tmp_path / "skill_audit.jsonl").read_text().splitlines()[-1])
    assert rec["event"] == "repro" and rec["outcome"] == "refused"


@pytest.mark.skipif(os.environ.get("RUN_NETWORK_TESTS") != "1",
                    reason="installs Black from PyPI; set RUN_NETWORK_TESTS=1")
@pytest.mark.parametrize("code,flags,expected", [
    ("x=1\n", [], "reformatted"),
    ("x = 1\n", [], "unchanged"),
    ("def f(:\n    pass\n", [], "parse_error"),
    # valid code that only the 25.9.0 preview style fails to parse -> preview crash
    ('with open("f") as f: content = f.read()  # fmt: skip\n', ["--preview"], "crash"),
])
def test_real_black_install_and_run(tmp_path, code, flags, expected):
    (tmp_path / "context.json").write_text(json.dumps(CTX))
    (tmp_path / "blocks").mkdir()
    (tmp_path / "blocks" / "block_1.txt").write_text(code)
    rc = rb.main(["--block", "1", "--version", "25.9.0", "--triage-dir", str(tmp_path), *flags])
    rec = json.loads((tmp_path / "skill_audit.jsonl").read_text().splitlines()[-1])
    assert rc == 0 and rec["outcome"] == expected and rec["version"] == "25.9.0"


@pytest.mark.skipif(os.environ.get("RUN_NETWORK_TESTS") != "1",
                    reason="installs Black from PyPI; set RUN_NETWORK_TESTS=1")
def test_repro_ignores_project_config_in_cwd(tmp_path, monkeypatch):
    """A pyproject.toml in the working directory must not change the reproduction."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "pyproject.toml").write_text("[tool.black]\nline-length = 10\n")
    monkeypatch.chdir(proj)
    td = tmp_path / "triage"
    (td / "blocks").mkdir(parents=True)
    (td / "context.json").write_text(json.dumps(CTX))
    (td / "blocks" / "block_1.txt").write_text("x = [1, 2, 3]\n")
    rb.main(["--block", "1", "--version", "25.9.0", "--triage-dir", str(td)])
    rec = json.loads((td / "skill_audit.jsonl").read_text().splitlines()[-1])
    assert rec["outcome"] == "unchanged"



def test_inline_source_selected(tmp_path):
    (tmp_path / "context.json").write_text(json.dumps(CTX))
    (tmp_path / "blocks").mkdir()
    (tmp_path / "blocks" / "inline_1.txt").write_text("x=1\n")
    # refused version -> no install needed, but the inline file must be found and audited
    assert rb.main(["--inline", "1", "--version", "26.10.1", "--triage-dir", str(tmp_path)]) == 2
    rec = json.loads((tmp_path / "skill_audit.jsonl").read_text().splitlines()[-1])
    assert rec["source"] == "inline_1.txt"
    with pytest.raises(SystemExit):
        rb.main(["--inline", "2", "--version", "25.9.0", "--triage-dir", str(tmp_path)])


@pytest.mark.skipif(os.environ.get("RUN_NETWORK_TESTS") != "1",
                    reason="installs Black from PyPI; set RUN_NETWORK_TESTS=1")
def test_relative_triage_dir_and_inline_snippet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "triage" / "blocks").mkdir(parents=True)
    (tmp_path / "triage" / "context.json").write_text(json.dumps(CTX))
    (tmp_path / "triage" / "blocks" / "inline_1.txt").write_text('f"{a[\'b\']}"\n')
    assert rb.main(["--inline", "1", "--version", "25.9.0", "--triage-dir", "triage"]) == 0
    rec = json.loads((tmp_path / "triage" / "skill_audit.jsonl").read_text().splitlines()[-1])
    assert rec["outcome"] in {"unchanged", "reformatted"}



@pytest.mark.skipif(os.environ.get("RUN_NETWORK_TESTS") != "1",
                    reason="installs Black from PyPI; set RUN_NETWORK_TESTS=1")
def test_dependencies_resolved_as_of_issue_date_c06(tmp_path):
    """Round-1 c06: with today's pytokens the bug is hidden; as of 2026-01-07 it reproduces."""
    ctx = {"black_releases_as_of_issue": ["25.12.0"], "latest_black_release_as_of_issue": "25.12.0",
           "issue": {"created_at": "2026-01-07T19:30:39Z"}}
    (tmp_path / "context.json").write_text(json.dumps(ctx))
    (tmp_path / "blocks").mkdir()
    (tmp_path / "blocks" / "block_1.txt").write_text("if True:\n    foo = 1+\\\n2\n    print(foo)\n")
    rb.main(["--block", "1", "--version", "25.12.0", "-t", "py313", "--triage-dir", str(tmp_path)])
    rec = json.loads((tmp_path / "skill_audit.jsonl").read_text().splitlines()[-1])
    pins = {p.split("==")[0].lower(): p.split("==")[1] for p in rec["resolved"] if "==" in p}
    assert pins["black"] == "25.12.0" and pins["pytokens"].startswith("0.3")
    assert rec["outcome"] == "parse_error" and rec["dependency_cutoff"] == "2026-01-07T19:30:39Z"
