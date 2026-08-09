# Weekly Meal Planner (prototype)

A weekly meal-planning and grocery-cart-building agent, originally scoped around one persona
(David) in the Discovery/Design sections of the Agentic AI PRD, now generalized to any signed-up
user. This is the Develop-phase prototype.

## What it does

Any user can sign up (name, username, password) or log back in. Each account triggers its own
weekly cycle, planned at the **meal level** — breakfast, lunch, and dinner are each their own
slot with their own recipe, every recipe includes a carb side so it's a complete meal, and each
recipe's ingredient list and calorie count is shown per serving. The app shows an estimated
maintenance-calorie number (from height/weight) and a capped 400-calorie deficit or surplus
target based on the user's goal.

**Cooking days and leftovers:** breakfast is always cooked fresh, every day. For lunch and
dinner, the user picks which days they'll actually cook; baseline is 1 serving = 1 meal, and the
app automatically works out how many servings each cook day's dish needs (`compute_meal_coverage`
in `app.py`) — a day cooked with no gap before the next cook day needs only 1 serving, while a
day followed by non-cooking days needs 1 (fresh) plus one more for each of those days, up to a
freshness cap (`FRESHNESS_CAP`, currently 4) so leftovers never sit for too long. Every
non-cooking day is paired with the NEAREST preceding cooking day so leftovers are always the
freshest available, and lunch/dinner are computed independently since eating-out flags differ per
meal. The app strictly respects the chosen cooking days: it never schedules a cook occasion on a
day the user didn't pick, and a leftover is never sourced from a day that hasn't been cooked yet.
If a gap between cooking days is too wide to cover within the freshness cap (including any
stretch before the week's first cooking day), submission is blocked with an error listing the
uncovered slots, asking the user to add a cooking day or mark those meals as eating out. The
recipe agent never sees or reasons about leftover days — it only ever proposes genuine cook
occasions; leftovers are synthesized locally and kept in sync across revisions, and the cart only
shops for real cook occasions, each scaled to the servings that specific dish needs (a leftover
day's groceries were already covered by its source day's shop).

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
  meals slot by slot (breakfast/lunch/dinner), using a `search_recipes` tool backed by
  `data/recipe_catalog.py`.
- `agents/mock_recipe_agent.py` — free, no-Claude-API-key fallback with the same interface, for
  testing without spending anything on Claude. Auto-selected when `ANTHROPIC_API_KEY` isn't set;
  still draws from the real Spoonacular catalog if `SPOONACULAR_API_KEY` is set, since the two
  keys are independent.
- `agents/cart_agent.py` — deterministic ingredient consolidation + mock pricing (not an LLM
  call, by design — see the module docstring for why). Takes a list of (recipe, servings) pairs
  and scales each cook occasion by its own automatically calculated servings before summing.
- `data/recipe_catalog.py` — the single place that decides mock vs. real recipes. Calls the live
  Spoonacular API (`data/spoonacular_api.py`) when `SPOONACULAR_API_KEY` is set, otherwise falls
  back to the local `data/mock_recipes.py` catalog (31 recipes, 8 cuisines, every one including a
  carb component). Both recipe agents above go through this module, and it caches every recipe a
  search returns (by name) so `app.py` can look up full ingredient details later for display and
  cart-building, since live Spoonacular results aren't a static catalog like the mock one.
- `data/spoonacular_api.py` — the real Spoonacular `complexSearch` call (cuisine + dish-type
  filters, nutrition and ingredients pulled in the same request). Raises `SpoonacularError` on
  any network/API failure rather than silently falling back — `app.py` catches that around both
  the propose and revise steps and shows the user an error with an explicit "click again to
  retry" message, per the Design failure-handling plan, instead of crashing or auto-retrying.
- `data/mock_prices.py` — stand-in for a live web-search pricing lookup (the Discovery/Design
  "synthetic data plan" for pricing; a separate swap point from the recipe catalog above — see
  the module docstring for where the swap goes).

## Running it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional — omit either or both to run in free/mock mode:
export ANTHROPIC_API_KEY=sk-ant-...       # omit -> free rule-based recipe picking, no Claude calls
export SPOONACULAR_API_KEY=...            # omit -> small local mock recipe catalog

streamlit run app.py
```

The two keys are independent: you can run with real recipes but a mock (free) planner, a real
Claude planner over the mock catalog, both real, or both mock. The app shows a warning banner for
whichever piece is running in mock mode.

## Known limitations (v1 prototype)

- Grocery prices are still mock data, not a live web-search pricing lookup (a separate,
  not-yet-built swap point from the Spoonacular recipe integration above).
- The calorie estimate is height/weight only (no age, sex, or activity level collected) — the
  UI says so explicitly; treat it as a rough starting point, not a clinical number.
- In mock-catalog mode, a small cuisine selection with a full 7-day week (21 meal slots) can run
  out of unique recipes per meal type before the week is full — the no-repeat rule then falls
  back to allowing a repeat rather than leaving a slot empty. Picking more cuisines avoids this;
  the real Spoonacular catalog has enough variety that this shouldn't come up.
- Spoonacular's free tier is rate-limited (150 points/day); a single week proposal can use a
  meaningful chunk of that (each `search_recipes` call costs ~1-1.5 points, and the agent calls
  it once per slot needing a recipe). A `SpoonacularError` (including a quota error) is surfaced
  as a UI message asking the user to retry, not retried automatically.
- Accounts live in a single local JSON file (`users_data.json`, gitignored) — fine for a local
  demo, not a real production auth store (no rate limiting, no password reset, no sessions
  beyond Streamlit's in-memory session state).
- No real checkout/store integration by design (see Discovery's human-boundary decision).
