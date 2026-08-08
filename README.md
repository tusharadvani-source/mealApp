# Weekly Meal Planner (prototype)

A weekly meal-planning and grocery-cart-building agent for David — see the Discovery/Design/Develop
sections of the Agentic AI PRD for full context. This is the Develop-phase prototype.

## What it does

David triggers a weekly cycle, picks cuisines and cooking days, and the recipe agent proposes a
week of meals. He can flag dislikes or additional eating-out nights and the plan gets revised.
Once approved, the cart agent consolidates ingredients across the week into a single priced
shopping list. **The agent never checks out or spends money — David buys the groceries himself.**

## Architecture

- `app.py` — orchestrator (Streamlit). Routes David's inputs to the agents below; holds no
  meal-selection or pricing logic itself.
- `agents/recipe_agent.py` — calls Claude (via the Tool Runner) to propose/revise the week's
  meals, using a `search_recipes` tool backed by the mock catalog in `data/mock_recipes.py`.
- `agents/mock_recipe_agent.py` — free, no-API-key fallback with the same interface, for testing
  without spending anything. Auto-selected when `ANTHROPIC_API_KEY` isn't set.
- `agents/cart_agent.py` — deterministic ingredient consolidation + mock pricing (not an LLM
  call, by design — see the module docstring for why).
- `storage/profile_store.py` — JSON-file memory: profile persists indefinitely, disliked meals
  for a rolling 4 weeks, last week's recipes for a rolling 1 week (repeat-avoidance only).
- `data/mock_recipes.py`, `data/mock_prices.py` — stand-ins for the real Spoonacular API and a
  live web-search pricing lookup (both are the Discovery/Design "synthetic data plan").

## Running it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional — omit this to run in free mock mode (no Claude calls):
export ANTHROPIC_API_KEY=sk-ant-...

streamlit run app.py
```

## Known limitations (v1 prototype)

- Recipe catalog and grocery prices are mock data, not the real Spoonacular API or a live
  web-search pricing lookup yet.
- Single local user (David) — profile is a flat JSON file, not multi-user.
- No real checkout/store integration by design (see Discovery's human-boundary decision).
