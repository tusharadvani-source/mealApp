"""Streamlit prototype for the meal-planning agent (Discovery/Design workflow, Develop phase).

Implements the Design #2 target workflow end to end, for any signed-in user, planning
at the MEAL level (breakfast, lunch, dinner are each their own slot):
  0. Sign up (name, username, password) or log in (username, password).
  1. Profile setup (once per account).
  2. Weekly trigger + current-weight confirmation, with a live maintenance/target
     calorie estimate shown (capped 400-cal deficit for weight loss, 400-cal surplus
     for bulking).
  3. Cuisines, which days to actually cook lunch/dinner, how many servings each cooked
     dish makes, per-day-per-meal eating-out flags, an optional single cheat-meal slot,
     optional calorie target override.
  4. Orchestrator -> recipe agent proposes every genuine cook occasion for the week
     (breakfast is cooked fresh daily; lunch/dinner only on the user's chosen cooking
     days -- never more days than that). Non-cooking-day lunches/dinners are filled
     locally as leftovers from a paired cooking day, using the extra servings beyond
     the first (see build_leftover_pairing / synthesize_leftovers below) -- the recipe
     agent never sees or reasons about leftover rows, it only ever proposes genuine
     cook occasions. If the chosen cooking days can't cover the week even with the
     chosen servings, the app blocks submission and asks for more cooking days or more
     servings, rather than silently cooking on extra days.
  5. User reviews (each cooked meal expandable to its full recipe, scaled to the chosen
     servings, with an explicit "per serving" calorie label; leftover meals shown as a
     simple reference to their source day), flags dislikes / additional eating-out slots.
  6. Recipe agent revises the genuine cook occasions; leftovers are resynthesized from
     the revised plan so a disliked dish disappears from both its cook day and any day
     eating its leftovers.
  7. Orchestrator -> cart agent consolidates + prices the shopping list. Only genuine
     cook occasions are priced -- a leftover day doesn't need its own groceries, since
     the 2x-serving shop for its source day already covers it (see the approve handler).
  8. Shopping list handed back to the user; nothing is ever purchased automatically.

This file is the orchestrator: it holds no meal-selection or pricing logic itself --
it only routes the user's inputs to recipe_agent / cart_agent and renders their output,
per the "orchestrator agent" role from Design #1/#3. Account auth and per-user
persistence live in storage/user_store.py; this file just gates on being logged in.
"""

import os

import streamlit as st

from agents import cart_agent
from agents import mock_recipe_agent
from agents import recipe_agent as real_recipe_agent
from data.mock_recipes import MOCK_RECIPES, all_cuisines
from nutrition import estimate_maintenance_calories, target_calories, MAX_ADJUSTMENT
from storage import profile_store, user_store

DAYS_OF_WEEK = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
MEAL_TYPES = ["breakfast", "lunch", "dinner"]
MIN_SERVINGS = 2
MAX_SERVINGS = 4

st.set_page_config(page_title="Weekly Meal Planner", page_icon="🍽️")

USING_MOCK_AGENT = not bool(os.environ.get("ANTHROPIC_API_KEY"))
recipe_agent = mock_recipe_agent if USING_MOCK_AGENT else real_recipe_agent

st.title("🍽️ Weekly Meal Planner")
st.caption(
    "Plan breakfast, lunch, and dinner tailored to you, revise on feedback, then hand "
    "off a priced shopping list. Never checks out on its own."
)

if USING_MOCK_AGENT:
    st.warning(
        "🧪 **Mock mode** — no ANTHROPIC_API_KEY set, so recipes are picked by simple "
        "cuisine/calorie filtering, not Claude. Export ANTHROPIC_API_KEY and restart "
        "to use the real recipe agent."
    )


def recipe_by_name(name):
    for r in MOCK_RECIPES:
        if r["name"] == name:
            return r
    return None


def slot_label(day, meal_type):
    return f"{day} — {meal_type.capitalize()}"


def save():
    """Persist the current user's state after any mutation."""
    user_store.save_state(st.session_state.username, st.session_state.store)


