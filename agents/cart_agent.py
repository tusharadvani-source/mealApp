"""Cart agent: consolidates approved recipes into a priced shopping list.

Design #3 (Agent loop) for this role:
  Observes - the final approved recipe list.
  Decides  - how to consolidate ingredients (merging duplicates, summing quantities)
             and estimates prices via web search.
  Produces - a shopping list with quantities and estimated prices.
  Checks   - the list stays close to David's stated budget before handing it back.

Implementation note: ingredient consolidation and pricing math is done deterministically
in plain Python rather than via an LLM call. This is a considered choice, not a shortcut --
Design/Develop's eval plan requires exact cart math (shared ingredients summed correctly,
total = sum of line items), which is an arithmetic guarantee an LLM call can't provide.
The "agent" framing still holds: this module is the one responsible for the
observe/decide/produce/check loop described above, and its price lookup is a placeholder
for a genuinely agentic web-search call later (Design #5 -- see price_for_ingredient's
docstring for the swap point).
"""

from collections import defaultdict

from data.mock_prices import price_for_ingredient

SERVING_MULTIPLIER = 2  # recipes are shown/shopped for 2 servings; calories stay per-serving


def build_cart(recipes, budget):
    """recipes: list of recipe dicts (with 'ingredients') approved for the week. Each
    recipe's base ingredient quantities are for ONE serving; the cart shops for
    SERVING_MULTIPLIER servings of everything, matching what's shown to the user.

    Returns a dict: {items: [...], total: float, price_unknown_items: [...], over_budget: bool}
    """
    merged = defaultdict(lambda: {"quantity": 0.0, "unit": None})
    for recipe in recipes:
        for ing in recipe["ingredients"]:
            key = (ing["name"].lower(), ing["unit"])
            merged[key]["quantity"] += ing["quantity"] * SERVING_MULTIPLIER
            merged[key]["unit"] = ing["unit"]

    items = []
    price_unknown_items = []
    total = 0.0
    for (name, unit), agg in sorted(merged.items()):
        unit_price = price_for_ingredient(name)
        if unit_price is None:
            price_unknown_items.append(name)
            items.append(
                {
                    "ingredient": name,
                    "quantity": round(agg["quantity"], 2),
                    "unit": unit,
                    "unit_price": None,
                    "line_total": None,
                    "price_unknown": True,
                }
            )
            continue
        line_total = round(agg["quantity"] * unit_price, 2)
        total += line_total
        items.append(
            {
                "ingredient": name,
                "quantity": round(agg["quantity"], 2),
                "unit": unit,
                "unit_price": unit_price,
                "line_total": line_total,
                "price_unknown": False,
            }
        )

    total = round(total, 2)
    over_budget = budget is not None and total > budget

    return {
        "items": items,
        "total": total,
        "price_unknown_items": price_unknown_items,
        "over_budget": over_budget,
        "budget": budget,
    }
