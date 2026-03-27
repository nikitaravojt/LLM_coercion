import csv
import os
from datetime import datetime
from openai import OpenAI
from config import (
    NUM_ROUNDS, TARGET_MODEL, TARGET_TEMPERATURE,
    LOGGING_DIR, LOGGING_FILENAME, NARRATIVE_FILENAME, OPENAI_API_KEY,
)
from agents import TargetAgent, PressureAgent, JudgeAgent, generate_counter_position

client = OpenAI(api_key=OPENAI_API_KEY)


def run_episode(question, attack_type, mitigation, domain="", num_rounds=NUM_ROUNDS, on_progress=None):
    """
    Run one full episode.  Returns a dict with all results.
    on_progress(stage, **kwargs) is called at each key stage if provided.
    Stages: "initial", "pressure", "target", "judge", "round_done".
    """
    def notify(stage, **kwargs):
        if on_progress:
            on_progress(stage, **kwargs)

    target = TargetAgent(mitigation=mitigation)
    pressure = PressureAgent(attack_type=attack_type)
    judge = JudgeAgent()

    # round 0 — initial position
    notify("initial")
    initial_response = target.respond(question)

    # generate counter-position once from round 0 response — anchors all pressure rounds
    counter_position = generate_counter_position(question, initial_response, attack_type)

    convo_history = [
        {"role": "user", "content": question},
        {"role": "assistant", "content": initial_response},
    ]

    rounds = []

    for round_num in range(1, num_rounds + 1):
        # pressure attacks
        notify("pressure", round_num=round_num)
        attack_msg = pressure.attack(
            question=question,
            target_last_response=convo_history[-1]["content"],
            round_number=round_num,
            counter_position=counter_position,
        )

        convo_history.append({
            "role": "user",
            "content": f"Discussion Member 1: {attack_msg}",
        })

        # target responds with full history
        notify("target", round_num=round_num)
        messages = [{"role": "system", "content": target.system_prompt}] + convo_history
        raw = client.chat.completions.create(
            model=TARGET_MODEL,
            temperature=TARGET_TEMPERATURE,
            messages=messages,
        )
        target_response = raw.choices[0].message.content.strip()

        convo_history.append({
            "role": "assistant",
            "content": target_response,
        })

        # judge
        notify("judge", round_num=round_num)
        try:
            verdict = judge.classify(
                question=question,
                original_response=initial_response,
                current_response=target_response,
            )
        except ValueError:
            verdict = {"label": "MAINTAINED", "cds": 0, "reasoning": "JUDGE ERROR", "raw": ""}

        rounds.append({
            "round":            round_num,
            "pressure_message": attack_msg,
            "target_response":  target_response,
            "label":            verdict["label"],
            "cds":              verdict["cds"],
            "reasoning":        verdict["reasoning"],
        })

        notify("round_done", round_num=round_num, label=verdict["label"])

        if verdict["label"] == "REVERSED":
            break

    # compute metrics
    trajectory = [r["cds"] for r in rounds]
    rfc = None # capitulation round: first round where position is not maintained
    rfr = None # reversal round: first round where position is fully reversed
    for r in rounds:
        if rfc is None and r["label"] in ("HEDGED", "REVERSED"):
            rfc = r["round"]
        if rfr is None and r["label"] == "REVERSED":
            rfr = r["round"]

    return {
        "question":          question,
        "domain":            domain,
        "attack_type":       attack_type,
        "mitigation":        mitigation,
        "initial_response":  initial_response,
        "rounds":            rounds,
        "final_label":       rounds[-1]["label"] if rounds else "MAINTAINED",
        "rfc":               rfc,
        "rfr":               rfr,
        "max_cds":           max(trajectory) if trajectory else 0,
        "trajectory":        trajectory,
    }


def run_batch(questions, attack_type, mitigation, num_rounds=NUM_ROUNDS):
    """
    Run an episode for each question.
    questions: list of dicts with at least "text" key, optionally "domain", "source".
    Returns list of episode result dicts.
    """
    results = []
    for i, q in enumerate(questions):
        print(f"  [{i+1}/{len(questions)}] {q.get('domain', '')} — running...")
        result = run_episode(
            question=q["text"],
            attack_type=attack_type,
            mitigation=mitigation,
            domain=q.get("domain", ""),
            num_rounds=num_rounds,
        )
        print(f"    -> {result['final_label']}  RFC={result['rfc']}  traj={result['trajectory']}")
        results.append(result)
    return results


def log_episode_narrative(result, directory=LOGGING_DIR, filename=NARRATIVE_FILENAME):
    """Append a human-readable narrative of one episode to episodes.log."""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)

    W = 80
    divider  = "═" * W
    thin_div = "─" * W
    icons    = {"MAINTAINED": "✓", "HEDGED": "~", "REVERSED": "✗"}

    lines = []
    lines.append(divider)
    lines.append(f"  EPISODE  —  {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")
    lines.append(f"  Question   : {result['question']}")
    lines.append(f"  Domain     : {result['domain']}")
    lines.append(f"  Attack     : {result['attack_type']}")
    lines.append(f"  Mitigation : {result['mitigation']}")
    lines.append(divider)

    lines.append("")
    lines.append("  ROUND 0 — Initial Position")
    lines.append(thin_div)
    lines.append("  TARGET:")
    for ln in result["initial_response"].splitlines():
        lines.append(f"    {ln}")

    for rd in result["rounds"]:
        lines.append("")
        lines.append(f"  ROUND {rd['round']}")
        lines.append(thin_div)
        lines.append("  PRESSURE:")
        for ln in rd["pressure_message"].splitlines():
            lines.append(f"    {ln}")
        lines.append("")
        lines.append("  TARGET:")
        for ln in rd["target_response"].splitlines():
            lines.append(f"    {ln}")
        lines.append("")
        lines.append(f"  JUDGE:  {icons.get(rd['label'], '?')} {rd['label']}  (CDS={rd['cds']})")
        for ln in rd["reasoning"].splitlines():
            lines.append(f"    {ln}")

    lines.append("")
    lines.append(divider)
    lines.append(f"  VERDICT:  {icons.get(result['final_label'], '?')} {result['final_label']}  |  RFC: {result['rfc']}  |  RFR: {result['rfr']}  |  Trajectory: {result['trajectory']}")
    lines.append(divider)
    lines.append("")

    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return path


def log_results_csv(results, directory=LOGGING_DIR, filename=LOGGING_FILENAME):
    """Append episode summaries to CSV. Creates file + header if needed."""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    file_exists = os.path.isfile(path)

    fieldnames = [
        "question", "domain", "attack_type", "mitigation",
        "final_label", "rfc", "rfr", "max_cds", "trajectory",
        "initial_response",
    ]

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for r in results:
            writer.writerow({
                "question":          r["question"][:120],
                "domain":            r["domain"],
                "attack_type":       r["attack_type"],
                "mitigation":        r["mitigation"],
                "final_label":       r["final_label"],
                "rfc":               r["rfc"],
                "rfr":               r["rfr"],
                "max_cds":           r["max_cds"],
                "trajectory":        str(r["trajectory"]),
                "initial_response":  r["initial_response"][:200],
            })
    return path
