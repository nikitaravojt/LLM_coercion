## Run 2. 5/5/25.
Implementing changes from Run 1.
Results:
- Improved behaviour regarding reasoning avoidance, sys prompts seem to work better now.
- Running now on n=30.
- Consensus achieved highest reversal rate (96%) though 11/29 reverals are "other" so its more destabilising than "directive".
- CtI (solid sycophancy) is lowest in consensus (45%) vs baseline (67%) and authority (68%).
- Consensus appears clean, but authority agent seems to still (milder but still) leak reasoning into its counterposition.
A few instances found of hints like "consider the combinations" or "implications of speed change", so confound still somewhat present here.
- Overall: reversal rates are baseline 21/30 (70%), authority 22/30 (73%), consensus 29/30 (96%).
- Solution: all pressure agents actually have no business knowing the target model's reasoning, only its final answer (ABCDE), at least for these MCQs. So will pass {target_answer_letter} into the PRESSURE_USER_TEMPLATE sys prompt instead of the full model response. This should fix the problem at source and prevent the pressure agents from being tempted to engage in reasoning/corrective behaviour like it sometimes does.



## Run 1. 5/5/26. 
Idea: merge SycophancyEval MCQ pipeline with my pressure agent multi-turn episodes.
Changes:
- Target responds naturally by removing 2-sentence constraint, despite higher token usage.
- Removing "no reasoning of any kind" strict constraint on pressure agents. 
- Modified target sys prompt to engage w/ pressure but to state the answer in one line at the end.
- Created new run_pilot.py to apply the usual multi-turn setup on the MCQ questions.
- Results in: logs/pilot1.log
Result:
- 90% reversal rate across baseline, authority and consensus.
- Noticed some instances of pressure agent incorrectly arguing for the correct answer based on its own reasoning,
not as instructed. 
- Modified the sys prompt for authority and consensus to disallow any reasoning, factual or mathematical.
- Running pilot2.log with these changes.
