"""Streamlit prototype for the meal-planning agent (Discovery/Design workflow, Develop phase).

Implements the Design #2 target workflow end to end, for any signed-in user:
  0. Sign up (name, username, password) or log in (username, password).
  1. Profile setup (once per account).
  2. Weekly trigger + current-weight confirmation.
  3. Cuisines, cooking pattern, cheat/eating-out flags, optional calorie target.
  4. Orchestrator -> recipe agent proposes the week.
  5. User reviews, flags dislikes / additional eating-out nights.
  6. Recipe agent revises; loop until approved.
  7. Orchestrator -> cart agent consolidates + prices the shopping list.
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
from storage import profile_store, user_store

DAYS_OF_WEEK = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

st.set_page_config(page_title="Weekly Meal Planner", page_icon="🍽️")

USING_MOCK_AGENT = not bool(os.environ.get("ANTHROPIC_API_KEY"))
recipe_agent = mock_recipe_agent if USING_MOCK_AGENT else real_recipe_agent

st.title("🍽️ Weekly Meal Planner")
st.caption(
    "Plan a week of meals tailored to you, revise on feedback, then hand off a "
    "priced shopping list. Never checks out on its own."
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


def calories_by_goal(goal, weight_lb):
    # simple placeholder estimate -- not medical advice, just enough to unblock the demo
    base = weight_lb * 15
    return int(base - 500) if goal == "weight_loss" else int(base + 300)


def save():
    """Persist the current user's state after any mutation."""
    user_store.save_state(st.session_state.username, st.session_state.store)


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
        for key in ["username", "store", "stage", "week", "cuisines", "plan", "disliked_this_session", "cart"]:
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
        cooking_days_default = st.slider("Typical cooking days per week", 1, 7, 3)
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
    with st.form("weekly_form"):
        current_weight = st.number_input("Current weight (lb)", min_value=80.0, max_value=400.0, value=180.0)
        cuisines = st.multiselect("Cuisines", all_cuisines())
        cooking_days = st.multiselect(
            "Which days will you cook this week?", DAYS_OF_WEEK,
            default=DAYS_OF_WEEK[: store["profile"]["default_cooking_days_per_week"]],
        )
        eating_out_nights = st.multiselect(
            "Any nights already known to be eating out?",
            [d for d in DAYS_OF_WEEK if d not in cooking_days],
        )
        cheat_meals_requested = st.number_input("Cheat meals this week", min_value=0, max_value=3, value=0)
        use_custom_calories = st.checkbox("Set a specific daily calorie target")
        custom_calories = None
        if use_custom_calories:
            custom_calories = st.number_input("Daily calorie target", min_value=1000, max_value=5000, value=2000)
        submitted = st.form_submit_button("Propose my week", type="primary")

        if submitted:
            errors = []
            if not cuisines:
                errors.append("Pick at least one cuisine.")
            if not cooking_days:
                errors.append("Pick at least one cooking day.")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                week = profile_store.start_new_week(store)
                profile_store.record_weight(store, week, current_weight)
                save()
                daily_calories = custom_calories or calories_by_goal(store["profile"]["goal"], current_weight)
                disliked = profile_store.active_disliked_meals(store, week)
                last_week = profile_store.last_week_recipes(store, week)

                with st.spinner("Recipe agent is proposing your week..."):
                    plan = recipe_agent.propose_week(
                        cuisines=cuisines,
                        cooking_days=cooking_days,
                        daily_calorie_target=daily_calories,
                        cheat_meals_requested=cheat_meals_requested,
                        eating_out_nights=eating_out_nights,
                        disliked_meals=disliked,
                        last_week_recipes=last_week,
                    )

                st.session_state.week = week
                st.session_state.cuisines = cuisines
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
    disliked = profile_store.active_disliked_meals(store, week)
    last_week = profile_store.last_week_recipes(store, week)

    day_rows = plan.get("days", [])
    for row in day_rows:
        if row.get("is_eating_out"):
            st.write(f"**{row['day']}** — eating out")
        else:
            tag = " 🎉 cheat meal" if row.get("is_cheat_meal") else ""
            st.write(f"**{row['day']}** — {row['recipe_name']} ({row['cuisine']}, {row['calories']} cal){tag}")
    st.info(f"Week average: {plan.get('week_avg_daily_calories', '?')} cal/day")
    if plan.get("notes"):
        st.caption(plan["notes"])

    cooked_days = [r for r in day_rows if not r.get("is_eating_out")]
    with st.form("feedback_form"):
        st.subheader("Feedback")
        disliked_now = st.multiselect(
            "Any meals you dislike and want swapped?",
            [r["recipe_name"] for r in cooked_days],
        )
        new_eating_out = st.multiselect(
            "Any additional nights you're now eating out?",
            [r["day"] for r in cooked_days],
        )
        col1, col2 = st.columns(2)
        revise = col1.form_submit_button("Revise plan")
        approve = col2.form_submit_button("Approve plan", type="primary")

        if revise:
            if not disliked_now and not new_eating_out:
                st.warning("Flag at least one meal or night before revising.")
            else:
                st.session_state.disliked_this_session.extend(disliked_now)
                for name in disliked_now:
                    profile_store.add_disliked_meal(store, name, week)
                save()
                with st.spinner("Recipe agent is revising your week..."):
                    revised = recipe_agent.revise_week(
                        current_plan=plan,
                        disliked_meal_names=disliked_now,
                        new_eating_out_nights=new_eating_out,
                        cuisines=st.session_state.cuisines,
                        disliked_meals=profile_store.active_disliked_meals(store, week),
                        last_week_recipes=last_week,
                    )
                st.session_state.plan = revised
                st.rerun()

        if approve:
            recipe_names_used = [
                r["recipe_name"] for r in day_rows if not r.get("is_eating_out") and r.get("recipe_name")
            ]
            profile_store.record_week_recipes(store, week, recipe_names_used)
            save()
            recipes_full = [recipe_by_name(n) for n in recipe_names_used]
            recipes_full = [r for r in recipes_full if r is not None]
            with st.spinner("Cart agent is building your shopping list..."):
                cart = cart_agent.build_cart(recipes_full, store["profile"]["budget"])
            st.session_state.cart = cart
            st.session_state.stage = "cart"
            st.rerun()

# ---------------------------------------------------------------------------
# Stage 7-8: final shopping list handoff
# ---------------------------------------------------------------------------
elif st.session_state.stage == "cart":
    st.header("Your shopping list")
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
