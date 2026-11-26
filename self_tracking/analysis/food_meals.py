"""Group logged food items into ingredients, and ingredient combos into meals.

Food names are brand-specific and differ between diet apps, so each name is
mapped to a broad ingredient (``item``) by the first regex in ``ITEM_RULES``
that matches. Each logged meal (date + meal slot) is then the set of its
items, and ``MEAL_RULES`` names the first recurring meal type that set fits.
"""

import re
import pandas as pd
import self_tracking.data as d

# (item, regex) — order matters: first match wins
ITEM_RULES = [
    ("muesli_recipe", r"^meal: muesli|muesli (nut )?mix"),
    ("pizza", r"pizza"),
    ("crisps", r"crisp|hula hoops|popcorn|wotsits|doritos|proper ?chips|lentil chips|walkers|mccoy|pork puffs|nudie|popped|potato grills|tortilla chips|popchips|kettle chips|corn puffs|harvest snaps|cheetos"),
    ("ketchup", r"ketchup"),
    ("huel_pancake_recipe", r"^meal: huel pancake"),
    ("meal_recipe", r"^meal:"),
    ("collagen_coffee", r"collagen.*coffee|coffee.*collagen"),
    ("collagen", r"collagen"),
    ("huel_hot", r"huel.*(hot & savoury|mac & cheeze|chick'?n|bolognese|pasta|curry|chilli|savoury|thai|mexican|sweet & sour|madras|cajun)"),
    ("huel_bar", r"huel.*bar"),
    ("protein_bar", r"protein (bar|flap ?jack|oat bar|slice)|raw protein|warrior crunch|fulfil|barebells|bodyme|grenade|nugo|hi protein|protein packed|protein.*bar|bar.*protein|choc chew|baked cookie|nature valley protein|pea-nut square"),
    ("protein_powder", r"huel complete protein|huel protein|protein powder|whey|casein|wondershake|clear vegan|pea protein|rice protein|soy protein|beef protein|vegan protein|lean shake|diet protein|lean matrix|protein mix|smart plant|protein .*(vanilla|chocolate|banana|strawberr)|banana milkshake protein|isolate"),
    ("huel_shake", r"huel|nutritionally complete"),
    ("coffee_drink", r"coffee|cappuccino|latte|dolce gusto|nescaf"),
    ("egg_white", r"egg whites?"),
    ("egg_sandwich", r"egg (&|and) bacon|egg mayo"),
    ("sandwich_deal", r"sandwich|sub roll|meal deal|chicken club|wrap by tesco|bbq chicken & coleslaw wrap|brie &"),
    ("salad_kit", r"caesar salad|layered salad|salad kit|coleslaw kit|pasta salad"),
    ("egg", r"\beggs?\b"),
    ("pb_powder", r"powdered peanut|pb2|pb & me"),
    ("peanut_butter", r"peanut butter|almond butter|nut butter"),
    ("oat_milk", r"oatly|oat drink|creamy oat|alpro oat|oat chilled|oat no sugar"),
    ("plant_milk", r"m\*lk|almond sweetened|coco drink|almond drink|alpro.*almond|koko|like milk|soya drink|coconut drink|almond bechamel"),
    ("milk", r"^(?!.*(chocolate|potato)).*(semi skimmed|skimmed|^milk|british milk|whole 3.7|pints)"),
    ("granola", r"granola"),
    ("overnight_oats", r"overnight oats"),
    ("oats", r"\boats?\b|porridge"),
    ("yogurt", r"skyr|yog(h)?urt|fage|quark"),
    ("cocoa", r"cocoa powder|^cocoa|cocoa by"),
    ("dark_choc", r"dark choc|cocoa solids|% cocoa|lindt|ugandan|moser roth|booja|truffle|chocolate bar|^chocolate$"),
    ("chia_flax", r"chia|flax"),
    ("dried_fruit", r"dates|sultana|raisin(?!.*bagel)|mixed fruit|dried"),
    ("bagel", r"bagel"),
    ("wrap", r"wrap"),
    ("toast_bread", r"bread|toast|hovis|sourdough|pitta|warburtons.*(thick|medium)"),
    ("jam_honey", r"conserve|jam\b|marmalade|honey(?!.*(chipotle|berry))|maple syrup|syrup"),
    ("sugar", r"demerara|^sugar$|caster sugar|granulated"),
    ("frozen_berries", r"summer fruits|mixed berries|berries medley|smoothie mix|black for(r)?est|frozen.*(berr|blueberr|strawberr|mango|fruit)|freshly frozen|mixed fruits|frozen strawberries|frozen mangos|frozen for freshness"),
    ("berries", r"strawberr|blueberr|raspberr|cherries|blackberr"),
    ("banana", r"banana"),
    ("apple", r"apple(?! juice)|braeburn|royal gala|granny smith|jazz"),
    ("pear", r"pear"),
    ("grapes", r"grape"),
    ("citrus", r"orange|tangerine|satsuma|clementine|mandarin"),
    ("stone_fruit", r"nectarine|plum|peach|mango|apricot"),
    ("melon", r"melon"),
    ("avocado", r"avocado"),
    ("sauce", r"sauce|mayonnaise|perinaise|mayo|bbq|pesto|salsa"),
    ("olive_oil", r"olive oil|sunflower oil|oil spray|frylight|cooking spray|\boil\b"),
    ("butter", r"butter(?!kist|nut)|lurpak"),
    ("cheese", r"cheese|cheddar|mozzarella|parmesan|feta|halloumi"),
    ("chicken", r"chicken"),
    ("beef_mince", r"beef|mince"),
    ("bacon_sausage", r"bacon|sausage|ham\b"),
    ("fish", r"salmon|cod|tuna|prawn|fish"),
    ("rice", r"\brice\b(?! cake)"),
    ("rice_cakes", r"rice cake|snack a jacks|kallo"),
    ("pasta_noodles", r"pasta|penne|spaghetti|noodle|fusilli"),
    ("chips_potato", r"chips straight|home chips|fries|potato(?!.*(crisp|snack|grill))|potatoes"),
    ("beans", r"beans?\b|beanz|chick ?peas|lentils"),
    ("peas_corn", r"peas\b|sweetcorn"),
    ("veg", r"pepper|onion|mushroom|kale|broccoli|courgette|tomato|spinach|carrot|cucumber|lettuce|cabbage|vegetable|medley|stir-fry|tofu|celery|garlic|leek|cauliflower|sprout|salad"),
    ("biscuit_sweet", r"biscuit|leibniz|cookie|kit kat|fibre one|doughnut|brownie|cake|krispies|halva|licorice|ice cream|halo top|lolly|lollies|ice pops|chocolate"),
    ("alcohol", r"whisk|cider|beer|ipa|lager|wine|gin|prosecco|stout|ale\b"),
    ("soft_drink", r"juice|lemonade|cola|pepsi|energy drink|squash|water"),
    ("nuts", r"almonds|cashew|walnut|peanuts|pistachio|nuts\b|seeds"),
]
_ITEM_RX = [(item, re.compile(pattern, re.I)) for item, pattern in ITEM_RULES]


