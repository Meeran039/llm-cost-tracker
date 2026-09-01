"""
Takes the pattern-finder's structured output and asks Groq's LLM to write
a plain-English recommendation, constrained to reason only from the given
numbers, not external claims about model quality it can't verify.
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


def generate_recommendation(pattern_summary: dict, client: Groq | None = None) -> str:
    if pattern_summary["total_calls"] == 0:
        return "No usage logged yet. Log a few calls via POST /usage/log to get a recommendation."

    client = client or Groq(api_key=os.getenv("GROQ_API_KEY"))

    prompt = f"""You are a cost-optimization advisor. You are given ONLY the
following real, aggregated usage data for one user. Do not claim anything
about model quality, capability, or behavior that isn't directly implied
by these numbers -- you have no way to verify such claims. Stick to what
the cost and call-volume data itself supports.

DATA:
- Total calls logged: {pattern_summary['total_calls']}
- Total cost: ${pattern_summary['total_cost_usd']}
- Average cost per call: ${pattern_summary['avg_cost_per_call']}
- Highest-spend provider: {pattern_summary['highest_spend_provider']}
- Breakdown by provider: {pattern_summary['by_provider']}

Write a 2-3 sentence plain-English observation about their spending pattern
and one concrete, data-grounded suggestion. Do not invent model-quality claims.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=200,
    )
    content = response.choices[0].message.content
    if not content:
        return "Couldn't generate a recommendation right now, please try again."
    return content