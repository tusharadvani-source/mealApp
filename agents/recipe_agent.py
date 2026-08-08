"""Recipe agent: proposes and revises a week of meals.

Design #3 (Agent loop) for this role:
  Observes  - David's cuisine picks, calorie target (or weight/goal to derive one),
              cooking pattern, disliked-meal/eating-out feedback.
  Decides   - which recipes to select and how to schedule them across cooking days.
  Produces  - a proposed week of recipes with per-day calorie totals.
  Checks    - no dish repeats within the week (or the 1-week/4-week memory windows),
              plan roughly fits the calorie target, no cheat meals unless David asked.

v1 uses MOCK_RECIPES via a search_recipes tool in place of the Spoonacular API
(Discovery: "Synthetic data plan"). Swapping in the real API later means replacing
only the search_recipes tool body -- this function's contract stays the same.
"""

import json
import os

import anthropic
from anthropic import beta_tool

from data.mock_recipes import MOCK_RECIPES, all_cuisines

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """You are the recipe-planning agent for a weekly meal-planning assistant.

Rules you must always follow:
- Only propose recipes matching the user's selected cuisines.
- Never repeat a dish within the same week's plan.
- Never propose a recipe listed under "recipes to avoid" (disliked within the last 4 weeks,
  or used in the immediately prior week) -- call the search_recipes tool with these excluded.
- Schedule exactly one recipe per cooking day given -- not more, not fewer.
- Do not include a cheat meal unless the user explicitly requested one; if requested, include
  exactly that many cheat-meal slots (a cheat meal can be any recipe -- mark it "is_cheat_meal": true).
- Try to keep each day's calories close to the daily calorie target, and the whole week's
  average close to it too. It's fine to be off by a modest amount if the cuisine/day constraints
  don't allow an exact match -- do not fabricate a recipe or its calorie count to force a fit.
- Nights flagged as "eating out" get no recipe -- they still appear in the output with
  "is_eating_out": true and "recipe_name": null.

You must call the search_recipes tool to find candidates -- never invent a recipe that isn't
returned by the tool.

When you have a final plan, respond with ONLY a JSON object (no prose, no markdown fences) of
this exact shape:
{
  "days": [
    {"day": "Sunday", "recipe_name": "...", "cuisine": "...", "calories": 000,
     "is_cheat_meal": false, "is_eating_out": false},
    ...
  ],
  "week_avg_daily_calories": 000,
  "notes": "one sentence on any tradeoff you made, or empty string"
}
"""


@beta_tool
def search_recipes(cuisines: list, exclude_names: list) -> str:
    """Search the recipe catalog for candidates.

    Args:
        cuisines: cuisine names to filter by (case-insensitive). Empty list means any cuisine.
        exclude_names: recipe names that must NOT be returned (disliked or used last week).
    """
    cuisines_lower = {c.lower() for c in cuisines}
    exclude_lower = {n.lower() for n in exclude_names}
    results = [
        r
        for r in MOCK_RECIPES
        if (not cuisines_lower or r["cuisine"].lower() in cuisines_lower)
        and r["name"].lower() not in exclude_lower
    ]
    return json.dumps(results)


def _client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Export it in your shell before running the app."
        )
    return anthropic.Anthropic(api_key=api_key)


def _extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def _run(user_message: str):
    client = _client()
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        system=SYSTEM_PROMPT,
        tools=[search_recipes],
        messages=[{"role": "user", "content": user_message}],
    )
    final_text = None
    for message in runner:
        for block in message.content:
            if block.type == "text":
                final_text = block.text
    if final_text is None:
        raise RuntimeError("Recipe agent produced no text output.")
    return _extract_json(final_text)


def propose_week(
    cuisines,
    cooking_days,
    daily_calorie_target,
    cheat_meals_requested,
    eating_out_nights,
    disliked_meals,
    last_week_recipes,
):
    """Propose a first-draft weekly plan. Returns the parsed JSON plan dict."""
    exclude = list(set(disliked_meals) | set(last_week_recipes))
    user_message = f"""Plan this week's meals.

Cuisines selected: {cuisines}
Cooking days (one recipe each): {cooking_days}
Nights already known to be eating out (no recipe needed): {eating_out_nights}
Daily calorie target: {daily_calorie_target}
Cheat meals requested this week: {cheat_meals_requested}
Recipes to avoid (disliked in last 4 weeks or used last week): {exclude}

All available cuisines in the catalog, for reference: {all_cuisines()}

Call search_recipes with cuisines={cuisines} and exclude_names={exclude} to find candidates,
then build the week's plan. Include every day from the cooking days AND the eating-out nights
in your "days" output (eating-out nights get is_eating_out=true, recipe_name=null, calories=0).
"""
    return _run(user_message)


def revise_week(current_plan, disliked_meal_names, new_eating_out_nights, cuisines, disliked_meals, last_week_recipes):
    """Revise a plan based on David's feedback. Must change at least the flagged items."""
    exclude = list(set(disliked_meals) | set(last_week_recipes) | set(disliked_meal_names))
    user_message = f"""Here is the current proposed week's plan (JSON):
{json.dumps(current_plan)}

David's feedback:
- Meals he now dislikes and wants replaced: {disliked_meal_names}
- Additional nights he's now eating out (no recipe needed, replace any existing recipe on
  these days with is_eating_out=true, recipe_name=null): {new_eating_out_nights}

Revise the plan. You MUST change every flagged day -- do not return the same recipe for a day
David flagged as disliked. Keep all non-flagged days the same as the current plan unless a
change is required to avoid a repeat.

Call search_recipes with cuisines={cuisines} and exclude_names={exclude} to find replacement
candidates for the flagged days.

Respond with the full revised plan in the same JSON shape as before (all days, not just the
changed ones).
"""
    return _run(user_message)