def evenly_spaced_days(n):
    """n days spread across the week, for a sensible default cooking-day selection."""
    if n <= 0:
        return []
    if n >= 7:
        return list(DAYS_OF_WEEK)
    step = 7 / n
    indices = []
    for i in range(n):
        idx = round(i * step) % 7
        if idx not in indices:
            indices.append(idx)
    i = 0
    while len(indices) < n and i < 7:
        if i not in indices:
            indices.append(i)
        i += 1
    return [DAYS_OF_WEEK[i] for i in sorted(indices)]


def build_leftover_pairing(cooking_days, servings):
    """For lunch/dinner: pair each non-cooking day with a cooking day whose spare
    servings it eats as a leftover. Each cooking day's dish yields `servings` total
    servings -- one eaten fresh, the remaining (servings - 1) available as leftovers on
    OTHER days -- so a cooking day can cover at most (servings - 1) leftover days.

    Strictly respects the chosen cooking days -- it never adds a cooking occasion on a
    day the user didn't pick. Returns (leftover_pairs, uncovered_days): leftover_pairs
    maps day -> source day; uncovered_days is any non-cooking day that couldn't be
    paired because leftover supply ran out. The caller should block submission and ask
    for more cooking days or more servings rather than silently cooking on more days
    than the user selected.
    """
    non_cooking_days = [d for d in DAYS_OF_WEEK if d not in cooking_days]
    capacity_per_day = max(0, servings - 1)
    leftover_slot_queue = [cd for cd in cooking_days for _ in range(capacity_per_day)]

    leftover_pairs = {}
    uncovered_days = []
    for i, day in enumerate(non_cooking_days):
        if i < len(leftover_slot_queue):
            leftover_pairs[day] = leftover_slot_queue[i]
        else:
            uncovered_days.append(day)
    return leftover_pairs, uncovered_days


def synthesize_leftovers(plan, leftover_rows_to_add):
    """Copy each genuine cook occasion's result onto the day(s) that eat its leftovers.
    The recipe agent never sees these rows -- they're a local, deterministic echo of
    an existing row, so there's nothing for the agent to get wrong here."""
    meals_by_key = {(m["day"], m["meal_type"]): m for m in plan["meals"]}
    full_meals = list(plan["meals"])
    for lo in leftover_rows_to_add:
        source_row = meals_by_key.get((lo["source_day"], lo["meal_type"]))
        if source_row and source_row.get("recipe_name"):
            full_meals.append(
                {
                    "day": lo["day"], "meal_type": lo["meal_type"],
                    "recipe_name": source_row["recipe_name"], "cuisine": source_row["cuisine"],
                    "calories": source_row["calories"], "is_cheat_meal": False,
                    "is_eating_out": False, "is_leftover": True,
                    "leftover_source_day": lo["source_day"],
                }
            )
        else:
            # Source day ended up with no recipe (e.g. it was flagged eating out) --
            # there's no leftover to eat, so this day has no meal here either.
            full_meals.append(
                {
                    "day": lo["day"], "meal_type": lo["meal_type"], "recipe_name": None,
                    "cuisine": None, "calories": 0, "is_cheat_meal": False,
                    "is_eating_out": True, "is_leftover": False, "leftover_source_day": None,
                }
            )
    return {
        "meals": full_meals,
        "week_avg_daily_calories": recompute_week_avg(full_meals),
        "notes": plan.get("notes", ""),
    }


def recompute_week_avg(meals):
    day_totals = {}
    for m in meals:
        if not m.get("is_eating_out") and m.get("recipe_name"):
            day_totals.setdefault(m["day"], []).append(m["calories"])
    day_sums = [sum(cals) for cals in day_totals.values()]
    return round(sum(day_sums) / len(day_sums)) if day_sums else 0


