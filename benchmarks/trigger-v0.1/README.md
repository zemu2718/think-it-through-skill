# Trigger benchmark v0.1

This snapshot records automatic Skill-discovery results from the official Skill Creator `run_eval.py` runner.

| Set | Description | Positive recall | Negative specificity | Overall |
| --- | --- | ---: | ---: | ---: |
| Dev (initial) | Pre-final; failures were used once to revise the description | 1/8 | 8/8 | 9/16 |
| Holdout | Final frozen description; never fed back into v0.1 tuning | 1/8 | 8/8 | 9/16 |

The final description is bound in `summary.json` by SHA-256. Each query was run exactly once. The session-wide 50-agent limit prevented a second dev run after revision, so the initial dev score must not be interpreted as the final description's dev score.

**Release conclusion:** the Skill avoided every close negative in both sets, but automatic positive recall was only 1/8 on the frozen holdout. The v0.1 discovery gate therefore **did not pass**. Direct `/think-it-through` invocation and source installation remain usable, while automatic loading needs another version and a fresh-session evaluation budget.

Files:

- `dev-initial.json` — initial description, tuning set;
- `holdout.json` — frozen final description, untouched holdout;
- `summary.json` — hashes, counts, runner details, and limitations.
