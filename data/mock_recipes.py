"""Mock recipe catalog standing in for the Spoonacular API (v1 prototype).

Each recipe: name, cuisine, meal_type ("breakfast" | "lunch" | "dinner"),
calories (per serving), ingredients (name, quantity, unit) -- quantities are
for ONE serving; the app scales them up for display/shopping (see
SERVING_MULTIPLIER in app.py / cart_agent.py). Every recipe includes a carb
component (rice, bread, pasta, tortilla, etc.) so it reads as a complete
meal, not just a protein/veg dish.

Real Spoonacular integration will replace MOCK_RECIPES lookups with live API
calls, keeping the same shape so recipe_agent.py doesn't change.
"""

MOCK_RECIPES = [
    # ---------------------------------------------------------------- Italian
    {
        "name": "Margherita Pizza",
        "cuisine": "Italian",
        "meal_type": "dinner",
        "calories": 780,
        "ingredients": [
            {"name": "pizza dough", "quantity": 1, "unit": "ball"},
            {"name": "mozzarella cheese", "quantity": 8, "unit": "oz"},
            {"name": "tomato", "quantity": 3, "unit": "each"},
            {"name": "basil", "quantity": 1, "unit": "bunch"},
            {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
        ],
    },
    {
        "name": "Chicken Alfredo Pasta",
        "cuisine": "Italian",
        "meal_type": "dinner",
        "calories": 820,
        "ingredients": [
            {"name": "fettuccine", "quantity": 12, "unit": "oz"},
            {"name": "chicken breast", "quantity": 1, "unit": "lb"},
            {"name": "heavy cream", "quantity": 1, "unit": "cup"},
            {"name": "parmesan cheese", "quantity": 4, "unit": "oz"},
            {"name": "garlic", "quantity": 3, "unit": "clove"},
        ],
    },
    {
        "name": "Minestrone Soup",
        "cuisine": "Italian",
        "meal_type": "lunch",
        "calories": 340,
        "ingredients": [
            {"name": "carrot", "quantity": 2, "unit": "each"},
            {"name": "celery", "quantity": 2, "unit": "stalk"},
            {"name": "cannellini beans", "quantity": 1, "unit": "can"},
            {"name": "diced tomato", "quantity": 1, "unit": "can"},
            {"name": "pasta", "quantity": 1, "unit": "cup"},
        ],
    },
    {
        "name": "Italian Frittata with Toast",
        "cuisine": "Italian",
        "meal_type": "breakfast",
        "calories": 400,
        "ingredients": [
            {"name": "egg", "quantity": 5, "unit": "each"},
            {"name": "parmesan cheese", "quantity": 2, "unit": "oz"},
            {"name": "bell pepper", "quantity": 1, "unit": "each"},
            {"name": "onion", "quantity": 0.5, "unit": "each"},
            {"name": "bread", "quantity": 4, "unit": "slice"},
        ],
    },
    # ----------------------------------------------------------------- Indian
    {
        "name": "Chicken Tikka Masala",
        "cuisine": "Indian",
        "meal_type": "dinner",
        "calories": 690,
        "ingredients": [
            {"name": "chicken breast", "quantity": 1.5, "unit": "lb"},
            {"name": "yogurt", "quantity": 1, "unit": "cup"},
            {"name": "tomato", "quantity": 4, "unit": "each"},
            {"name": "heavy cream", "quantity": 0.5, "unit": "cup"},
            {"name": "garam masala", "quantity": 2, "unit": "tbsp"},
            {"name": "rice", "quantity": 2, "unit": "cup"},
        ],
    },
    {
        "name": "Chana Masala",
        "cuisine": "Indian",
        "meal_type": "lunch",
        "calories": 420,
        "ingredients": [
            {"name": "chickpeas", "quantity": 2, "unit": "can"},
            {"name": "onion", "quantity": 2, "unit": "each"},
            {"name": "tomato", "quantity": 3, "unit": "each"},
            {"name": "garlic", "quantity": 3, "unit": "clove"},
            {"name": "rice", "quantity": 2, "unit": "cup"},
        ],
    },
    {
        "name": "Vegetable Biryani",
        "cuisine": "Indian",
        "meal_type": "dinner",
        "calories": 560,
        "ingredients": [
            {"name": "rice", "quantity": 3, "unit": "cup"},
            {"name": "carrot", "quantity": 2, "unit": "each"},
            {"name": "peas", "quantity": 1, "unit": "cup"},
            {"name": "onion", "quantity": 2, "unit": "each"},
            {"name": "garam masala", "quantity": 1, "unit": "tbsp"},
        ],
    },
    {
        "name": "Masala Omelette with Toast",
        "cuisine": "Indian",
        "meal_type": "breakfast",
        "calories": 380,
        "ingredients": [
            {"name": "egg", "quantity": 4, "unit": "each"},
            {"name": "onion", "quantity": 1, "unit": "each"},
            {"name": "tomato", "quantity": 1, "unit": "each"},
            {"name": "garam masala", "quantity": 1, "unit": "tbsp"},
            {"name": "bread", "quantity": 4, "unit": "slice"},
        ],
    },
    # ---------------------------------------------------------------- Mexican
    {
        "name": "Beef Tacos",
        "cuisine": "Mexican",
        "meal_type": "dinner",
        "calories": 610,
        "ingredients": [
            {"name": "ground beef", "quantity": 1, "unit": "lb"},
            {"name": "corn tortilla", "quantity": 8, "unit": "each"},
            {"name": "cheddar cheese", "quantity": 4, "unit": "oz"},
            {"name": "lettuce", "quantity": 1, "unit": "head"},
            {"name": "tomato", "quantity": 2, "unit": "each"},
        ],
    },
    {
        "name": "Chicken Burrito Bowl",
        "cuisine": "Mexican",
        "meal_type": "lunch",
        "calories": 700,
        "ingredients": [
            {"name": "chicken breast", "quantity": 1, "unit": "lb"},
            {"name": "rice", "quantity": 2, "unit": "cup"},
            {"name": "black beans", "quantity": 1, "unit": "can"},
            {"name": "corn", "quantity": 1, "unit": "cup"},
            {"name": "avocado", "quantity": 1, "unit": "each"},
        ],
    },
    {
        "name": "Veggie Enchiladas",
        "cuisine": "Mexican",
        "meal_type": "dinner",
        "calories": 480,
        "ingredients": [
            {"name": "corn tortilla", "quantity": 8, "unit": "each"},
            {"name": "black beans", "quantity": 1, "unit": "can"},
            {"name": "cheddar cheese", "quantity": 6, "unit": "oz"},
            {"name": "onion", "quantity": 1, "unit": "each"},
            {"name": "enchilada sauce", "quantity": 1, "unit": "can"},
        ],
    },
    {
        "name": "Breakfast Burrito",
        "cuisine": "Mexican",
        "meal_type": "breakfast",
        "calories": 450,
        "ingredients": [
            {"name": "corn tortilla", "quantity": 4, "unit": "each"},
            {"name": "egg", "quantity": 4, "unit": "each"},
            {"name": "cheddar cheese", "quantity": 2, "unit": "oz"},
            {"name": "black beans", "quantity": 0.5, "unit": "can"},
            {"name": "onion", "quantity": 0.5, "unit": "each"},
        ],
    },
    # ---------------------------------------------------------------- Chinese
    {
        "name": "Kung Pao Chicken",
        "cuisine": "Chinese",
        "meal_type": "dinner",
        "calories": 640,
        "ingredients": [
            {"name": "chicken breast", "quantity": 1, "unit": "lb"},
            {"name": "peanuts", "quantity": 0.5, "unit": "cup"},
            {"name": "bell pepper", "quantity": 2, "unit": "each"},
            {"name": "soy sauce", "quantity": 3, "unit": "tbsp"},
            {"name": "rice", "quantity": 2, "unit": "cup"},
        ],
    },
    {
        "name": "Vegetable Fried Rice",
        "cuisine": "Chinese",
        "meal_type": "lunch",
        "calories": 460,
        "ingredients": [
            {"name": "rice", "quantity": 3, "unit": "cup"},
            {"name": "egg", "quantity": 2, "unit": "each"},
            {"name": "carrot", "quantity": 1, "unit": "each"},
            {"name": "peas", "quantity": 1, "unit": "cup"},
            {"name": "soy sauce", "quantity": 2, "unit": "tbsp"},
        ],
    },
    {
        "name": "Beef and Broccoli",
        "cuisine": "Chinese",
        "meal_type": "dinner",
        "calories": 590,
        "ingredients": [
            {"name": "flank steak", "quantity": 1, "unit": "lb"},
            {"name": "broccoli", "quantity": 1, "unit": "head"},
            {"name": "soy sauce", "quantity": 3, "unit": "tbsp"},
            {"name": "garlic", "quantity": 2, "unit": "clove"},
            {"name": "rice", "quantity": 2, "unit": "cup"},
        ],
    },
    {
        "name": "Congee with Scallions",
        "cuisine": "Chinese",
        "meal_type": "breakfast",
        "calories": 320,
        "ingredients": [
            {"name": "rice", "quantity": 1, "unit": "cup"},
            {"name": "green onion", "quantity": 1, "unit": "bunch"},
            {"name": "egg", "quantity": 2, "unit": "each"},
            {"name": "soy sauce", "quantity": 1, "unit": "tbsp"},
            {"name": "sesame oil", "quantity": 1, "unit": "tbsp"},
        ],
    },
    # ------------------------------------------------------------------ Thai
    {
        "name": "Pad Thai",
        "cuisine": "Thai",
        "meal_type": "dinner",
        "calories": 650,
        "ingredients": [
            {"name": "rice noodles", "quantity": 8, "unit": "oz"},
            {"name": "shrimp", "quantity": 0.75, "unit": "lb"},
            {"name": "egg", "quantity": 2, "unit": "each"},
            {"name": "peanuts", "quantity": 0.25, "unit": "cup"},
            {"name": "bean sprouts", "quantity": 1, "unit": "cup"},
        ],
    },
    {
        "name": "Green Curry Chicken",
        "cuisine": "Thai",
        "meal_type": "dinner",
        "calories": 610,
        "ingredients": [
            {"name": "chicken breast", "quantity": 1, "unit": "lb"},
            {"name": "coconut milk", "quantity": 1, "unit": "can"},
            {"name": "green curry paste", "quantity": 3, "unit": "tbsp"},
            {"name": "bell pepper", "quantity": 2, "unit": "each"},
            {"name": "rice", "quantity": 2, "unit": "cup"},
        ],
    },
    {
        "name": "Tom Yum Soup",
        "cuisine": "Thai",
        "meal_type": "lunch",
        "calories": 310,
        "ingredients": [
            {"name": "shrimp", "quantity": 0.5, "unit": "lb"},
            {"name": "mushroom", "quantity": 1, "unit": "cup"},
            {"name": "lemongrass", "quantity": 2, "unit": "stalk"},
            {"name": "lime", "quantity": 2, "unit": "each"},
            {"name": "chili", "quantity": 2, "unit": "each"},
            {"name": "rice", "quantity": 1, "unit": "cup"},
        ],
    },
    {
        "name": "Thai Rice Porridge",
        "cuisine": "Thai",
        "meal_type": "breakfast",
        "calories": 380,
        "ingredients": [
            {"name": "rice", "quantity": 1, "unit": "cup"},
            {"name": "chicken breast", "quantity": 0.5, "unit": "lb"},
            {"name": "egg", "quantity": 2, "unit": "each"},
            {"name": "green onion", "quantity": 1, "unit": "bunch"},
            {"name": "soy sauce", "quantity": 1, "unit": "tbsp"},
        ],
    },
    # --------------------------------------------------------- Mediterranean
    {
        "name": "Greek Chicken Salad",
        "cuisine": "Mediterranean",
        "meal_type": "lunch",
        "calories": 480,
        "ingredients": [
            {"name": "chicken breast", "quantity": 1, "unit": "lb"},
            {"name": "cucumber", "quantity": 1, "unit": "each"},
            {"name": "feta cheese", "quantity": 4, "unit": "oz"},
            {"name": "kalamata olives", "quantity": 0.5, "unit": "cup"},
            {"name": "tomato", "quantity": 2, "unit": "each"},
            {"name": "pita bread", "quantity": 2, "unit": "each"},
        ],
    },
    {
        "name": "Falafel Wrap",
        "cuisine": "Mediterranean",
        "meal_type": "lunch",
        "calories": 520,
        "ingredients": [
            {"name": "chickpeas", "quantity": 2, "unit": "can"},
            {"name": "pita bread", "quantity": 4, "unit": "each"},
            {"name": "tahini", "quantity": 3, "unit": "tbsp"},
            {"name": "cucumber", "quantity": 1, "unit": "each"},
            {"name": "lettuce", "quantity": 1, "unit": "head"},
        ],
    },
    {
        "name": "Chicken Gyro Platter",
        "cuisine": "Mediterranean",
        "meal_type": "dinner",
        "calories": 620,
        "ingredients": [
            {"name": "chicken breast", "quantity": 1.25, "unit": "lb"},
            {"name": "pita bread", "quantity": 4, "unit": "each"},
            {"name": "cucumber", "quantity": 1, "unit": "each"},
            {"name": "tomato", "quantity": 2, "unit": "each"},
            {"name": "feta cheese", "quantity": 3, "unit": "oz"},
            {"name": "tahini", "quantity": 2, "unit": "tbsp"},
        ],
    },
    {
        "name": "Shakshuka",
        "cuisine": "Mediterranean",
        "meal_type": "breakfast",
        "calories": 390,
        "ingredients": [
            {"name": "egg", "quantity": 6, "unit": "each"},
            {"name": "tomato", "quantity": 5, "unit": "each"},
            {"name": "bell pepper", "quantity": 1, "unit": "each"},
            {"name": "onion", "quantity": 1, "unit": "each"},
            {"name": "feta cheese", "quantity": 3, "unit": "oz"},
            {"name": "bread", "quantity": 4, "unit": "slice"},
        ],
    },
    # -------------------------------------------------------------- American
    {
        "name": "Grilled Salmon with Veggies",
        "cuisine": "American",
        "meal_type": "dinner",
        "calories": 540,
        "ingredients": [
            {"name": "salmon fillet", "quantity": 1.5, "unit": "lb"},
            {"name": "broccoli", "quantity": 1, "unit": "head"},
            {"name": "lemon", "quantity": 2, "unit": "each"},
            {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
            {"name": "potato", "quantity": 4, "unit": "each"},
        ],
    },
    {
        "name": "Turkey Chili",
        "cuisine": "American",
        "meal_type": "dinner",
        "calories": 460,
        "ingredients": [
            {"name": "ground turkey", "quantity": 1, "unit": "lb"},
            {"name": "kidney beans", "quantity": 1, "unit": "can"},
            {"name": "diced tomato", "quantity": 1, "unit": "can"},
            {"name": "onion", "quantity": 1, "unit": "each"},
            {"name": "bell pepper", "quantity": 1, "unit": "each"},
            {"name": "bread", "quantity": 4, "unit": "slice"},
        ],
    },
    {
        "name": "Classic Cheeseburger",
        "cuisine": "American",
        "meal_type": "lunch",
        "calories": 850,
        "ingredients": [
            {"name": "ground beef", "quantity": 1.25, "unit": "lb"},
            {"name": "burger bun", "quantity": 4, "unit": "each"},
            {"name": "cheddar cheese", "quantity": 4, "unit": "oz"},
            {"name": "lettuce", "quantity": 1, "unit": "head"},
            {"name": "tomato", "quantity": 2, "unit": "each"},
        ],
    },
    {
        "name": "Avocado Toast with Eggs",
        "cuisine": "American",
        "meal_type": "breakfast",
        "calories": 420,
        "ingredients": [
            {"name": "bread", "quantity": 4, "unit": "slice"},
            {"name": "egg", "quantity": 4, "unit": "each"},
            {"name": "avocado", "quantity": 2, "unit": "each"},
            {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
            {"name": "lemon", "quantity": 1, "unit": "each"},
        ],
    },
    # -------------------------------------------------------------- Japanese
    {
        "name": "Chicken Teriyaki Bowl",
        "cuisine": "Japanese",
        "meal_type": "dinner",
        "calories": 610,
        "ingredients": [
            {"name": "chicken thigh", "quantity": 1.25, "unit": "lb"},
            {"name": "soy sauce", "quantity": 3, "unit": "tbsp"},
            {"name": "rice", "quantity": 2, "unit": "cup"},
            {"name": "broccoli", "quantity": 1, "unit": "head"},
            {"name": "sesame oil", "quantity": 1, "unit": "tbsp"},
        ],
    },
    {
        "name": "Salmon Sushi Bowl",
        "cuisine": "Japanese",
        "meal_type": "lunch",
        "calories": 520,
        "ingredients": [
            {"name": "salmon fillet", "quantity": 0.75, "unit": "lb"},
            {"name": "rice", "quantity": 2, "unit": "cup"},
            {"name": "cucumber", "quantity": 1, "unit": "each"},
            {"name": "avocado", "quantity": 1, "unit": "each"},
            {"name": "soy sauce", "quantity": 2, "unit": "tbsp"},
        ],
    },
    {
        "name": "Miso Soup with Tofu",
        "cuisine": "Japanese",
        "meal_type": "breakfast",
        "calories": 260,
        "ingredients": [
            {"name": "tofu", "quantity": 1, "unit": "block"},
            {"name": "miso paste", "quantity": 3, "unit": "tbsp"},
            {"name": "green onion", "quantity": 1, "unit": "bunch"},
            {"name": "seaweed", "quantity": 1, "unit": "sheet"},
            {"name": "rice", "quantity": 1, "unit": "cup"},
        ],
    },
]


def all_cuisines():
    return sorted({r["cuisine"] for r in MOCK_RECIPES})


def recipes_for_meal_type(meal_type):
    return [r for r in MOCK_RECIPES if r["meal_type"] == meal_type]
