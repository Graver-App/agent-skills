#!/usr/bin/env python3
"""Measure whether each skill's description reaches the requests it was written for.

Reads evals/triggers.json, generates one eval case per query in a temporary copy
of this plugin, runs `claude plugin eval` against it, and prints a table of
expected-vs-actual triggering plus false negatives and false positives.

Why not skill-creator's scripts/run_eval.py: it approximates a skill by writing a
slash command into .claude/commands/, on the premise that a command appears in
Claude's available_skills list. That no longer holds, so it systematically
under-reports. Measured on this repo: a query it scored 0/2 fires 2/2 here. See
BASELINE.md.

Usage:  python3 evals/run_triggers.py [--runs 1] [--skill NAME] [-j 4]
"""
import argparse, json, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def build(workdir: pathlib.Path, queries: list[dict]) -> dict:
    for sub in (".claude-plugin", "skills"):
        shutil.copytree(ROOT / sub, workdir / sub)
    index = {}
    for i, q in enumerate(queries):
        name = f"q{i:02d}"
        case = workdir / "evals" / name
        (case / "graders").mkdir(parents=True)
        (case / "prompt.md").write_text(
            "---\nmax_turns: 6\nallowed_tools: [Read, Glob, Grep, Skill]\nruns: 1\n---\n\n"
            + q["query"] + "\n")
        (case / "graders" / "skill-fired.md").write_text(
            "---\ntype: tool_used\ntool: Skill\n"
            f"input_match: '\"skill\"\\s*:\\s*\"(?:[\\w-]+:)?{q['skill']}\"'\n"
            "min: 1\n---\n\nDid this phrasing reach the skill?\n")
        index[name] = q
    return index


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--skill", help="only queries for this skill")
    ap.add_argument("-j", "--concurrency", type=int, default=4)
    args = ap.parse_args()

    queries = json.loads((ROOT / "evals" / "triggers.json").read_text())["queries"]
    if args.skill:
        queries = [q for q in queries if q["skill"] == args.skill]
    if not queries:
        print("no queries matched", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="graver-triggers-") as tmp:
        work = pathlib.Path(tmp)
        index = build(work, queries)
        out = work / "out.json"
        cmd = ["claude", "plugin", "eval", ".", "--ablation", "none",
               "--runs", str(args.runs), "--no-publish", "--trust-plugin",
               "-j", str(args.concurrency), "--json", str(out)]
        proc = subprocess.run(cmd, cwd=work, capture_output=True, text=True)
        if not out.exists():
            sys.stderr.write(proc.stdout + proc.stderr)
            return 1
        data = json.loads(out.read_text())

    rows = []
    for case in data["cases"]:
        q = index[case["name"]]
        runs = case["arms"]["with"]
        fired = sum(
            1 for r in runs
            if any(g["name"] == "skill-fired" and g["passed"] for g in r["graders"]))
        rate = fired / len(runs)
        ok = (rate >= 0.5) == q["should_trigger"]
        rows.append((q["skill"], q["should_trigger"], fired, len(runs), ok, q["query"]))
    rows.sort()

    skill = None
    for s, want, fired, total, ok, query in rows:
        if s != skill:
            print(f"\n### {s}")
            skill = s
        mark = "ok  " if ok else ("FALSE NEG" if want else "FALSE POS")
        print(f"  {mark:9} want={str(want):5} fired={fired}/{total}  {query[:64]}")

    print()
    bad = 0
    for s in sorted({r[0] for r in rows}):
        sub = [r for r in rows if r[0] == s]
        fn = sum(1 for r in sub if r[1] and not r[4])
        fp = sum(1 for r in sub if not r[1] and not r[4])
        bad += fn + fp
        print(f"{s:32} {sum(1 for r in sub if r[4])}/{len(sub)} correct  (FN {fn}, FP {fp})")
    print(f"\ncost ${data['costUsd']:.2f}  duration {data['durationSeconds']}s")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
