"""Mock ingredient price table standing in for the live web-search pricing lookup (v1 prototype).

Prices are rough US grocery averages per the unit each ingredient is normally sold/measured in.
Real version will replace price_for_ingredient() with a web-search tool call ("average price of X"),
keeping the same (ingredient_name, quantity, unit) -> price interface.
"""

MOCK_PRICES_PER_UNIT = {
    "pizza dough": 2.50,
    "mozzarella cheese": 5.00,
    "tomato": 0.60,
    "basil": 2.50,
    "olive oil": 0.75,
    "fettuccine": 2.20,
    "chicken breast": 4.50,
    "heavy cream": 3.20,
    "parmesan cheese": 6.50,
    "garlic": 0.40,
    "carrot": 0.50,
    "celery": 1.80,
    "cannellini beans": 1.60,
    "diced tomato": 1.40,
    "pasta": 1.90,
    "yogurt": 3.00,
    "garam masala": 3.50,
    "rice": 0.90,
    "chickpeas": 1.30,
    "onion": 0.70,
    "peas": 1.50,
    "ground beef": 5.50,
    "corn tortilla": 2.80,
    "cheddar cheese": 4.80,
    "lettuce": 1.90,
    "black beans": 1.30,
    "corn": 1.20,
    "avocado": 1.50,
    "enchilada sauce": 2.10,
    "peanuts": 2.60,
    "bell pepper": 1.10,
    "soy sauce": 2.90,
    "egg": 3.50,
    "flank steak": 8.00,
    "broccoli": 2.20,
    "rice noodles": 2.40,
    "shrimp": 8.50,
    "bean sprouts": 1.20,
    "coconut milk": 2.30,
    "green curry paste": 3.80,
    "mushroom": 2.50,
    "lemongrass": 1.80,
    "lime": 0.50,
    "chili": 0.60,
    "cucumber": 0.90,
    "feta cheese": 4.20,
    "kalamata olives": 4.50,
    "pita bread": 2.60,
    "tahini": 5.50,
    "salmon fillet": 9.50,
    "lemon": 0.60,
    "potato": 0.80,
    "ground turkey": 5.00,
    "kidney beans": 1.30,
    "burger bun": 3.00,
    "chicken thigh": 3.80,
    "sesame oil": 4.50,
    "tofu": 2.50,
    "miso paste": 4.00,
    "green onion": 1.20,
    "seaweed": 3.00,
}

DEFAULT_PRICE_PER_UNIT = 2.00


def price_for_ingredient(name: str):
    """Rough average price for one unit of the ingredient. None if genuinely unpriceable."""
    return MOCK_PRICES_PER_UNIT.get(name.lower())
