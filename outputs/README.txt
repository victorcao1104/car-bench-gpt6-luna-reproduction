CAR-bench Disambiguation consistency replication
Experiment date: 2026-10-19 Pacific/Auckland
Start with report.html. Raw trajectories and task snapshot are in outputs/.
The original benchmark repository is required at work/car-bench, commit ce6dc9d08f4ff81eb4c1a5c317aff25112ee950b.
Install its dependencies plus the recorded dependency versions into an isolated Python environment.
The runner reads the already configured local .env.local for OPENAI_API_KEY and GEMINI_API_KEY.
No credentials or private encryption keys are included in this bundle.
Run: python work/experiment.py --tasks 25 --jobs 3
Completed task files are skipped. Do not run a second process simultaneously: the cost guard is thread-safe, not multi-process.
Analysis: python work/analyze_experiment.py, then python work/build_report.py
Costs include the connectivity probes. OpenAI project hard limit is $10/month; local experimental guards are $9.50 OpenAI and $4.50 Gemini.
The local Gemini guard controls only calls made through this runner, not unrelated Google account usage.
This is a current-code replication with a Responses API adapter, not an exact historical code reproduction.