# ---------------------------------------------------------------------------
# Stage 0: auth gate -- nothing below runs until logged in
# ---------------------------------------------------------------------------
if st.session_state.get("username") is None:
    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        with st.form("login_form"):
            login_username = st.text_input("Username")
            login_password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", type="primary")
            if submitted:
                canonical, state = user_store.verify_login(login_username, login_password)
                if state is None:
                    st.error("Incorrect username or password.")
                else:
                    st.session_state.username = canonical
                    st.session_state.store = state
                    st.session_state.stage = "idle" if profile_store.has_profile(state) else "profile_setup"
                    st.rerun()

    with tab_signup:
        with st.form("signup_form"):
            signup_name = st.text_input("Your name")
            signup_username = st.text_input("Choose a username")
            signup_password = st.text_input("Choose a password", type="password")
            signup_password_confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create account", type="primary")
            if submitted:
                if signup_password != signup_password_confirm:
                    st.error("Passwords don't match.")
                else:
                    try:
                        state = user_store.create_account(signup_username, signup_password, signup_name)
                    except ValueError as e:
                        st.error(str(e))
                    else:
                        st.session_state.username = signup_username
                        st.session_state.store = state
                        st.session_state.stage = "profile_setup"
                        st.rerun()

    st.stop()

store = st.session_state.store

with st.sidebar:
    st.write(f"👤 Signed in as **{store['profile']['name'] or st.session_state.username}**")
    if st.button("Log out"):
        for key in [
            "username", "store", "stage", "week", "cuisines", "plan",
            "disliked_this_session", "cart", "leftover_rows_to_add", "servings",
        ]:
            st.session_state.pop(key, None)
        st.rerun()

if "stage" not in st.session_state:
    st.session_state.stage = "profile_setup" if not profile_store.has_profile(store) else "idle"

# ---------------------------------------------------------------------------
# Stage 1: Profile setup (once per account)
# ---------------------------------------------------------------------------
if st.session_state.stage == "profile_setup":
    st.header("First-time setup")
    with st.form("profile_form"):
        height_in = st.number_input("Height (inches)", min_value=48, max_value=96, value=70)
        goal = st.selectbox("Goal", ["weight_loss", "bulking"])
        budget = st.number_input("Weekly grocery budget ($)", min_value=10.0, value=100.0, step=5.0)
        cooking_days_default = st.slider(
            "Typical days per week you cook lunch/dinner (breakfast is always daily)", 1, 7, 4
        )
        submitted = st.form_submit_button("Save profile")
        if submitted:
            profile_store.set_profile(store, height_in, goal, budget, cooking_days_default)
            save()
            st.session_state.stage = "idle"
            st.rerun()

# ---------------------------------------------------------------------------
# Stage: idle -- trigger the weekly cycle
# ---------------------------------------------------------------------------
elif st.session_state.stage == "idle":
    st.header(f"Ready when you are, {store['profile']['name']}")
    p = store["profile"]
    st.write(f"Goal: **{p['goal']}** · Budget: **${p['budget']:.2f}/week** · Height: {p['height_in']} in")
    if st.button("Plan my next week", type="primary"):
        st.session_state.stage = "weekly_inputs"
        st.rerun()

