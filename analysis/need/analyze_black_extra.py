"""Extra need metrics for psf/black (read-only; input files produced by fetch_black_issues.py
and fetch of open issues).
Usage: python -I analyze_black_extra.py RAW.json OPEN_ISSUES.json OUT.json
Metrics:
- silent_closures: external non-bot issues closed with no non-author, non-bot comment ever
- closer/labeler concentration: share of close/label events by the top human actor
- open backlog (whole history, from OPEN_ISSUES.json = GET repos/psf/black/issues?state=open,
  PRs filtered out): count, zero-comment count, lacking any T:/C:/F:/S: label, lacking C:/F: label,
  age distribution.
"""
import json, sys, collections, statistics as st
from datetime import datetime, timezone
def t(s): return datetime.fromisoformat(s.replace("Z", "+00:00"))
def isbot(l, ty): return ty == "Bot" or (l or "").endswith("[bot]")
MAINT = {"OWNER", "MEMBER", "COLLABORATOR"}
raw = json.load(open(sys.argv[1])); opn = json.load(open(sys.argv[2]))
ext = [i for i in raw["issues"] if not isbot(i["user"], i["user_type"]) and i["author_association"] not in MAINT]
silent = [i["number"] for i in ext if i["state"] == "closed" and not any(
    c["user"] != i["user"] and not isbot(c["user"], c["user_type"]) for c in i["comments"])]
closes = collections.Counter(e["actor"] for i in ext for e in i["events"] if e["event"] == "closed" and e["actor"] != i["user"])
labels = collections.Counter(e["actor"] for i in ext for e in i["events"] if e["event"] == "labeled"
                             and e["actor"] != i["user"] and not isbot(e["actor"], e["actor_type"]))
spam = [i["number"] for i in ext if {"spam / ai", "spam"} & set(i["labels_now"])]
asof = datetime(2026, 10, 20, tzinfo=timezone.utc)
iss = [i for i in opn if "pull_request" not in i]
ages = sorted((asof - t(i["created_at"])).days for i in iss)
pref = lambda i, ps: any(l["name"].startswith(ps) for l in i["labels"])
out = {
 "window_external_n": len(ext),
 "silent_closures": {"n": len(silent), "share_of_external": round(len(silent) / len(ext), 3), "numbers": silent},
 "non_author_closes_total": sum(closes.values()), "top_closers": closes.most_common(4),
 "top_closer_share": round(closes.most_common(1)[0][1] / sum(closes.values()), 3),
 "non_author_human_label_events": sum(labels.values()), "top_labelers": labels.most_common(4),
 "top_labeler_share": round(labels.most_common(1)[0][1] / sum(labels.values()), 3),
 "spam_labelled": spam,
 "open_backlog": {"as_of": "2026-10-20", "open_issues": len(iss),
   "zero_comments": sum(i["comments"] == 0 for i in iss),
   "no_T_C_F_S_label": sum(not pref(i, ("T:", "C:", "F:", "S:")) for i in iss),
   "no_C_or_F_label": sum(not pref(i, ("C:", "F:")) for i in iss),
   "only_T_bug_label": sum([l["name"] for l in i["labels"]] == ["T: bug"] for i in iss),
   "S_needs_repro_or_awaiting": sum(pref(i, ("S: needs repro", "S: awaiting response")) for i in iss),
   "median_age_days": st.median(ages), "older_than_365d": sum(a > 365 for a in ages)},
}
json.dump(out, open(sys.argv[3], "w"), indent=1); print(json.dumps(out, indent=1))
