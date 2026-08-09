"""Live Spoonacular integration -- the real swap-in for MOCK_RECIPES documented in
data/mock_recipes.py's module docstring. Only called when SPOONACULAR_API_KEY is set;
data/recipe_catalog.py decides mock vs real and is what the rest of the app imports.
"""

import os

import requests

BASE_URL = "https://api.spoonacular.com/recipes/complexSearch"
TIMEOUT_SECONDS = 15
RESULTS_PER_SEARCH = 8

# Spoonacular's dish-type filter has no separate "lunch"/"dinner" value -- both draw
# from "main course". Our own meal_type is stamped onto the result regardless, since
# that's the only thing the rest of the app relies on to fill a slot correctly.
_MEAL_TYPE_TO_DISH_TYPE = {"breakfast": "breakfast", "lunch": "main course", "dinner": "main course"}


class SpoonacularError(Exception):
    """Raised when Spoonacular can't be reached or returns an error. The caller
    (ultimately the UI) should surface this with an option to retry manually,
    per the Design failure-handling plan -- not silently retry or fall back."""


def search_recipes(cuisines, meal_type, exclude_names):
    api_key = os.environ.get("SPOONACULAR_API_KEY")
    if not api_key:
        raise SpoonacularError("SPOONACULAR_API_KEY is not set.")

    params = {
        "apiKey": api_key,
        "type": _MEAL_TYPE_TO_DISH_TYPE[meal_type],
        "number": RESULTS_PER_SEARCH,
        "addRecipeNutrition": "true",
        "fillIngredients": "true",
        "instructionsRequired": "false",
    }
    if cuisines:
        params["cuisine"] = ",".join(cuisines)

    try:
        response = requests.get(BASE_URL, params=params, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as e:
        raise SpoonacularError(f"Couldn't reach Spoonacular: {e}") from e

    if response.status_code != 200:
        raise SpoonacularError(
            f"Spoonacular returned HTTP {response.status_code}: {response.text[:200]}"
        )

    try:
        payload = response.json()
    except ValueError as e:
        raise SpoonacularError(f"Spoonacular returned an unreadable response: {e}") from e

    cuisines_lower = {c.lower() for c in cuisines}
    exclude_lower = {n.lower() for n in exclude_names}
    recipes = []
    for item in payload.get("results", []):
        recipe = _to_recipe(item, meal_type, cuisines_lower)
        if recipe is None:
            continue
        if recipe["name"].lower() in exclude_lower:
            continue
        recipes.append(recipe)
    return recipes


def _to_recipe(item, meal_type, cuisines_lower):
    calories = _find_calories(item.get("nutrition", {}).get("nutrients", []))
    ingredients = _to_ingredients(item.get("extendedIngredients", []))
    if calories is None or not ingredients or not item.get("title"):
        # Missing data for this dish (happens on some Spoonacular entries) --
        # skip it rather than show an incomplete recipe.
        return None

    cuisine_tags = item.get("cuisines") or []
    cuisine = next((c for c in cuisine_tags if c.lower() in cuisines_lower), None)
    cuisine = cuisine or (cuisine_tags[0] if cuisine_tags else "International")

    return {
        "name": item["title"],
        "cuisine": cuisine,
        "meal_type": meal_type,
        "calories": round(calories),
        "ingredients": ingredients,
    }


def _find_calories(nutrients):
    for n in nutrients:
        if n.get("name") == "Calories":
            return n.get("amount")
    return None


def _to_ingredients(extended_ingredients):
    ingredients = []
    for ing in extended_ingredients:
        us = (ing.get("measures") or {}).get("us") or {}
        quantity = us.get("amount", ing.get("amount"))
        unit = us.get("unitShort") or ing.get("unit") or "each"
        name = ing.get("name") or ing.get("nameClean")
        if not name or quantity is None:
            continue
        ingredients.append({"name": name, "quantity": round(quantity, 2), "unit": unit})
    return ingredients
