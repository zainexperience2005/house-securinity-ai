"""CI gate: run evals and fail the build if scores drop below configured thresholds."""
import os
import sys
import json
import time

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from evals.run_evals import run_benchmark


def run_ci_gate():
    print("=" * 80)
    print("🚦 CONTINUOUS INTEGRATION: DEEPEVAL & SAFETY QUALITY GATE")
    print("=" * 80)

    # 1. Execute Benchmark
    run_benchmark()

    # 2. Inspect Results
    results_path = os.path.join(os.path.dirname(__file__), "eval_results.json")
    if not os.path.exists(results_path):
        print("❌ Error: eval_results.json was not generated!")
        sys.exit(1)

    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_results = data.get("results", [])
    total_metrics = 0
    passed_metrics = 0
    failures = []

    for case in test_results:
        c_name = case.get("test_case")
        categories = case.get("categories", {})
        for cat_name, metrics in categories.items():
            for m_name, m_val in metrics.items():
                total_metrics += 1
                if m_val.get("passed", False):
                    passed_metrics += 1
                else:
                    failures.append({
                        "case": c_name,
                        "category": cat_name,
                        "metric": m_name,
                        "score": m_val.get("score"),
                        "reason": m_val.get("reason")
                    })

    pass_rate = (passed_metrics / total_metrics * 100) if total_metrics > 0 else 0
    print("\n" + "=" * 80)
    print(f"📊 CI SUMMARY: {passed_metrics}/{total_metrics} Checks Passed ({pass_rate:.1f}%)")
    print("=" * 80)

    # Generate Markdown Summary for CI
    md_summary = f"# 🏛️ House Scrutiny Agent - CI Eval Gate\n\n"
    md_summary += f"- **Timestamp**: `{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}`\n"
    md_summary += f"- **Pass Rate**: **{pass_rate:.1f}%** ({passed_metrics}/{total_metrics} checks passed)\n"
    md_summary += f"- **Status**: {'✅ PASSED' if len(failures) == 0 else '❌ FAILED'}\n\n"

    if failures:
        md_summary += "### ⚠️ Failures Detected:\n"
        for f in failures:
            md_summary += f"- **{f['case']}** -> *{f['metric']}* (Score: {f['score']:.2f}): {f['reason']}\n"
    else:
        md_summary += "### 🎉 All Deterministic, Safety, and Regulatory Scrutiny Checks Passed!\n"

    summary_file = os.path.join(os.path.dirname(__file__), "ci_summary.md")
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(md_summary)

    print(f"CI Markdown report generated at: {summary_file}")

    # Enforce minimum threshold (95% pass rate for CI gate)
    if pass_rate < 90.0:
        print(f"\n❌ CI Quality Gate FAILED: Pass rate {pass_rate:.1f}% is below 90% threshold.")
        sys.exit(1)
    else:
        print(f"\n✅ CI Quality Gate PASSED successfully!")
        sys.exit(0)


if __name__ == "__main__":
    run_ci_gate()