# ---------------------------------------------------------------------------
# Stage 2-3: weekly trigger inputs
# ---------------------------------------------------------------------------
elif st.session_state.stage == "weekly_inputs":
    st.header("This week's inputs")

    # Weight lives outside the form so the calorie estimate below updates live.
    current_weight = st.number_input("Current weight (lb)", min_value=80.0, max_value=400.0, value=180.0)
    maintenance = estimate_maintenance_calories(store["profile"]["height_in"], current_weight)
    computed_target = target_calories(maintenance, store["profile"]["goal"])
    adjustment_word = "deficit" if store["profile"]["goal"] == "weight_loss" else "surplus"
    st.info(
        f"Estimated maintenance calories: **{maintenance}/day**. "
        f"With a {MAX_ADJUSTMENT}-cal {adjustment_word} for your **{store['profile']['goal']}** goal, "
        f"target: **{computed_target}/day**."
    )
    st.caption(
        "Rough estimate from height and weight only — doesn't account for age, sex, or "
        "activity level, so treat it as a starting point, not a precise number."
    )

    # These two also live outside the form: each has a dependent widget (the cheat-meal
    # day/meal pickers, the calorie override input) that must appear the moment the
    # checkbox is ticked -- widgets inside st.form only take effect on submit, so a
    # conditional-on-checkbox widget placed inside the form would never render live.
    st.subheader("Cheat meal")
    include_cheat = st.checkbox("Include one cheat meal this week?")
    cheat_day = cheat_meal_type = None
    if include_cheat:
        col1, col2 = st.columns(2)
        cheat_day = col1.selectbox("Cheat meal day", DAYS_OF_WEEK)
        cheat_meal_type = col2.selectbox("Cheat meal", ["Breakfast", "Lunch", "Dinner"])

    use_custom_calories = st.checkbox("Override the calculated calorie target")
    custom_calories = None
    if use_custom_calories:
        custom_calories = st.number_input(
            "Daily calorie target", min_value=1000, max_value=5000, value=computed_target
        )

    with st.form("weekly_form"):
        cuisines = st.multiselect("Cuisines", all_cuisines())

        st.subheader("Cooking days")
        st.caption(
            "On days you don't cook, you'll eat a leftover portion of a dish from a nearby "
            "cooking day instead of a fresh recipe. Breakfast is cooked fresh every day "
            "regardless. Pick enough cooking days (or enough servings per dish) to cover the "
            "whole week -- the app will never schedule cooking on a day you didn't select."
        )
        default_cooking_days = evenly_spaced_days(store["profile"]["default_cooking_days_per_week"])
        cooking_days = st.multiselect(
            "Which days will you cook lunch/dinner?", DAYS_OF_WEEK, default=default_cooking_days
        )
        servings = st.number_input(
            "🍽️ Servings per cooked dish (1 eaten fresh, the rest as leftovers)",
            min_value=MIN_SERVINGS, max_value=MAX_SERVINGS, value=MIN_SERVINGS,
        )

        st.subheader("Eating out")
        st.caption("For each day, flag any meals you already know you'll be eating out.")
        eating_out_by_day = {}
        for day in DAYS_OF_WEEK:
            eating_out_by_day[day] = st.multiselect(
                day, ["Breakfast", "Lunch", "Dinner"], key=f"eating_out_{day}"
            )

        submitted = st.form_submit_button("Propose my week", type="primary")

        if submitted:
            if not cuisines:
                st.error("Pick at least one cuisine.")
            else:
                eating_out_slots = [
                    {"day": day, "meal_type": mt.lower()}
                    for day in DAYS_OF_WEEK
                    for mt in eating_out_by_day[day]
                ]
                eating_out_keys = {(s["day"], s["meal_type"]) for s in eating_out_slots}

                # Breakfast: fresh every day, no leftovers.
                breakfast_slots = [
                    {"day": d, "meal_type": "breakfast"}
                    for d in DAYS_OF_WEEK
                    if (d, "breakfast") not in eating_out_keys
                ]

                # Lunch/dinner: only the days the user chose to cook get a genuine fresh
                # recipe; the rest eat a leftover paired from a cooking day's spare servings.
                leftover_pairs, uncovered_days = build_leftover_pairing(cooking_days, servings)
                lunch_dinner_slots = []
                leftover_rows_to_add = []
                blocked_uncovered = []
                for mt in ["lunch", "dinner"]:
                    for day in DAYS_OF_WEEK:
                        if (day, mt) in eating_out_keys:
                            continue
                        if day in cooking_days:
                            lunch_dinner_slots.append({"day": day, "meal_type": mt})
                        elif day in uncovered_days:
                            blocked_uncovered.append((day, mt))
                        else:
                            source_day = leftover_pairs[day]
                            if (source_day, mt) in eating_out_keys:
                                # Source day's meal is eating out -- no leftover to inherit.
                                eating_out_slots.append({"day": day, "meal_type": mt})
                            else:
                                leftover_rows_to_add.append(
                                    {"day": day, "meal_type": mt, "source_day": source_day}
                                )

                if blocked_uncovered:
                    st.error(
                        "Not enough cooking days/servings to cover the whole week without "
                        "cooking on an extra day. Uncovered: "
                        + ", ".join(f"{d} {mt}" for d, mt in blocked_uncovered)
                        + ". Add another cooking day, raise servings per dish, or mark those "
                        "meals as eating out."
                    )
                else:
                    meal_slots = breakfast_slots + lunch_dinner_slots

                    cheat_meal_slot = None
                    if include_cheat and cheat_day and cheat_meal_type:
                        candidate = {"day": cheat_day, "meal_type": cheat_meal_type.lower()}
                        if candidate in meal_slots:
                            cheat_meal_slot = candidate

                    week = profile_store.start_new_week(store)
                    profile_store.record_weight(store, week, current_weight)
                    save()
                    daily_calories = custom_calories or computed_target
                    disliked = profile_store.active_disliked_meals(store, week)
                    last_week = profile_store.last_week_recipes(store, week)

                    with st.spinner("Recipe agent is proposing your week..."):
                        plan = recipe_agent.propose_week(
                            cuisines=cuisines,
                            meal_slots=meal_slots,
                            eating_out_slots=eating_out_slots,
                            daily_calorie_target=daily_calories,
                            cheat_meal_slot=cheat_meal_slot,
                            disliked_meals=disliked,
                            last_week_recipes=last_week,
                        )
                    plan = synthesize_leftovers(plan, leftover_rows_to_add)

                    st.session_state.week = week
                    st.session_state.cuisines = cuisines
                    st.session_state.servings = servings
                    st.session_state.leftover_rows_to_add = leftover_rows_to_add
                    st.session_state.plan = plan
                    st.session_state.disliked_this_session = []
                    st.session_state.stage = "review_plan"
                    st.rerun()

