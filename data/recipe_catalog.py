"""Recipe catalog: dispatches to the live Spoonacular API when SPOONACULAR_API_KEY is
set, otherwise the local mock catalog -- the real swap point documented in
mock_recipes.py's module docstring.

Both agents/recipe_agent.py's search_recipes tool and agents/mock_recipe_agent.py's
local filtering call search_recipes() here, so the swap applies whether the
Claude-powered or free rule-based planner is driving the week.
"""

import os

from data.mock_recipes import MOCK_RECIPES

CURATED_CUISINES = [
    "American", "Chinese", "Indian", "Italian",
    "Japanese", "Mediterranean", "Mexican", "Thai",
]

USE_REAL_RECIPES = bool(os.environ.get("SPOONACULAR_API_KEY"))

# Recipes returned by search_recipes are cached here (by lowercase name) so app.py can
# look up full ingredient details later for display/cart-building -- unlike MOCK_RECIPES,
# live Spoonacular results aren't a static catalog to search after the fact.
_recipe_cache = {r["name"].lower(): r for r in MOCK_RECIPES}


def all_cuisines():
    return CURATED_CUISINES


def search_recipes(cuisines, meal_type, exclude_names):
    if USE_REAL_RECIPES:
        from data import spoonacular_api
        results = spoonacular_api.search_recipes(cuisines, meal_type, exclude_names)
    else:
        results = _search_mock(cuisines, meal_type, exclude_names)
    for r in results:
        _recipe_cache[r["name"].lower()] = r
    return results


def _search_mock(cuisines, meal_type, exclude_names):
    cuisines_lower = {c.lower() for c in cuisines}
    exclude_lower = {n.lower() for n in exclude_names}
    return [
        r
        for r in MOCK_RECIPES
        if r["meal_type"] == meal_type
        and (not cuisines_lower or r["cuisine"].lower() in cuisines_lower)
        and r["name"].lower() not in exclude_lower
    ]


def recipe_by_name(name):
    if not name:
        return None
    return _recipe_cache.get(name.lower())
