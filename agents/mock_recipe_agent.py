"""Free, no-API-key fallback for the recipe agent.

Same propose_week / revise_week contract as agents/recipe_agent.py (same
inputs, same JSON-shaped output), but picks recipes with plain rule-based
filtering instead of calling Claude. Lets the app be clicked through end to
end at zero cost.

Plans at the meal level -- breakfast, lunch, and dinner are each their own
slot with their own recipe, not one recipe per day.
"""

from data.mock_recipes import MOCK_RECIPES
from nutrition import target_for_meal as _target_for_meal


def _candidates(cuisines, meal_type, exclude_names):
    cuisines_lower = {c.lower() for c in cuisines}
    exclude_lower = {n.lower() for n in exclude_names}
    return [
        r
        for r in MOCK_RECIPES
        if r["meal_type"] == meal_type
        and (not cuisines_lower or r["cuisine"].lower() in cuisines_lower)
        and r["name"].lower() not in exclude_lower
    ]


def _pick(pool, used_this_week, target_calories, prefer_high_calorie=False):
    """Closest-to-target recipe not already used this week (or highest-calorie, for a
    cheat-meal slot). Falls back to any unused recipe, then to a repeat if the pool
    itself is exhausted -- matches the "allow a repeat rather than fail" behavior in
    the original day-level version."""
    available = [r for r in pool if r["name"] not in used_this_week]
    if not available:
        available = pool
    if not available:
        return None
    if prefer_high_calorie:
        return max(available, key=lambda r: r["calories"])
    return min(available, key=lambda r: abs(r["calories"] - target_calories))


def _day_avgs(meals):
    day_totals = {}
    for m in meals:
        if not m["is_eating_out"] and m.get("recipe_name"):
            day_totals.setdefault(m["day"], []).append(m["calories"])
    return [sum(cals) for cals in day_totals.values()]


def propose_week(
    cuisines,
    meal_slots,
    eating_out_slots,
    daily_calorie_target,
    cheat_meal_slot,
    disliked_meals,
    last_week_recipes,
):
    exclude = list(set(disliked_meals) | set(last_week_recipes))
    used_this_week = set()

    meals = []
    for slot in eating_out_slots:
        meals.append(
            {
                "day": slot["day"], "meal_type": slot["meal_type"], "recipe_name": None,
                "cuisine": None, "calories": 0, "is_cheat_meal": False, "is_eating_out": True,
            }
        )

    for slot in meal_slots:
        day, meal_type = slot["day"], slot["meal_type"]
        is_cheat = (
            cheat_meal_slot is not None
            and cheat_meal_slot["day"] == day
            and cheat_meal_slot["meal_type"] == meal_type
        )
        pool = _candidates(cuisines, meal_type, exclude)
        target = _target_for_meal(daily_calorie_target, meal_type)
        recipe = _pick(pool, used_this_week, target, prefer_high_calorie=is_cheat)
        if recipe is None:
            meals.append(
                {
                    "day": day, "meal_type": meal_type, "recipe_name": None, "cuisine": None,
                    "calories": 0, "is_cheat_meal": False, "is_eating_out": False,
                }
            )
            continue
        used_this_week.add(recipe["name"])
        meals.append(
            {
                "day": day, "meal_type": meal_type, "recipe_name": recipe["name"],
                "cuisine": recipe["cuisine"], "calories": recipe["calories"],
                "is_cheat_meal": is_cheat, "is_eating_out": False,
            }
        )

    day_avgs = _day_avgs(meals)
    week_avg = round(sum(day_avgs) / len(day_avgs)) if day_avgs else 0
    return {
        "meals": meals,
        "week_avg_daily_calories": week_avg,
        "notes": "Mock mode: recipes picked by simple cuisine/calorie filtering, not Claude.",
    }


def revise_week(current_plan, disliked_meal_names, new_eating_out_slots, cuisines, disliked_meals, last_week_recipes):
    exclude = list(set(disliked_meals) | set(last_week_recipes) | set(disliked_meal_names))
    used_this_week = {
        m["recipe_name"]
        for m in current_plan["meals"]
        if m.get("recipe_name") and m["recipe_name"] not in disliked_meal_names
    }
    new_eating_out_keys = {(s["day"], s["meal_type"]) for s in new_eating_out_slots}

    new_meals = []
    for m in current_plan["meals"]:
        key = (m["day"], m["meal_type"])

        if key in new_eating_out_keys:
            new_meals.append(
                {
                    "day": m["day"], "meal_type": m["meal_type"], "recipe_name": None,
                    "cuisine": None, "calories": 0, "is_cheat_meal": False, "is_eating_out": True,
                }
            )
            continue

        if m.get("recipe_name") in disliked_meal_names:
            pool = _candidates(cuisines, m["meal_type"], exclude)
            target = m["calories"] or 500
            replacement = _pick(pool, used_this_week, target, prefer_high_calorie=m.get("is_cheat_meal", False))
            if replacement is None:
                new_meals.append(
                    {
                        "day": m["day"], "meal_type": m["meal_type"], "recipe_name": None,
                        "cuisine": None, "calories": 0, "is_cheat_meal": False, "is_eating_out": False,
                    }
                )
                continue
            used_this_week.add(replacement["name"])
            new_meals.append(
                {
                    "day": m["day"], "meal_type": m["meal_type"], "recipe_name": replacement["name"],
                    "cuisine": replacement["cuisine"], "calories": replacement["calories"],
                    "is_cheat_meal": m.get("is_cheat_meal", False), "is_eating_out": False,
                }
            )
            continue

        new_meals.append(m)

    day_avgs = _day_avgs(new_meals)
    week_avg = round(sum(day_avgs) / len(day_avgs)) if day_avgs else 0
    return {
        "meals": new_meals,
        "week_avg_daily_calories": week_avg,
        "notes": "Mock mode: recipes picked by simple cuisine/calorie filtering, not Claude.",
    }