# ---------------------------------------------------------------------------
# Stage 5-6: review plan, revise on feedback
# ---------------------------------------------------------------------------
elif st.session_state.stage == "review_plan":
    st.header("Proposed week")
    plan = st.session_state.plan
    week = st.session_state.week
    servings = st.session_state.servings
    disliked = profile_store.active_disliked_meals(store, week)
    last_week = profile_store.last_week_recipes(store, week)

    meal_rows = plan.get("meals", [])
    rows_by_day = {day: [] for day in DAYS_OF_WEEK}
    for row in meal_rows:
        rows_by_day.setdefault(row["day"], []).append(row)

    slot_lookup = {}  # slot_label -> (day, meal_type), for the feedback form below
    for day in DAYS_OF_WEEK:
        rows = sorted(rows_by_day.get(day, []), key=lambda r: MEAL_TYPES.index(r["meal_type"]))
        if not rows:
            continue
        day_total = sum(r["calories"] for r in rows if not r.get("is_eating_out"))
        st.markdown(f"**{day}** — {day_total} cal")
        for row in rows:
            slot_lookup[slot_label(row["day"], row["meal_type"])] = (row["day"], row["meal_type"])
            if row.get("is_eating_out"):
                st.write(f"　{row['meal_type'].capitalize()} — eating out")
            elif row.get("is_leftover"):
                st.write(
                    f"　{row['meal_type'].capitalize()} — {row['recipe_name']} "
                    f"♻️ leftover from {row['leftover_source_day']}"
                )
            else:
                tag = " 🎉 cheat meal" if row.get("is_cheat_meal") else ""
                label = f"{row['meal_type'].capitalize()} — {row['recipe_name']} ({row['cuisine']}, {row['calories']} cal per serving){tag}"
                full_recipe = recipe_by_name(row["recipe_name"])
                with st.expander(label):
                    if full_recipe:
                        st.write(f"**Ingredients (serves {servings}):**")
                        for ing in full_recipe["ingredients"]:
                            st.write(f"- {ing['quantity'] * servings} {ing['unit']} {ing['name']}")
                        st.caption(
                            f"{row['calories']} cal per serving — the extra {servings - 1} "
                            f"serving(s) cover today's leftover day(s), if any."
                        )
                    else:
                        st.caption("Ingredient details unavailable for this recipe.")

    st.info(f"Week average: {plan.get('week_avg_daily_calories', '?')} cal/day")
    if plan.get("notes"):
        st.caption(plan["notes"])

    cooked_rows = [r for r in meal_rows if not r.get("is_eating_out")]
    fresh_rows = [r for r in cooked_rows if not r.get("is_leftover")]
    with st.form("feedback_form"):
        st.subheader("Feedback")
        disliked_now = st.multiselect(
            "Any meals you dislike and want swapped?",
            sorted({r["recipe_name"] for r in fresh_rows}),
        )
        new_eating_out_labels = st.multiselect(
            "Any additional meals you're now eating out?",
            [slot_label(r["day"], r["meal_type"]) for r in cooked_rows],
        )
        col1, col2 = st.columns(2)
        revise = col1.form_submit_button("Revise plan")
        approve = col2.form_submit_button("Approve plan", type="primary")

        if revise:
            if not disliked_now and not new_eating_out_labels:
                st.warning("Flag at least one meal before revising.")
            else:
                fresh_keys = {(r["day"], r["meal_type"]) for r in fresh_rows}
                new_eating_out_keys = {slot_lookup[label] for label in new_eating_out_labels}
                # Slots on a genuine cook occasion go to the agent; slots that are
                # leftover echoes are handled locally by dropping them from the pairing.
                new_eating_out_for_agent = [
                    {"day": d, "meal_type": mt} for (d, mt) in new_eating_out_keys if (d, mt) in fresh_keys
                ]
                st.session_state.leftover_rows_to_add = [
                    lo
                    for lo in st.session_state.leftover_rows_to_add
                    if (lo["day"], lo["meal_type"]) not in new_eating_out_keys
                ]

                st.session_state.disliked_this_session.extend(disliked_now)
                for name in disliked_now:
                    profile_store.add_disliked_meal(store, name, week)
                save()

                fresh_only_plan = {"meals": fresh_rows}
                with st.spinner("Recipe agent is revising your week..."):
                    revised_fresh = recipe_agent.revise_week(
                        current_plan=fresh_only_plan,
                        disliked_meal_names=disliked_now,
                        new_eating_out_slots=new_eating_out_for_agent,
                        cuisines=st.session_state.cuisines,
                        disliked_meals=profile_store.active_disliked_meals(store, week),
                        last_week_recipes=last_week,
                    )
                revised = synthesize_leftovers(revised_fresh, st.session_state.leftover_rows_to_add)
                st.session_state.plan = revised
                st.rerun()

        if approve:
            # Only genuine cook occasions need groceries -- a leftover day's meal was
            # already paid for by its source day's 2x-serving shop (see build_cart).
            all_dish_names_used = sorted({r["recipe_name"] for r in cooked_rows if r.get("recipe_name")})
            profile_store.record_week_recipes(store, week, all_dish_names_used)
            save()
            recipes_full = [recipe_by_name(r["recipe_name"]) for r in fresh_rows if r.get("recipe_name")]
            recipes_full = [r for r in recipes_full if r is not None]
            with st.spinner("Cart agent is building your shopping list..."):
                cart = cart_agent.build_cart(recipes_full, store["profile"]["budget"], servings=servings)
            st.session_state.cart = cart
            st.session_state.stage = "cart"
            st.rerun()

# ---------------------------------------------------------------------------
# Stage 7-8: final shopping list handoff
# ---------------------------------------------------------------------------
elif st.session_state.stage == "cart":
    st.header("Your shopping list")
    st.caption(
        f"Quantities are for {st.session_state.servings} servings of each cooked dish — enough "
        "for the cook day plus its leftover day(s), where applicable."
    )
    cart = st.session_state.cart
    for item in cart["items"]:
        if item["price_unknown"]:
            st.write(f"- {item['quantity']} {item['unit']} **{item['ingredient']}** — price unknown")
        else:
            st.write(
                f"- {item['quantity']} {item['unit']} **{item['ingredient']}** — ${item['line_total']:.2f}"
            )
    st.subheader(f"Estimated total: ${cart['total']:.2f}")
    if cart["over_budget"]:
        st.warning(f"This is over your ${cart['budget']:.2f} budget.")
    if cart["price_unknown_items"]:
        st.caption(f"Price unknown for: {', '.join(cart['price_unknown_items'])}")
    st.success("You review and purchase this yourself — the agent stops here.")

    if st.button("Plan another week"):
        st.session_state.stage = "idle"
        st.rerun()
