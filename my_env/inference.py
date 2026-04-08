"""
E-commerce Platform Manager — LLM Inference Loop

Uses an OpenAI-compatible API (e.g. Grok via x.ai) to autonomously
play the e-commerce environment.

Usage:
    # Set your API key first
    set HF_TOKEN=your_api_key_here

    # Run (defaults to Grok API)
    python inference.py

    # Or specify a custom base URL
    python inference.py --base-url https://api.openai.com/v1 --model gpt-4

Environment variables:
    HF_TOKEN  — API key for the LLM provider
"""

import argparse
import json
import os
import sys
import time

import requests

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: pip install openai")
    sys.exit(1)

# ──────────────────── Config ─────────────────────────
ENV_API = "http://localhost:8000"
DEFAULT_BASE_URL = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-3-latest"

SYSTEM_PROMPT = """\
You are an expert e-commerce platform manager AI. You manage an online store
with multiple products. Your goal is to MAXIMIZE PROFIT while keeping
CUSTOMER SATISFACTION high.

On each turn you receive the current state (products with price, cost, stock,
demand, competitor_price; plus global metrics). You must respond with a JSON
action containing exactly three keys:

1. "pricing" — a dict mapping each product name to one of: "increase", "decrease", "keep"
2. "inventory" — a dict mapping each product name to true (restock) or false (skip)
3. "marketing" — one of: "run_ads", "influencer", "no_campaign"

Rules & tips:
- Increasing price reduces demand; decreasing price increases demand.
- Restocking costs money (product cost × 30 units).
- "run_ads" costs $200 and boosts demand; "influencer" costs $350 and boosts satisfaction.
- Stockouts hurt satisfaction. Overpriced products (>15% above competitor) hurt satisfaction.
- Reward = profit×0.6 + satisfaction×50 − stockout_penalty − overspending_penalty

Respond with ONLY valid JSON, no markdown fences, no explanation.
"""


def build_user_prompt(state: dict) -> str:
    """Format the environment observation into a user prompt."""
    return (
        "Current environment state:\n"
        f"```json\n{json.dumps(state, indent=2)}\n```\n\n"
        "Provide your action as JSON."
    )


def parse_action(response_text: str, product_names: list) -> dict:
    """Parse the LLM response into a valid action dict."""
    # Strip markdown fences if present
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        action = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: do nothing
        print(f"  ⚠ Could not parse LLM response, using default action.")
        action = {
            "pricing": {name: "keep" for name in product_names},
            "inventory": {name: False for name in product_names},
            "marketing": "no_campaign",
        }

    # Validate and fill missing keys
    if "pricing" not in action:
        action["pricing"] = {name: "keep" for name in product_names}
    if "inventory" not in action:
        action["inventory"] = {name: False for name in product_names}
    if "marketing" not in action:
        action["marketing"] = "no_campaign"

    return action


def main():
    parser = argparse.ArgumentParser(description="E-commerce LLM Inference Loop")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OpenAI-compatible API base URL")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name to use")
    parser.add_argument("--max-steps", type=int, default=30, help="Maximum number of steps")
    parser.add_argument("--env-url", default=ENV_API, help="Environment API base URL")
    args = parser.parse_args()

    api_key = os.getenv("HF_TOKEN")
    if not api_key:
        print("Error: HF_TOKEN environment variable not set.")
        print("  Set it with:  set HF_TOKEN=your_api_key_here")
        sys.exit(1)

    client = OpenAI(
        api_key=api_key,
        base_url=args.base_url,
    )

    print(f"🛒 E-commerce Platform Manager — LLM Inference")
    print(f"   Model:    {args.model}")
    print(f"   API:      {args.base_url}")
    print(f"   Env:      {args.env_url}")
    print(f"   Steps:    {args.max_steps}")
    print("=" * 60)

    # Reset environment
    print("\n🔄 Resetting environment...")
    try:
        resp = requests.post(f"{args.env_url}/reset", timeout=10)
        reset_data = resp.json()
    except Exception as exc:
        print(f"❌ Could not connect to environment: {exc}")
        print("   Make sure the FastAPI server is running on", args.env_url)
        sys.exit(1)

    obs = reset_data.get("observation", reset_data)
    total_reward = 0.0
    total_profit = 0.0

    for step_num in range(1, args.max_steps + 1):
        print(f"\n{'─' * 60}")
        print(f"📅 Day {step_num}")

        product_names = list(obs.get("products", {}).keys())

        # Build prompt & call LLM
        user_msg = build_user_prompt(obs)

        try:
            completion = client.chat.completions.create(
                model=args.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                max_tokens=512,
            )
            llm_response = completion.choices[0].message.content
        except Exception as exc:
            print(f"  ⚠ LLM call failed: {exc}")
            llm_response = "{}"

        # Parse action
        action = parse_action(llm_response, product_names)
        print(f"  🎮 Action: {json.dumps(action, indent=4)}")

        # Step environment
        try:
            resp = requests.post(
                f"{args.env_url}/step",
                json=action,
                timeout=10,
            )
            step_data = resp.json()
        except Exception as exc:
            print(f"  ❌ Step failed: {exc}")
            break

        obs = step_data.get("observation", step_data)
        reward = step_data.get("reward", 0.0)
        done = step_data.get("done", False)

        total_reward += reward
        total_profit += obs.get("profit", 0.0)

        # Print summary
        print(f"  💰 Profit:       ${obs.get('profit', 0):.2f}")
        print(f"  😊 Satisfaction: {obs.get('customer_satisfaction', 0):.2%}")
        print(f"  💵 Budget:       ${obs.get('budget', 0):,.2f}")
        print(f"  🏆 Reward:       {reward:.2f}")

        if done:
            print(f"\n🏁 Simulation complete!")
            break

        # Small delay to avoid rate limits
        time.sleep(0.5)

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"📊 FINAL RESULTS")
    print(f"   Total Reward: {total_reward:.2f}")
    print(f"   Total Profit: ${total_profit:,.2f}")
    print(f"   Final Satisfaction: {obs.get('customer_satisfaction', 0):.2%}")
    print(f"   Final Budget: ${obs.get('budget', 0):,.2f}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
