"""Compute triage-need metrics from black_issues_raw.json.
Usage: python -I analyze_black_need.py RAW.json AS_OF(YYYY-MM-DD) OUT.json
Definitions:
- bot: user type 'Bot' or login ending in '[bot]'
- first human response: earliest comment by a non-author, non-bot account
- first maintainer response: earliest comment with author_association in
  OWNER/MEMBER/COLLABORATOR (non-author)
- first triage action: earliest of (non-author non-bot comment, label/close event
  by a non-author non-bot actor). Labels added by the author at creation
  (issue-template labels) are NOT triage.
- unresponded issues are right-censored at AS_OF.
"""
import json, sys, statistics as st
from datetime import datetime, timezone

MAINT = {"OWNER", "MEMBER", "COLLABORATOR"}
def t(s): return datetime.fromisoformat(s.replace("Z", "+00:00"))
def isbot(login, typ): return typ == "Bot" or (login or "").endswith("[bot]")

raw = json.load(open(sys.argv[1])); asof = datetime.fromisoformat(sys.argv[2]).replace(tzinfo=timezone.utc)
rows = []
for i in raw["issues"]:
    a, c0 = i["user"], t(i["created_at"])
    if isbot(a, i["user_type"]): continue
    hum = [t(c["created_at"]) for c in i["comments"] if c["user"] != a and not isbot(c["user"], c["user_type"])]
    mnt = [t(c["created_at"]) for c in i["comments"] if c["user"] != a and c["assoc"] in MAINT]
    botc = [t(c["created_at"]) for c in i["comments"] if isbot(c["user"], c["user_type"])]
    tri_ev = [t(e["created_at"]) for e in i["events"]
              if e["event"] in ("labeled", "closed", "unlabeled", "marked_as_duplicate")
              and e["actor"] and e["actor"] != a and not isbot(e["actor"], e["actor_type"])]
    tmpl = sorted({e["label"] for e in i["events"] if e["event"] == "labeled" and e["actor"] == a
                   and abs((t(e["created_at"]) - c0).total_seconds()) < 60})
    triage_labels = sorted({e["label"] for e in i["events"] if e["event"] == "labeled" and e["actor"] != a
                            and not isbot(e["actor"], e["actor_type"])})
    first = lambda xs: (min(xs) - c0).total_seconds() / 86400 if xs else None
    rows.append({"number": i["number"], "created_at": i["created_at"], "author_is_maintainer": i["author_association"] in MAINT,
                 "first_human_days": first(hum), "first_maint_days": first(mnt), "first_bot_days": first(botc),
                 "first_triage_days": first(hum + tri_ev), "template_labels": tmpl, "triage_labels": triage_labels,
                 "labels_now": i["labels_now"], "state": i["state"], "state_reason": i["state_reason"],
                 "age_days": (asof - c0).total_seconds() / 86400})

def summ(key, subset):
    vals = [r[key] for r in subset if r[key] is not None]
    none = [r for r in subset if r[key] is None]
    return {"n": len(subset), "responded": len(vals), "never": len(none),
            "median_days_responded_only": round(st.median(vals), 2) if vals else None,
            "p75_days_responded_only": round(sorted(vals)[int(0.75 * (len(vals) - 1))], 2) if vals else None,
            "share_within_1d": round(sum(v <= 1 for v in vals) / len(subset), 3),
            "share_within_7d": round(sum(v <= 7 for v in vals) / len(subset), 3),
            "share_none_after_7d": round(sum(1 for r in subset if (r[key] is None or r[key] > 7) and r["age_days"] > 7) / len(subset), 3)}

ext = [r for r in rows if not r["author_is_maintainer"]]
out = {"meta": raw["meta"], "as_of": sys.argv[2], "n_all_nonbot": len(rows), "n_external": len(ext),
       "external": {k: summ(k, ext) for k in ("first_human_days", "first_maint_days", "first_triage_days")},
       "all": {k: summ(k, rows) for k in ("first_human_days", "first_maint_days", "first_triage_days")}}
# Template-label accuracy: template said T: bug, maintainers later applied something conflicting
conf = {"R: not a bug", "T: style", "T: user support", "T: enhancement", "T: documentation", "R: duplicate", "R: invalid", "spam / ai"}
tb = [r for r in ext if "T: bug" in r["template_labels"]]
out["template_T_bug"] = {"n": len(tb), "later_relabelled_conflicting": sum(1 for r in tb if set(r["triage_labels"]) & conf),
                         "labels_now_still_T_bug": sum(1 for r in tb if "T: bug" in r["labels_now"])}
out["no_component_label_now"] = sum(1 for r in ext if not any(l.startswith(("C:", "F:")) for l in r["labels_now"]))
out["open_now"] = sum(1 for r in ext if r["state"] == "open")
out["open_now_only_template_or_none"] = sum(1 for r in ext if r["state"] == "open" and not r["triage_labels"])
out["label_counts_triage"] = {}
for r in ext:
    for l in r["triage_labels"]: out["label_counts_triage"][l] = out["label_counts_triage"].get(l, 0) + 1
out["label_counts_triage"] = dict(sorted(out["label_counts_triage"].items(), key=lambda x: -x[1]))
json.dump({"summary": out, "rows": rows}, open(sys.argv[3], "w"), indent=1)
print(json.dumps(out, indent=1))
