# CAR-bench: GPT-6 Luna Reproduction

[English report (PDF)](outputs/extension/CAR-bench_Corrected_First3_Report_EN.pdf) | [English report (HTML)](outputs/extension/comparison-report-en.html) | [Presentation](outputs/CAR_bench_presentation_safety_insight.pptx)

Success and consistency across Base, Hallucination and Disambiguation tasks, using the official CAR-bench environment and saved historical GPT-5 results. The experiment was completed in October 2026.

The corrected primary analysis uses **the first three trials for both models**, following the authors' analysis functions. Six-run combinatorial estimates are supplementary only. Recalculation and report preparation incurred no additional model API charges.

## Experiment setup

- Agent: GPT-6 Luna with medium reasoning.
- Simulated user and scoring: Gemini 2.5 Flash, using the benchmark's prompts and scoring pipeline.
- Current test split: 50 Base, 50 Hallucination and 25 Disambiguation tasks.
- Official code: [CAR-bench/car-bench](https://github.com/CAR-bench/car-bench), commit `ce6dc9d08f4ff81eb4c1a5c317aff25112ee950b`.
- Dataset: [johanneskirmayr/car-bench-dataset](https://huggingface.co/datasets/johanneskirmayr/car-bench-dataset), revision `1fcf24ad802c42e04a0d8fe05b5ca0d481a4e7af`.

All 125 tasks have six complete repetitions, giving 750 balanced trials. An incomplete seventh round adds 41 Base and 43 Hallucination trials, for 834 stored valid trials in total. The primary analysis uses only 375 trials: trial IDs `0`, `1` and `2` for each task. Budget interruptions are not counted as model failures.

## Primary results: first three trials

| Task type | Tasks | All stored valid trials | Pass@1 | Pass@3 | Pass^3 |
|---|---:|---:|---:|---:|---:|
| Base | 50 | 341 | 76.0% | 84.0% | 58.0% |
| Hallucination | 50 | 343 | 66.0% | 78.0% | 50.0% |
| Disambiguation | 25 | 150 | 68.0% | 80.0% | 40.0% |

- **Pass@1:** proportion of tasks successful on the first trial only.
- **Pass@3:** proportion successful at least once in the first three trials.
- **Pass^3:** proportion successful in all three trials.

The consistency gap is Pass@3 minus Pass^3. It must be interpreted alongside success rates: a task that always fails also has a zero gap.

An earlier analysis used a multi-run average for Pass@1 and five-run combinatorial estimates for historical GPT-5. The corrected analysis follows the first-trial/first-three-trial implementation in the authors' `analyze_results.py` and `analyze_results_v2.py`. Previous values are explicitly marked as superseded in the [correction audit](outputs/extension/metric-correction-audit.json).

## Historical comparison on identical tasks

The current task snapshots differ from some definitions stored with the historical results. A shared task ID does not guarantee an identical task. We retain only matching task definitions without historical infrastructure errors. Both models use trial IDs `0`, `1` and `2`.

| Task type | Matched tasks | Luna Pass^3 | Historical GPT-5 Pass^3 | Difference (pp) | Paired 95% CI (pp) |
|---|---:|---:|---:|---:|---:|
| Base | 48 | 58.3% | 66.7% | -8.3 | -22.9 to +6.2 |
| Hallucination | 45 | 51.1% | 60.0% | -8.9 | -24.4 to +4.4 |
| Disambiguation | 19 | 42.1% | 47.4% | -5.3 | -31.6 to +21.1 |

Intervals use 10,000 paired task-bootstrap resamples with seed 769. All intervals cross zero, so this sample does not establish a clear improvement or deterioration in consistency. This is not evidence of equivalence. Historical code, model-service, simulator and judge conditions were not fully controlled, so differences cannot be attributed solely to a model upgrade.

The report separately shows the paper's Table 4 as descriptive context. Those aggregate values use a different evaluation population and are not a matched-task comparison.

![Historical comparison on identical tasks](outputs/extension/matched-comparison.png)

![Success counts in the first three trials](outputs/extension/consistency-distribution.png)

## Supplementary analysis: six-run combinations

| Task type | Complete runs | Mean success per run | Estimated Pass@3 | Estimated Pass^3 |
|---|---:|---:|---:|---:|
| Base | 6 | 75.3% | 87.1% | 61.5% |
| Hallucination | 6 | 66.0% | 77.3% | 53.3% |
| Disambiguation | 6 | 56.7% | 75.8% | 37.8% |

These estimates average all 20 three-trial combinations of six Luna runs. The supplementary historical comparison averages all 10 combinations of five GPT-5 runs. For a task with `c` successes in `n` runs:

```text
Estimated Pass^3 = C(c, 3) / C(n, 3)
Estimated Pass@3 = 1 - C(n - c, 3) / C(n, 3)
```

Here `C(a, 3) = 0` when `a < 3`. Results are averaged equally across tasks. Mean success per run is `c / n`; it differs from primary Pass@1, which uses the first trial only. Supplementary values do not replace the primary comparison.

Additional trials followed a fixed schedule rather than outcome-based selection. Base and Hallucination were stopped during round seven at the experiment owner's request. Disambiguation was subsequently completed through round six. Partial seventh-round results are excluded from balanced supplementary estimates.

## Interpretation and deployment insight

The replication shows persistent inconsistency: Disambiguation Pass@3 is 80%, while Pass^3 is 40%. A successful run does not establish repeatable behavior. No reasoning-disabled control was run, so the experiment does not isolate the effect of reasoning.

Hallucination task failures are not a direct measurement of fabrication rates. Invalid tool use, task deviation and other scoring conditions can also cause failure. User simulation and scoring remain imperfect, and there was no full independent human relabelling.

The presentation proposes enforcing critical safety policies through an independent rule-based layer. The paper itself discusses external rule-based safety layers in Section 7, Limitations (PDF page 10, printed page 40608). Our powered-door-release illustration is a deployment example, not a benchmark trial. The hypothetical 1% unsafe-action rate on that slide is not an experimental result. Neither a gated agent nor the effectiveness of such a safety layer was evaluated in this replication.

## Recorded costs and budget controls

| Provider | Cumulative estimated cost (USD) |
|---|---:|
| OpenAI | $0.930797 |
| Gemini | $4.989678 |
| Total | $5.920475 |

The totals include the original Disambiguation experiment and a conservative $0.078386 reservation for three interrupted or failed requests without returned usage data. These requests were not treated as free. Provider billing remains authoritative.

The local OpenAI early-stop threshold was $9.50 under a requested $10 budget. Gemini initially had a $5 budget; a later NZ$10 top-up authorization increased its local threshold conservatively to US$9.50. The supplement stopped when six rounds were complete rather than exhausting the remaining funds. Local guards apply to this runner and do not control unrelated account usage or configure provider-side limits.

`outputs/usage-ledger.json` records the initial experiment. `outputs/extension/usage-ledger.json` includes that entire ledger as a prefix plus later calls. **Do not add the two ledgers together.**

## Reproduce the analysis without API calls

Use a Python environment with the dependencies recorded in this repository. From the repository root:

```bash
python work/analyze_extension.py
python work/plot_extension.py
python work/verify_first_three.py
python work/build_english_report.py
```

These commands analyze saved trajectories, regenerate figures, verify metrics against the authors' functions, and build the English report. They do not require model API credentials. Plotting requires NumPy and Matplotlib; English PDF generation requires ReportLab. Verification uses the included historical results and correction snapshots.

Paid experiment entry points are separate: `work/extend_experiment.py` and `work/supplement_disambiguation.py`. They require locally configured credentials and can incur API charges. Read their budget and stopping conditions before use. Do not run competing experiment processes against the same ledger. No credentials are included in this repository.

## Evidence and downloads

- [English PDF report](outputs/extension/CAR-bench_Corrected_First3_Report_EN.pdf)
- [English HTML report](outputs/extension/comparison-report-en.html)
- [Presentation](outputs/CAR_bench_presentation_safety_insight.pptx)
- [Metric summary and confidence intervals](outputs/extension/summary.json)
- [Per-task results](outputs/extension/per-task-results.csv)
- [Trial index](outputs/extension/trial-index.csv)
- [Task-definition audit](outputs/extension/task-definition-audit.json)
- [Historical matched-task results](outputs/extension/historical-matched.json)
- [First-three-trial verification](outputs/extension/first-three-verification.json)
- [Raw-data and ledger hashes](outputs/extension/immutable-data-sha256.json)
- [Cumulative cost ledger](outputs/extension/usage-ledger.json)
- [Execution and stopping events](outputs/extension/events.jsonl)
- [Provenance](evidence/provenance.json) and [file checksums](evidence/checksums.sha256)

PNG/SVG figures and raw trial files are included under `outputs/`. Original trajectories and cost ledgers were preserved through the metric correction. Some archived reports and slides describe the repository as private because they were produced before publication; that access note is historical.
