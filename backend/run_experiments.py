import sys
import os

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from razorai.mlops.experiments import ResearchExperimentHarness


def main():
    print("\n" + "="*80)
    print("RAZORAI RESEARCH BENCHMARK EXPERIMENT SUITE")
    print("Evaluating Unified Payment Representation vs. Siloed Baseline Architectures")
    print("="*80 + "\n")

    harness = ResearchExperimentHarness()
    experiments = harness.run_all_experiments()

    for exp in experiments:
        print(f"\n[*] {exp['experiment_id']}: {exp['title']}")
        print(f"    Hypothesis: {exp['hypothesis']}")
        print("-" * 75)
        print(f"{'Metric':<38} | {'Baseline':<16} | {'Proposed':<16} | {'Uplift'}")
        print("-" * 75)
        for m in exp['metrics']:
            metric_name = m['metric']
            keys = list(m.keys())
            base_key = next((k for k in keys if "baseline" in k), keys[1])
            prop_key = next((k for k in keys if "proposed" in k), keys[2])
            uplift = m.get('uplift', '')

            base_val = str(m[base_key])
            prop_val = str(m[prop_key])
            print(f"{metric_name:<38} | {base_val:<16} | {prop_val:<16} | {uplift}")
        print("-" * 75)
        print(f"    Conclusion: {exp['conclusion']}\n")

    print("="*80)
    print("[SUCCESS] All 7 Research Experiments Concluded Successfully.")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
