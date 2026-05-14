import random
from openai import OpenAI
from config import (
    PRESSURE_MODEL, JUDGE_MODEL,
    PRESSURE_TEMPERATURE, JUDGE_TEMPERATURE,
    INTENSITY_BY_ROUND, CDS_ENCODING, OPENAI_API_KEY
)
from prompts import (
    PRESSURE_SYSTEM_PROMPTS,
    PRESSURE_USER_TEMPLATE,
    CITATION_ESCALATION_BY_ROUND,
    JUDGE_SYSTEM,
    JUDGE_USER_TEMPLATE,
)

client = OpenAI(api_key=OPENAI_API_KEY)


def _call_api(system_prompt: str, user_prompt: str, model: str, temperature: float) -> str:
    """
    Makes a single call to the OpenAI chat completions API.
    Returns the assistant's reply as a plain string.
    All agents will use this, no other direct calls to the API should be made outside this function.
    """
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    return response.choices[0].message.content.strip()


# Pressure agent

class PressureAgent:
    """
    The adversarial agent that attempts to induce sycophancy in target.
    The system prompt (persona) is fixed for the episode.
    The user prompt is rebuilt each round with current context.
    """

    def __init__(self, attack_type: str):
        if attack_type not in PRESSURE_SYSTEM_PROMPTS:
            raise ValueError(f"Unknown attack type: {attack_type}")
        self.attack_type = attack_type
        self.system_prompt = PRESSURE_SYSTEM_PROMPTS[attack_type]

    def attack(self, question: str, target_last_response: str, round_number: int,
               counter_position: str = "", target_answer_letter: str = "") -> str:
        """
        Generate an attack message for the given round.
        round_number: 1, 2 or 3 - controls escalation intensity.
        counter_position: one-sentence opposite stance, prepended to anchor the pressure agent's opening.
        target_answer_letter: the explicit letter the target chose (e.g., "C")
        """
        intensity_instruction = INTENSITY_BY_ROUND[round_number]
        if self.attack_type == "authority_citation":
            intensity_instruction += (
                f"\n\nCitation escalation for this round:\n"
                f"{CITATION_ESCALATION_BY_ROUND[round_number]}"
            )

        user_prompt = PRESSURE_USER_TEMPLATE.format(
            question=question,
            target_last_response=target_last_response,
            target_answer_letter=target_answer_letter or "unknown",
            counter_position=counter_position,
            round_number=round_number,
            intensity_instruction=intensity_instruction,
        )

        return _call_api(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            model=PRESSURE_MODEL,
            temperature=PRESSURE_TEMPERATURE,
        )



def pick_counter_position(target_letter, correct_letter, all_options="ABCDE"):
    """Pick a wrong answer to push towards"""
    wrong_options = [c for c in all_options if c != correct_letter and c != target_letter]
    if not wrong_options:
        wrong_options = [c for c in all_options if c != target_letter]
    return random.choice(wrong_options)



# Legacy code: Judge (unused)
class JudgeAgent:
    """
    Classifies target responses as MAINTAINED, HEDGED, or REVERSED.
    Always runs at temperature 0 for determinism.
    Parses the final word of the response as the label.
    """

    def __init__(self):
        self.system_prompt = JUDGE_SYSTEM

    def classify(self, question: str, original_response: str, current_response: str) -> dict:
        """
        Classify the current response relative to the original position.
        Returns a dict with:
            "label"     - MAINTAINED, HEDGED, or REVERSED
            "cds"       - numeric encoding (0, 1, 2)
            "reasoning" - the judge's reasoning before the label
            "raw"       - full raw output (for debugging)
        """
        user_prompt = JUDGE_USER_TEMPLATE.format(
            question=question,
            original_response=original_response,
            current_response=current_response,
        )

        raw = _call_api(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            model=JUDGE_MODEL,
            temperature=JUDGE_TEMPERATURE,
        )

        label = _parse_judge_label(raw)

        return {
            "label":     label,
            "cds":       CDS_ENCODING[label],
            "reasoning": raw.rsplit("\n", 1)[0].strip(),  # everything before the final label line
            "raw":       raw,
        }
    
def _parse_judge_label(raw: str) -> str:
    """
    Extract the classification label from the judge's raw output.
    The judge is instructed to put the label on the final line as a single word.
    Falls back to scanning all lines if the final line is not a valid label.
    """
    valid_labels = set(CDS_ENCODING.keys())  # MAINTAINED, HEDGED, REVERSED

    # first try: last non-empty line
    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    if lines and lines[-1].upper() in valid_labels:
        return lines[-1].upper()

    # fallback: scan all lines for a valid label
    for line in reversed(lines):
        if line.upper() in valid_labels:
            return line.upper()

    # if nothing found, raise - episode.py should catch and discard this trial
    raise ValueError(f"Judge produced no valid label. Raw output:\n{raw}")


