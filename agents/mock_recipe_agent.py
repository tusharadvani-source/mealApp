"""Free, no-API-key fallback for the recipe agent.

Same propose_week / revise_week contract as agents/recipe_agent.py (same inputs,
same JSON-shaped output), but picks recipes with plain rule-based filtering instead
of calling Claude. Lets the app be clicked through end to end at zero cost.

As discussed: at the current ~24-recipe mock-catalog scale, this rule-based picker
produces results about as good as the LLM version. The real justification for the
Claude-backed recipe_agent.py is real-scale data (Spoonacular's ~365k recipes) and
the judgment calls in the revision loop -- see recipe_agent.py's module docstring.
This module exists purely so David (or Tushar, testing) can try the full workflow
before spending anything on API calls.
"""

from data.mock_recipes import MOCK_RECIPES


def _candidates(cuisines, exclude_names):
    cuisines_lower = {c.lower() for c in cuisines}
    exclude_lower = {n.lower() for n in exclude_names}
    return [
        r
        for r in MOCK_RECIPES
        if (not cuisines_lower or r["cuisine"].lower() in cuisines_lower)
        and r["name"].lower() not in exclude_lower
    ]


def _pick_for_day(pool, used_this_week, daily_calorie_target):
    """Closest-to-target recipe not already used this week. Falls back to any unused recipe."""
    available = [r for r in pool if r["name"] not in used_this_week]
    if not available:
        available = pool  # ran out of unique options; allow a repeat rather than fail
    return min(available, key=lambda r: abs(r["calories"] - daily_calorie_target))


def propose_week(
    cuisines,
    cooking_days,
    daily_calorie_target,
    cheat_meals_requested,
    eating_out_nights,
    disliked_meals,
    last_week_recipes,
):
    exclude = list(set(disliked_meals) | set(last_week_recipes))
    pool = _candidates(cuisines, exclude)

    days = []
    used_this_week = set()
    for day in eating_out_nights:
        days.append(
            {"day": day, "recipe_name": None, "cuisine": None, "calories": 0,
             "is_cheat_meal": False, "is_eating_out": True}
        )

    cooking_calories = []
    for day in cooking_days:
        if not pool:
            recipe = None
        else:
            recipe = _pick_for_day(pool, used_this_week, daily_calorie_target)
            used_this_week.add(recipe["name"])
        if recipe is None:
            days.append(
                {"day": day, "recipe_name": None, "cuisine": None, "calories": 0,
                 "is_cheat_meal": False, "is_eating_out": False}
            )
            continue
        cooking_calories.append(recipe["calories"])
        days.append(
            {
                "day": day,
                "recipe_name": recipe["name"],
                "cuisine": recipe["cuisine"],
                "calories": recipe["calories"],
                "is_cheat_meal": False,
                "is_eating_out": False,
            }
        )

    # Mark the N highest-calorie cooked days as the requested cheat meals.
    cooked_rows = [d for d in days if not d["is_eating_out"] and d["recipe_name"]]
    cooked_rows.sort(key=lambda d: d["calories"], reverse=True)
    for row in cooked_rows[: max(0, cheat_meals_requested)]:
        row["is_cheat_meal"] = True

    week_avg = round(sum(cooking_calories) / len(cooking_calories)) if cooking_calories else 0
    return {
        "days": days,
        "week_avg_daily_calories": week_avg,
        "notes": "Mock mode: recipes picked by simple cuisine/calorie filtering, not Claude.",
    }


def revise_week(current_plan, disliked_meal_names, new_eating_out_nights, cuisines, disliked_meals, last_week_recipes):
    exclude = list(set(disliked_meals) | set(last_week_recipes) | set(disliked_meal_names))
    pool = _candidates(cuisines, exclude)

    used_this_week = {
        d["recipe_name"] for d in current_plan["days"] if d.get("recipe_name") and d["recipe_name"] not in disliked_meal_names
    }

    new_days = []
    cooking_calories = []
    for row in current_plan["days"]:
        if row["day"] in new_eating_out_nights:
            new_days.append(
                {"day": row["day"], "recipe_name": None, "cuisine": None, "calories": 0,
                 "is_cheat_meal": False, "is_eating_out": True}
            )
            continue
        if row.get("recipe_name") in disliked_meal_names:
            target = row["calories"] or 600
            if not pool:
                new_days.append(
                    {"day": row["day"], "recipe_name": None, "cuisine": None, "calories": 0,
                     "is_cheat_meal": False, "is_eating_out": False}
                )
                continue
            replacement = _pick_for_day(pool, used_this_week, target)
            used_this_week.add(replacement["name"])
            new_days.append(
                {
                    "day": row["day"],
                    "recipe_name": replacement["name"],
                    "cuisine": replacement["cuisine"],
                    "calories": replacement["calories"],
                    "is_cheat_meal": row.get("is_cheat_meal", False),
                    "is_eating_out": False,
                }
            )
            if not row["is_eating_out"]:
                cooking_calories.append(replacement["calories"])
            continue
        new_days.append(row)
        if not row["is_eating_out"] and row.get("recipe_name"):
            cooking_calories.append(row["calories"])

    week_avg = round(sum(cooking_calories) / len(cooking_calories)) if cooking_calories else 0
    return {
        "days": new_days,
        "week_avg_daily_calories": week_avg,
        "notes": "Mock mode: recipes picked by simple cuisine/calorie filtering, not Claude.",
    }
