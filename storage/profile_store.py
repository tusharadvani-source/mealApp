"""Simple JSON-file persistence for David's profile and agent memory.

Implements the Design #6 memory decision:
- Profile (height, weight history, goal, budget, cooking pattern) persists indefinitely.
- Disliked meals persist for a rolling 4-week window (not permanent).
- Last week's recipes persist for a rolling 1-week window (repeat-avoidance lookback only).
- Cuisine picks, calorie overrides, and cheat/outside-meal flags are NOT persisted here
  (they're one-off weekly inputs, held only in session state for that cycle).
"""

import json
import os

STORE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profile_data.json")

DISLIKED_MEAL_WINDOW_WEEKS = 4
LAST_RECIPES_WINDOW_WEEKS = 1


def _default_state():
    return {
        "profile": {
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


def load():
    if not os.path.exists(STORE_PATH):
        return _default_state()
    with open(STORE_PATH, "r") as f:
        data = json.load(f)
    # backfill any fields missing from an older save file
    defaults = _default_state()
    for key, value in defaults.items():
        data.setdefault(key, value)
    return data


def save(state):
    with open(STORE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def has_profile(state):
    p = state["profile"]
    return p["height_in"] is not None and p["goal"] is not None


def set_profile(state, height_in, goal, budget, default_cooking_days_per_week):
    state["profile"] = {
        "height_in": height_in,
        "goal": goal,
        "budget": budget,
        "default_cooking_days_per_week": default_cooking_days_per_week,
    }
    save(state)


def start_new_week(state):
    """Advance the week counter. Call once per weekly planning cycle."""
    state["current_week"] += 1
    save(state)
    return state["current_week"]


def record_weight(state, week, weight_lb):
    state["weight_history"].append({"week": week, "weight_lb": weight_lb})
    save(state)


def latest_weight(state):
    if not state["weight_history"]:
        return None
    return state["weight_history"][-1]["weight_lb"]


def add_disliked_meal(state, name, week):
    existing = {d["name"] for d in state["disliked_meals"]}
    if name not in existing:
        state["disliked_meals"].append({"name": name, "week_disliked": week})
        save(state)


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
    save(state)


def last_week_recipes(state, current_week):
    """Recipes used in the immediately prior week only (1-week lookback, not longer)."""
    for w in state["weekly_recipe_history"]:
        if w["week"] == current_week - 1:
            return w["recipe_names"]
    return []
