# Weekly Meal Planner (prototype)

A weekly meal-planning and grocery-cart-building agent, originally scoped around one persona
(David) in the Discovery/Design sections of the Agentic AI PRD, now generalized to any signed-up
user. This is the Develop-phase prototype.

## What it does

Any user can sign up (name, username, password) or log back in. Each account triggers its own
weekly cycle, planned at the **meal level** — breakfast, lunch, and dinner are each their own
slot with their own recipe, every recipe includes a carb side so it's a complete meal, and
recipes are shown/shopped for a user-chosen number of servings (2-4) with an explicit
per-serving calorie label. The app shows an estimated maintenance-calorie number (from
height/weight) and a capped 400-calorie deficit or surplus target based on the user's goal.

**Cooking days and leftovers:** breakfast is always cooked fresh, every day. For lunch and
dinner, the user picks which days they'll actually cook and how many servings per dish (2-4,
highlighted right under the cooking-days picker) — each cook day's dish yields one serving eaten
fresh, with the rest available as leftovers on paired non-cooking days
(`build_leftover_pairing` / `synthesize_leftovers` in `app.py`). The app strictly respects the
chosen cooking days: it never schedules a cook occasion on a day the user didn't pick. If the
selected cooking days and servings can't cover the whole week, submission is blocked with an
error listing the uncovered slots, asking the user to add a cooking day, raise servings, or mark
those meals as eating out. The recipe agent never sees or reasons about leftover days — it only
ever proposes genuine cook occasions; leftovers are synthesized locally and kept in sync across
revisions, and the cart only shops for real cook occasions (a leftover day's groceries were
already covered by its source day's multi-serving shop).

Users also flag per-meal eating-out slots and at most one cheat meal; the recipe agent proposes
and revises around all of that. Once approved, the cart agent consolidates ingredients across
the week into a single priced shopping list.
**The agent never checks out or spends money — the user buys the groceries themself.**

## Architecture

- `app.py` — orchestrator (Streamlit). Gates on login, then routes the signed-in user's inputs
  to the agents below; holds no meal-selection or pricing logic itself.
- `nutrition.py` — maintenance-calorie estimate (height/weight only — no age/sex collected, so
  it's a rough approximation, not clinical) and the capped 400-cal deficit/surplus target logic.
- `storage/user_store.py` — multi-user accounts: signup/login, salted PBKDF2-SHA256 password
  hashing (passwords are never stored in plain text), and per-account state persistence.
- `storage/profile_store.py` — pure in-memory logic for one user's profile + agent memory
  (no file I/O — `user_store.py` owns persistence). Profile persists indefinitely, disliked
  meals for a rolling 4 weeks, last week's recipes for a rolling 1 week (repeat-avoidance only).
- `agents/recipe_agent.py` — calls Claude (via the Tool Runner) to propose/revise the week's
  meals slot by slot (breakfast/lunch/dinner), using a `search_recipes` tool backed by the mock
  catalog in `data/mock_recipes.py`.
- `agents/mock_recipe_agent.py` — free, no-API-key fallback with the same interface, for testing
  without spending anything. Auto-selected when `ANTHROPIC_API_KEY` isn't set.
- `agents/cart_agent.py` — deterministic ingredient consolidation + mock pricing (not an LLM
  call, by design — see the module docstring for why). Scales quantities by the user's chosen
  `servings` (2-4) to match what's shown to the user.
- `data/mock_recipes.py`, `data/mock_prices.py` — stand-ins for the real Spoonacular API and a
  live web-search pricing lookup (both are the Discovery/Design "synthetic data plan"). 31
  recipes tagged by cuisine and meal type, every one including a carb component.

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
- The calorie estimate is height/weight only (no age, sex, or activity level collected) — the
  UI says so explicitly; treat it as a rough starting point, not a clinical number.
- With a small cuisine selection and a full 7-day week (21 meal slots), the mock catalog can run
  out of unique recipes per meal type before the week is full — the no-repeat rule then falls
  back to allowing a repeat rather than leaving a slot empty. Picking more cuisines avoids this.
- Accounts live in a single local JSON file (`users_data.json`, gitignored) — fine for a local
  demo, not a real production auth store (no rate limiting, no password reset, no sessions
  beyond Streamlit's in-memory session state).
- No real checkout/store integration by design (see Discovery's human-boundary decision).
