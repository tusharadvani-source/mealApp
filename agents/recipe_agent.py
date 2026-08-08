"""Recipe agent: proposes and revises a week of meals, at the meal level
(breakfast, lunch, dinner are each their own slot with their own recipe).

Design #3 (Agent loop) for this role:
  Observes  - David's cuisine picks, calorie target (or weight/goal to derive one),
              which day+meal slots need a recipe vs. are eating out, and any
              disliked-meal/eating-out feedback.
  Decides   - which recipes to select per slot and how to schedule them.
  Produces  - a proposed week of meals with per-day calorie totals.
  Checks    - no dish repeats within the week (or the 1-week/4-week memory windows),
              each meal roughly fits its share of the calorie target, at most one
              cheat meal and only in the slot the user asked for.

v1 uses MOCK_RECIPES via a search_recipes tool in place of the Spoonacular API
(Discovery: "Synthetic data plan"). Swapping in the real API later means replacing
only the search_recipes tool body -- this function's contract stays the same.
"""

import json
import os

import anthropic
from anthropic import beta_tool

from data.mock_recipes import MOCK_RECIPES, all_cuisines
from nutrition import MEAL_CALORIE_SPLIT

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """You are the recipe-planning agent for a weekly meal-planning assistant.

You plan at the MEAL level, not the day level: breakfast, lunch, and dinner are each
their own slot with their own recipe.

Rules you must always follow:
- Only propose recipes matching the user's selected cuisines.
- A recipe's meal_type must match the slot you're filling (breakfast recipes for
  breakfast slots, etc.) -- always call search_recipes with the slot's meal_type.
- Never repeat a dish anywhere within the same week's plan, across any meal type.
- Never propose a recipe listed under "recipes to avoid" (disliked within the last 4
  weeks, or used in the immediately prior week) -- call search_recipes with these excluded.
- Every recipe in the catalog already includes a carb component (rice, bread, pasta,
  tortilla, etc.), so a returned recipe is always a complete meal -- you don't need to
  add anything to it.
- Fill every slot listed as needing a recipe, exactly once each.
- At most ONE cheat meal is allowed, and only in the specific slot the user names (if
  any) -- mark only that slot "is_cheat_meal": true, and pick something more indulgent
  there. Never add a cheat meal to a slot the user didn't specify.
- Try to keep each meal's calories close to its share of the daily calorie target
  (roughly 25% breakfast / 35% lunch / 40% dinner), and the whole week's daily average
  close to the target. It's fine to be off by a modest amount if the constraints don't
  allow an exact match -- do not fabricate a recipe or its calorie count to force a fit.
- Slots marked as eating out get no recipe -- they still appear in the output with
  "is_eating_out": true and "recipe_name": null.

You must call the search_recipes tool to find candidates -- never invent a recipe that
isn't returned by the tool.

When you have a final plan, respond with ONLY a JSON object (no prose, no markdown fences) of
this exact shape:
{
  "meals": [
    {"day": "Sunday", "meal_type": "breakfast", "recipe_name": "...", "cuisine": "...",
     "calories": 000, "is_cheat_meal": false, "is_eating_out": false},
    ...
  ],
  "week_avg_daily_calories": 000,
  "notes": "one sentence on any tradeoff you made, or empty string"
}
"""


@beta_tool
def search_recipes(cuisines: list, meal_type: str, exclude_names: list) -> str:
    """Search the recipe catalog for candidates.

    Args:
        cuisines: cuisine names to filter by (case-insensitive). Empty list means any cuisine.
        meal_type: "breakfast", "lunch", or "dinner" -- must match the slot being filled.
        exclude_names: recipe names that must NOT be returned (disliked or used last week).
    """
    cuisines_lower = {c.lower() for c in cuisines}
    exclude_lower = {n.lower() for n in exclude_names}
    results = [
        r
        for r in MOCK_RECIPES
        if r["meal_type"] == meal_type
        and (not cuisines_lower or r["cuisine"].lower() in cuisines_lower)
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
    meal_slots,
    eating_out_slots,
    daily_calorie_target,
    cheat_meal_slot,
    disliked_meals,
    last_week_recipes,
):
    """Propose a first-draft weekly plan. Returns the parsed JSON plan dict.

    meal_slots: list of {"day": ..., "meal_type": ...} needing a recipe.
    eating_out_slots: list of {"day": ..., "meal_type": ...} with no recipe needed.
    cheat_meal_slot: {"day": ..., "meal_type": ...} or None -- at most one cheat meal.
    """
    exclude = list(set(disliked_meals) | set(last_week_recipes))
    user_message = f"""Plan this week's meals.

Cuisines selected: {cuisines}
Meal slots needing a recipe (day + meal_type, one recipe each): {meal_slots}
Slots the user is eating out (no recipe needed): {eating_out_slots}
Daily calorie target: {daily_calorie_target} (split roughly {MEAL_CALORIE_SPLIT} across breakfast/lunch/dinner)
Cheat meal slot (at most one, mark ONLY this slot is_cheat_meal=true; if None, no cheat meal this week): {cheat_meal_slot}
Recipes to avoid (disliked in last 4 weeks or used last week): {exclude}

All available cuisines in the catalog, for reference: {all_cuisines()}

For each slot in meal_slots, call search_recipes with cuisines={cuisines}, the slot's
meal_type, and exclude_names={exclude} to find candidates, then build the week's plan.
Include every slot from meal_slots AND every slot from eating_out_slots in your "meals"
output.
"""
    return _run(user_message)


def revise_week(current_plan, disliked_meal_names, new_eating_out_slots, cuisines, disliked_meals, last_week_recipes):
    """Revise a plan based on the user's feedback. Must change at least the flagged slots.

    new_eating_out_slots: list of {"day": ..., "meal_type": ...} to convert to eating-out.
    """
    exclude = list(set(disliked_meals) | set(last_week_recipes) | set(disliked_meal_names))
    user_message = f"""Here is the current proposed week's plan (JSON):
{json.dumps(current_plan)}

User's feedback:
- Meals he now dislikes and wants replaced: {disliked_meal_names}
- Slots that are now eating out (no recipe needed, replace any existing recipe on these
  slots with is_eating_out=true, recipe_name=null): {new_eating_out_slots}

Revise the plan. You MUST change every flagged slot -- do not return the same recipe for
a slot flagged as disliked. Keep all non-flagged slots the same as the current plan
unless a change is required to avoid a repeat. Preserve any existing is_cheat_meal flag
on a slot unless that slot itself was flagged.

Call search_recipes (matching each flagged slot's meal_type) with cuisines={cuisines} and
exclude_names={exclude} to find replacement candidates for the flagged slots.

Respond with the full revised plan in the same JSON shape as before (all slots, not just
the changed ones).
"""
    return _run(user_message)