def item_for(desc: str) -> str:
    for item, rx in _ITEM_RX:
        if rx.search(desc):
            return item
    return "other"


POWDER = {"huel_shake", "protein_powder", "huel_pancake_recipe"}
FRUIT = {"berries", "frozen_berries", "banana", "apple", "grapes", "stone_fruit", "pear", "citrus", "melon"}
DRINKS = {"oat_milk", "plant_milk", "milk", "collagen", "collagen_coffee", "coffee_drink", "soft_drink"}
SHAKE_EXTRAS = {"huel_shake", "protein_powder", "banana", "collagen", "berries", "frozen_berries"} | DRINKS

# (meal, is it a breakfast-type meal, test on the meal's set of items)
# order matters: first match wins
MEAL_RULES = [
    ("Protein pancakes", True, lambda s: "huel_pancake_recipe" in s or ("egg" in s and bool(s & POWDER) and not s & {"bagel", "toast_bread"})),
    ("French toast", True, lambda s: "toast_bread" in s and ("egg_white" in s or ("egg" in s and bool(s & (FRUIT | {"oat_milk"}))))),
    ("Choc PB overnight oats", True, lambda s: "oats" in s and bool(s & {"cocoa", "chia_flax", "pb_powder"})),
    ("Protein porridge", True, lambda s: "oats" in s and bool(s & {"protein_powder", "collagen_coffee"})),
    ("Oats + skyr", True, lambda s: {"oats", "yogurt"} <= s),
    ("Muesli/granola + yogurt", True, lambda s: bool(s & {"muesli_recipe", "granola"})),
    ("Egg & avocado bagel", True, lambda s: {"bagel", "egg", "avocado"} <= s),
    ("Egg (& bacon) bagel", True, lambda s: {"bagel", "egg"} <= s),
    ("Bagel + PB", True, lambda s: {"bagel", "peanut_butter"} <= s),
    ("Huel shake", True, lambda s: "huel_shake" in s and s <= SHAKE_EXTRAS),
    ("Fry-up", True, lambda s: "bacon_sausage" in s and bool(s & {"egg", "toast_bread"})),
    ("Omelette / eggs + veg", True, lambda s: {"egg", "veg"} <= s and "chicken" not in s),
    ("Meal deal / sandwich", False, lambda s: bool(s & {"sandwich_deal", "egg_sandwich"})),
    ("Salad kit", False, lambda s: "salad_kit" in s),
    ("Huel Hot & Savoury", False, lambda s: "huel_hot" in s),
    ("Pizza", False, lambda s: "pizza" in s),
    ("Fish & chips", False, lambda s: {"fish", "chips_potato"} <= s),
    ("Chicken & chips", False, lambda s: {"chicken", "chips_potato"} <= s),
    ("Chicken wrap", False, lambda s: {"chicken", "wrap"} <= s),
    ("Chicken + rice/pasta + veg", False, lambda s: "chicken" in s and bool(s & {"rice", "pasta_noodles"})),
    ("Chicken + veg", False, lambda s: {"chicken", "veg"} <= s),
    ("Mince dish", False, lambda s: "beef_mince" in s and bool(s & {"veg", "sauce", "rice", "pasta_noodles", "beans", "chips_potato"})),
    ("Plain chicken", False, lambda s: "chicken" in s),
]
BREAKFASTS = [name for name, is_breakfast, _ in MEAL_RULES if is_breakfast]


def meal_for(items: set[str]) -> str | None:
    for name, _, test in MEAL_RULES:
        if test(items):
            return name
    return None


def foods() -> pd.DataFrame:
    """data.foods() with an ``item`` column."""
    df = d.foods()
    items = {desc: item_for(desc) for desc in df.desc.unique()}
    return df.assign(item=df.desc.map(items))


def meals(foods_df: pd.DataFrame) -> pd.DataFrame:
    """One row per logged meal: date, meal slot, set of items, meal type."""
    df = foods_df.groupby(["date", "meal"]).item.agg(set).reset_index(name="items")
    return df.assign(meal_type=df["items"].map(meal_for))
