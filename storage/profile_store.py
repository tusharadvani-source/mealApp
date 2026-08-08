"""Pure in-memory logic for a single user's profile and agent memory.

No file I/O lives here -- storage/user_store.py owns persistence across
potentially many user accounts. This module only shapes and mutates the
per-user "state" dict.

Implements the Design #6 memory decision:
- Profile (name, height, weight history, goal, budget, cooking pattern) persists indefinitely.
- Disliked meals persist for a rolling 4-week window (not permanent).
- Last week's recipes persist for a rolling 1-week window (repeat-avoidance lookback only).
- Cuisine picks, calorie overrides, and cheat/outside-meal flags are NOT persisted here
  (they're one-off weekly inputs, held only in session state for that cycle).
"""

DISLIKED_MEAL_WINDOW_WEEKS = 4
LAST_RECIPES_WINDOW_WEEKS = 1


def default_state():
    return {
        "profile": {
            "name": None,
            "height_in": None,
            "goal": None,  # "weight_loss" or "bulking"
            "budget": None,
            "default_cooking_days_per_week": None,
        },
        "weight_history": [],  # [{"week": int, "weight_lb": float}]
        "disliked_meals": [],  # [{"name": str, "week_disliked": int}]
        "weekly_recipe_history": [],  # [{"week": int, "recipe_names": [str, ...]}]
        "current_week": 0,
    }


def has_profile(state):
    p = state["profile"]
    return p["height_in"] is not None and p["goal"] is not None


def set_profile(state, height_in, goal, budget, default_cooking_days_per_week):
    state["profile"]["height_in"] = height_in
    state["profile"]["goal"] = goal
    state["profile"]["budget"] = budget
    state["profile"]["default_cooking_days_per_week"] = default_cooking_days_per_week


def start_new_week(state):
    """Advance the week counter. Call once per weekly planning cycle."""
    state["current_week"] += 1
    return state["current_week"]


def record_weight(state, week, weight_lb):
    state["weight_history"].append({"week": week, "weight_lb": weight_lb})


def latest_weight(state):
    if not state["weight_history"]:
        return None
    return state["weight_history"][-1]["weight_lb"]


def add_disliked_meal(state, name, week):
    existing = {d["name"] for d in state["disliked_meals"]}
    if name not in existing:
        state["disliked_meals"].append({"name": name, "week_disliked": week})


def active_disliked_meals(state, current_week):
    """Meals disliked within the last DISLIKED_MEAL_WINDOW_WEEKS weeks (rolling, not permanent)."""
    cutoff = current_week - DISLIKED_MEAL_WINDOW_WEEKS
    active = [d["name"] for d in state["disliked_meals"] if d["week_disliked"] > cutoff]
    return active


def record_week_recipes(state, week, recipe_names):
    state["weekly_recipe_history"] = [
        w for w in state["weekly_recipe_history"] if w["week"] != week
    ]
    state["weekly_recipe_history"].append({"week": week, "recipe_names": recipe_names})


def last_week_recipes(state, current_week):
    """Recipes used in the immediately prior week only (1-week lookback, not longer)."""
    for w in state["weekly_recipe_history"]:
        if w["week"] == current_week - 1:
            return w["recipe_names"]
    return []
