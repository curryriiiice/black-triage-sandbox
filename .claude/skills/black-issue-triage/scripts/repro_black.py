#!/usr/bin/env python3
"""Reproduce a reported Black formatting problem without executing the reporter's code.

Installs the requested Black release from PyPI (wheels only, so no package build scripts
run) into a throw-away virtualenv, feeds a code block extracted from the issue to
`black -` on stdin, then formats the result a second time to check stability. Black only
parses its input; the snippet is never imported or executed.

Usage (from the repository root):
  python3 .claude/skills/black-issue-triage/scripts/repro_black.py --block 1 --version 25.9.0
  python3 .../repro_black.py --block 2 --version as-of --preview --target-version py314

`--version as-of` means "the latest Black release that existed when the issue was opened".
Versions released after the issue was opened are refused (no hindsight in replays).
Only an allow-list of Black options is accepted. Prints one JSON object on stdout.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import subprocess
import sys
import venv
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from triage_common import DEFAULT_TRIAGE_DIR, MARKER, audit, load_json, parse_version  # noqa: E402

PIP_TIMEOUT = 180
BLACK_TIMEOUT = 60
TARGET_VERSIONS = {f"py3{i}" for i in range(3, 16)}

# outcome -> labels a maintainer would normally apply (the model still decides)
SUGGESTED_LABELS = {
    "crash": ["C: crash"],
    "not_equivalent": ["C: crash"],
    "invalid_code": ["C: invalid code"],
    "unstable": ["C: unstable formatting"],
    "parse_error": ["C: parser"],
    "reformatted": [],
    "unchanged": [],
}


def build_black_args(ns: argparse.Namespace) -> list[str]:
    args: list[str] = []
    if ns.preview:
        args.append("--preview")
    if ns.unstable:
        args.append("--unstable")
    for feat in ns.enable_unstable_feature or []:
        if not feat.replace("_", "").isalnum():
            raise SystemExit(f"{MARKER} refused unstable feature name {feat!r}")
        args += ["--enable-unstable-feature", feat]
    for tv in ns.target_version or []:
        if tv not in TARGET_VERSIONS:
            raise SystemExit(f"{MARKER} refused target version {tv!r}")
        args += ["--target-version", tv]
    if ns.line_length is not None:
        if not 1 <= ns.line_length <= 1000:
            raise SystemExit(f"{MARKER} refused line length {ns.line_length}")
        args += ["--line-length", str(ns.line_length)]
    if ns.skip_string_normalization:
        args.append("--skip-string-normalization")
    if ns.skip_magic_trailing_comma:
        args.append("--skip-magic-trailing-comma")
    if ns.pyi:
        args.append("--pyi")
    return args


def strip_preview(args: list[str]) -> list[str]:
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a == "--enable-unstable-feature":
            skip = True
            continue
        if a not in {"--preview", "--unstable"}:
            out.append(a)
    return out


def classify(rc: int, stderr: str, src: str, out: str) -> str:
    if rc == 0:
        return "unchanged" if out == src else "reformatted"
    low = stderr.lower()
    if "cannot parse" in low:
        return "parse_error"
    if "second pass" in low or "unstable formatting" in low:
        return "unstable"
    if "produced invalid code" in low:
        return "invalid_code"
    if "not equivalent to the source" in low:
        return "not_equivalent"
    return "crash"


def resolve_version(requested: str, ctx: dict[str, Any] | None) -> tuple[str | None, str | None]:
    """Return (version, error). Enforces 'released on or before the issue date'."""
    known = (ctx or {}).get("black_releases_as_of_issue") or []
    if requested == "as-of":
        latest = (ctx or {}).get("latest_black_release_as_of_issue")
        return (latest, None) if latest else (None, "no release list in context.json")
    if parse_version(requested) is None:
        return None, f"{requested!r} is not a final Black release number"
    if known:
        norm = {parse_version(v): v for v in known}
        if parse_version(requested) not in norm:
            return None, (f"Black {requested} had not been released when the issue was opened "
                          f"(latest then: {known[-1]}); refusing to use hindsight")
        return norm[parse_version(requested)], None
    return requested, None


def ensure_black(version: str, triage_dir: Path) -> Path:
    env_dir = triage_dir / "venvs" / f"black-{version}"
    exe = env_dir / "bin" / "black"
    if exe.exists():
        return exe
    venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)
    reqs = [f"black=={version}"]
    if parse_version(version) < (22, 3, 0):
        reqs.append("click<8.1")  # old Black releases break with click>=8.1
    cmd = [str(env_dir / "bin" / "python"), "-m", "pip", "install", "--quiet",
           "--disable-pip-version-check", "--only-binary=:all:", *reqs]
    subprocess.run(cmd, check=True, timeout=PIP_TIMEOUT, capture_output=True, text=True)
    return exe


def run_black(exe: Path, args: list[str], src: str) -> tuple[int, str, str]:
    """Run Black isolated from any pyproject.toml / user config (only explicit flags count).

    Without this, Black would pick up the configuration of the repository the agent runs
    in (this sandbox's own pyproject.toml sets target-version and `unstable = true`).
    """
    iso = exe.parent.parent / "isolated-cwd"
    iso.mkdir(exist_ok=True)
    cfg = iso / "empty-black-config.toml"
    if not cfg.exists():
        cfg.write_text("[tool.black]\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BLACK_")}
    env.update(NO_COLOR="1", XDG_CONFIG_HOME=str(iso), HOME=str(iso))
    proc = subprocess.run([str(exe), "--quiet", "--config", str(cfg), *args, "-"], input=src,
                          capture_output=True, text=True, timeout=BLACK_TIMEOUT, cwd=iso,
                          env=env)
    return proc.returncode, proc.stdout, proc.stderr


def udiff(a: str, b: str, name_a: str, name_b: str, limit: int = 4000) -> str:
    d = "".join(difflib.unified_diff(a.splitlines(True), b.splitlines(True), name_a, name_b))
    return d if len(d) <= limit else d[:limit] + "\n... (diff truncated)\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Safely reproduce a Black formatting report.")
    src_group = ap.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--block", type=int, help="code block number from context.md")
    src_group.add_argument("--snippet-file", help="file under the triage dir holding the code")
    ap.add_argument("--version", required=True, help="exact Black release, or 'as-of'")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--unstable", action="store_true")
    ap.add_argument("--enable-unstable-feature", action="append")
    ap.add_argument("-t", "--target-version", action="append")
    ap.add_argument("-l", "--line-length", type=int)
    ap.add_argument("-S", "--skip-string-normalization", action="store_true")
    ap.add_argument("-C", "--skip-magic-trailing-comma", action="store_true")
    ap.add_argument("--pyi", action="store_true")
    ap.add_argument("--triage-dir", default=str(DEFAULT_TRIAGE_DIR))
    ns = ap.parse_args(argv)
    triage_dir = Path(ns.triage_dir)
    ctx = load_json(triage_dir / "context.json")
    black_args = build_black_args(ns)

    if ns.block is not None:
        src_path = triage_dir / "blocks" / f"block_{ns.block}.txt"
    else:
        src_path = Path(ns.snippet_file).resolve()
        if triage_dir.resolve() not in src_path.parents:
            raise SystemExit(f"{MARKER} snippet file must live under {triage_dir}")
    if not src_path.is_file():
        raise SystemExit(f"{MARKER} no such code block/snippet: {src_path}")
    src = src_path.read_text(encoding="utf-8")

    result: dict[str, Any] = {"marker": MARKER, "source": str(src_path.name),
                              "requested_version": ns.version, "black_args": black_args,
                              "executed_snippet": False}
    version, err = resolve_version(ns.version, ctx)
    if err:
        result.update(outcome="refused", error=err)
    else:
        result["version"] = version
        try:
            exe = ensure_black(version, triage_dir)
            rc, out, stderr = run_black(exe, black_args, src)
            outcome = classify(rc, stderr, src, out)
            result.update(exit_code=rc, stderr=stderr[-2000:], diff=udiff(src, out, "input",
                                                                           "black-pass-1"))
            if rc == 0:
                rc2, out2, stderr2 = run_black(exe, black_args, out)
                if rc2 != 0 or out2 != out:
                    outcome = "unstable" if rc2 == 0 else classify(rc2, stderr2, out, out2)
                    result["second_pass"] = {"exit_code": rc2, "stderr": stderr2[-2000:],
                                             "diff": udiff(out, out2, "black-pass-1",
                                                           "black-pass-2")}
            suggested = list(SUGGESTED_LABELS.get(outcome, []))
            preview_flags = {"--preview", "--unstable", "--enable-unstable-feature"}
            if rc != 0 and preview_flags & set(black_args):
                # Control run without preview/unstable features: does the stable style work?
                stable_args = strip_preview(black_args)
                rc_c, _, stderr_c = run_black(exe, stable_args, src)
                result["control_without_preview"] = {"black_args": stable_args,
                                                     "exit_code": rc_c,
                                                     "stderr": stderr_c[-1000:]}
                if rc_c == 0:
                    result["note"] = ("fails only with preview/unstable features; the stable "
                                      "style handles this input, so the input is valid code")
                    if outcome == "parse_error":
                        outcome = "crash"
                    suggested = list(SUGGESTED_LABELS.get(outcome, [])) + ["C: preview style"]
            result["outcome"] = outcome
            result["suggested_labels"] = suggested
        except subprocess.CalledProcessError as exc:
            result.update(outcome="install_failed", error=(exc.stderr or str(exc))[-1500:])
        except subprocess.TimeoutExpired as exc:
            result.update(outcome="timeout", error=f"timed out: {exc.cmd[:2]}")
    audit(triage_dir, "repro", **{k: result.get(k) for k in
                                  ("source", "requested_version", "version", "black_args",
                                   "outcome", "exit_code", "error")})
    print(f"{MARKER} repro outcome: {result.get('outcome')}")
    print(json.dumps(result, indent=2))
    return 0 if result.get("outcome") not in {"refused", "install_failed", "timeout"} else 2


if __name__ == "__main__":
    sys.exit(main())
