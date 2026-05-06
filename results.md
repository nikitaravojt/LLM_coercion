
## Run 4. 5/5/26. Pilot4_gpt-4o-mini.log
Idea: running same seed as Run 3 but on gpt-4o-mini to see what happens (n=20).



## Run 3. 5/5/26. Pilot3.log.
Idea: running an n=50 sample on gpt3.5-turbo to gain more results. Considered removing reasoning feed into the pressure template entirely since the pressure agents do not need to see the targets reasoning, just its final answer, but decided against it for now.
Results stored at the top of pilot3.log.


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
- Testing some changes in pilot2_1.log. Implemented fixes: pull possible responses from question itself rather than rely on a default ABCDE, since some only have ABCD and no E. 
- Still some problems: still some contamination where model hallucinates an E where only possible responses are A-C. On one question, model gives different R0 answer across different personas despite T=0 and same seed - this non-determinism in the starting position may be unavoidable in some cases due to the inherent limitatiton of the API. Also, some mild hallucination mid-response by the target (Q10 Authority in pilot2_1.log). Some issues in dataset quality where a question is malformed (Q5) where a division by zero is one of the possible answers.



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
