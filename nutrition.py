"""Calorie estimation: maintenance calories plus a capped deficit/surplus target.

Deliberately height+weight only, per the product decision to not collect age or
biological sex. That means this is a rough estimate, not a clinical BMR/TDEE
calculation (real formulas like Mifflin-St Jeor need age and sex too) -- the UI
must say so, not present this as precise. We approximate with the Mifflin-St
Jeor weight/height terms, a sex-neutral offset (average of the male/female
constants), an assumed average age (30), and a moderate-activity multiplier.

MAX_ADJUSTMENT is the hard cap Design settled on: at most a 400-calorie
deficit for weight loss, at most a 400-calorie surplus for bulking.
"""

MAX_ADJUSTMENT = 400
ASSUMED_AGE = 30
ACTIVITY_MULTIPLIER = 1.375  # light-to-moderate activity, since we don't collect an activity level

MEAL_CALORIE_SPLIT = {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.40}


def target_for_meal(daily_calorie_target, meal_type):
    return round(daily_calorie_target * MEAL_CALORIE_SPLIT[meal_type])


def estimate_maintenance_calories(height_in, weight_lb):
    """Rough maintenance-calorie (TDEE) estimate from height and weight alone."""
    weight_kg = weight_lb * 0.453592
    height_cm = height_in * 2.54
    sex_neutral_offset = (5 + -161) / 2  # average of the Mifflin-St Jeor male/female constants
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * ASSUMED_AGE + sex_neutral_offset
    return round(bmr * ACTIVITY_MULTIPLIER)


def target_calories(maintenance_calories, goal):
    """Daily calorie target after applying the capped deficit/surplus for the goal."""
    if goal == "weight_loss":
        return maintenance_calories - MAX_ADJUSTMENT
    if goal == "bulking":
        return maintenance_calories + MAX_ADJUSTMENT
    return maintenance_calories
