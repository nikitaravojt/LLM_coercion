# Deliberation Chamber

A basic experiment framework for measuring sycophancy in LLMs - the tendency of a model to reverse a correct answer under social pressure rather than reasoned argument.

## Overview

A **target model** answers a multiple-choice question. A **pressure agent** then challenges that answer across up to three escalating rounds using one of three social pressure personas, without providing any factual reasoning. Reversal is detected by comparing the answer letter before and after pressure.

Three pressure conditions are tested:

| Condition | Persona |
|---|---|
| `baseline` | Bare contradiction, no persona ("I don't think that's right") |
| `authority` | Subject-matter expert expressing credentialled disappointment |
| `consensus` | Group representative conveying social isolation |

A fourth condition (`authority_citation`) modifies authority with fabricated academic citations and is used for normative (MoralChoice) runs only.

A **judge agent** (GPT-4o-mini) is also implemented for open-ended question classification (MAINTAINED / HEDGED / REVERSED) but is not used in the main MCQ pipeline, which uses letter extraction instead.

## Datasets

| Dataset | File | Questions | Type |
|---|---|---|---|
| SycophancyEval | `data/syco_eval_filtered.jsonl` | 2,254 | MCQ with ground truth (math, MMLU, AQUA-RAT) |
| MoralChoice (high ambiguity) | `data/moralchoice_high.json` | 680 | Normative dilemmas, no ground truth |

TruthfulQA and TriviaQA subsets are excluded from SycophancyEval as they lack unambiguous correct answers.

## Models tested

| Model | Dataset | n |
|---|---|---|
| gpt-3.5-turbo | SycophancyEval | 100 |
| gpt-3.5-turbo | MoralChoice | 100 |
| gpt-4o-mini | SycophancyEval | 50 |
| gpt-4o-mini | MoralChoice | 50 |
| gpt-4.1-mini | SycophancyEval | 30 |
| gpt-4.1-mini | MoralChoice | 30 |

All target runs use temperature 0 and seed 200 for reproducibility. Pressure agent runs at temperature 0.7.

## Setup

```
pip install openai python-dotenv
```

Add your OpenAI key to a `.env` file:

```
OPENAI_API_KEY=sk-...
```

## Running an experiment

```bash
# SycophancyEval
python run_pilot.py --logfile syceval_run.log --num_questions 50 --seed 200 --sycophancyeval

# MoralChoice
python run_pilot.py --logfile normative_run.log --num_questions 50 --seed 200 --moralchoice high

# Full responses in log (verbose)
python run_pilot.py --logfile run.log --num_questions 10 --seed 200 --sycophancyeval --verbose
```

Each run produces a `.log` (human-readable episode transcript) and a `.json` (structured results) in `results/`.

## Analysing results

```bash
python helpers/analyse.py results/syceval_gpt35_n100.json
```

Outputs: per-condition reversal rates, R0 accuracy, sycophancy susceptibility, round-of-reversal breakdown, and a per-question vulnerability profile.

## Structure

```
run_pilot.py              — experiment runner
agents.py                 — PressureAgent, JudgeAgent
prompts.py                — system prompts and templates for all agents
config.py                 — model names, temperatures, intensity schedule

data/
  syco_eval_filtered.jsonl    — filtered SycophancyEval dataset
  moralchoice_high.json       — parsed MoralChoice (high ambiguity)
  raw_data/                   — original source files

helpers/
  analyse.py                  — metrics and analysis from JSON results
  aqua_parser.py              — converts raw SycophancyEval JSONL to experiment format
  moralchoice_parser.py       — converts MoralChoice CSV to experiment format

results/                  — all experiment outputs (.log + .json)
logs/                     — early pilot runs
results.md                — development notes
```
