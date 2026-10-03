"""
NutriGen AI - Deterministic Constraint Validation & Grocery Consolidation Engine
Implements Problem 14: Constraint-Based Weekly Meal Planner validation,
including vegetarian verification, budget checks, cooking time limits,
ingredient reuse metrics, pantry utilization, weekly variety rules,
and general non-medical nutrition balance heuristics.
"""

import re
import json
from typing import Dict, Any, List, Tuple, Optional


# ==========================================
# 1. Non-Vegetarian & Allergy Keywords
# ==========================================

NON_VEGETARIAN_KEYWORDS = [
    "chicken", "mutton", "beef", "pork", "fish", "prawn", "prawns", "shrimp",
    "bacon", "ham", "lamb", "crab", "lobster", "salmon", "tuna", "turkey",
    "veal", "duck", "squid", "octopus", "meat", "poultry", "seafood",
    "anchovy", "anchovies", "prosciutto", "pepperoni", "salami", "gelatin"
]

OFF_TOPIC_KEYWORDS = [
    "quantum", "cryptocurrency", "bitcoin", "blockchain", "stock market",
    "hack", "bypass", "jailbreak", "write python code to", "sql injection",
    "who won the", "president", "cricket world cup", "write an essay on",
    "movie review", "weather forecast"
]

PROTEIN_SOURCES_VEG = [
    "dal", "lentil", "lentils", "paneer", "tofu", "chickpea", "chickpeas",
    "chole", "rajma", "kidney beans", "soy", "soya", "moong", "urad",
    "chana", "besan", "sprouts", "curd", "yogurt", "milk", "cheese",
    "peanut", "peanuts", "almond", "nuts", "seeds"
]

VEGETABLE_KEYWORDS = [
    "tomato", "onion", "potato", "spinach", "palak", "methi", "carrot",
    "peas", "matar", "capsicum", "bell pepper", "cauliflower", "gobi",
    "cabbage", "patta gobi", "bhindi", "okra", "brinjal", "eggplant",
    "baingan", "cucumber", "gourd", "lauki", "zucchini", "mushroom",
    "beans", "french beans", "beetroot", "ginger", "garlic", "coriander"
]

CARB_KEYWORDS = [
    "rice", "roti", "phulka", "chapati", "paratha", "poha", "upma",
    "khichdi", "oats", "bread", "quinoa", "dosa", "idli", "thepla",
    "noodles", "pasta", "semolina", "suji", "rava"
]


# ==========================================
# 2. Input Guardrails
# ==========================================

def validate_planner_inputs(
    budget: float,
    max_cook_time: int,
    num_days: int = 7,
    reuse_target: float = 30.0,
    diet: str = "Vegetarian"
) -> Tuple[bool, List[str]]:
    """
    Strict application-level guardrails for planner input parameters.
    Prevents negative budgets, invalid cooking times, out-of-range days, etc.
    """
    errors: List[str] = []

    if budget is None or budget <= 0:
        errors.append("Weekly grocery budget must be a positive amount greater than ₹0.")
    elif budget > 50000:
        errors.append("Weekly grocery budget exceeds maximum reasonable limit (₹50,000).")

    if max_cook_time is None or max_cook_time <= 0:
        errors.append("Cooking time limit must be greater than 0 minutes.")
    elif max_cook_time < 10:
        errors.append("Cooking time limit must be at least 10 minutes for realistic meal preparation.")
    elif max_cook_time > 180:
        errors.append("Cooking time limit cannot exceed 180 minutes per meal.")

    if num_days is None or num_days < 1 or num_days > 7:
        errors.append("Planning duration must be between 1 and 7 days.")

    if reuse_target < 0 or reuse_target > 100:
        errors.append("Ingredient reuse target must be between 0% and 100%.")

    if diet.lower() not in ["vegetarian", "vegan", "jain", "eggetarian"]:
        errors.append(f"Problem 14 requires a vegetarian diet. '{diet}' is not a vegetarian category.")

    return len(errors) == 0, errors


def check_off_topic_query(query_text: str) -> Tuple[bool, str]:
    """
    Guardrail to detect queries completely unrelated to meal planning and nutrition.
    Returns (is_off_topic, reason_or_message).
    """
    q_lower = query_text.lower().strip()
    if not q_lower:
        return True, "Query cannot be empty."

    # Direct match for known adversarial/off-topic patterns
    for kw in OFF_TOPIC_KEYWORDS:
        if kw in q_lower:
            return True, "This tool is designed for vegetarian meal planning, grocery planning and cooking constraints."

    return False, ""


def check_non_veg_intent(query_or_request: str) -> Tuple[bool, str]:
    """
    Guardrail to detect adversarial requests to introduce meat or fish into the vegetarian plan.
    """
    q_lower = query_or_request.lower()
    found_items = [kw for kw in NON_VEGETARIAN_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', q_lower)]
    if found_items:
        return True, f"Non-vegetarian item detected ({', '.join(found_items)}). Problem 14 strictly enforces 100% vegetarian meals."
    return False, ""


# ==========================================
# 3. Deterministic Python Constraint Validator
# ==========================================

def validate_meal_plan_constraints(
    plan_data: Dict[str, Any],
    budget_limit: float,
    max_cook_time: int,
    pantry_items: Optional[List[Dict[str, Any]]] = None,
    min_reuse_target: float = 30.0,
    required_days: int = 7,
    allergies: Optional[List[str]] = None,
    dislikes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Authoritative deterministic validation layer in Python.
    Checks:
    1. Vegetarian compliance
    2. Weekly budget
    3. Per-meal cooking-time limit
    4. Ingredient reuse across meals
    5. Pantry utilization
    6. Weekly variety
    7. Nutrition-balance heuristic (general, non-medical)
    8. Required number of days/meals
    9. Missing/invalid fields & format
    """
    violations: List[str] = []
    warnings: List[str] = []

    pantry_items = pantry_items or []
    allergies = [a.lower().strip() for a in (allergies or []) if a.strip()]
    dislikes = [d.lower().strip() for d in (dislikes or []) if d.strip()]

    # --- 1. Schema & Structure Check ---
    format_ok = True
    if not isinstance(plan_data, dict):
        return {
            "valid": False,
            "vegetarian_ok": False,
            "budget_ok": False,
            "cooking_time_ok": False,
            "ingredient_reuse_ok": False,
            "pantry_ok": False,
            "variety_ok": False,
            "nutrition_balance_ok": False,
            "format_ok": False,
            "violations": ["Plan output is not a valid JSON dictionary."],
            "warnings": [],
            "metrics": {}
        }

    days_list = plan_data.get("days", [])
    if not isinstance(days_list, list) or len(days_list) < required_days:
        format_ok = False
        violations.append(f"Required {required_days} days in meal plan, but found {len(days_list) if isinstance(days_list, list) else 0}.")

    # --- 2. Vegetarian & Allergy Compliance ---
    vegetarian_ok = True
    detected_non_veg = []
    detected_allergens = []

    all_meals: List[Dict[str, Any]] = []
    all_meal_names: List[str] = []
    dinner_names: List[str] = []
    all_ingredients: List[str] = []
    ingredient_meal_map: Dict[str, List[str]] = {}

    total_plan_cost = 0.0
    max_observed_cook_time = 0
    cooking_time_exceeded_meals = []

    for d_idx, day_obj in enumerate(days_list):
        day_name = day_obj.get("day", f"Day {d_idx + 1}")
        
        for m_type in ["breakfast", "lunch", "dinner"]:
            meal = day_obj.get(m_type)
            if not isinstance(meal, dict):
                violations.append(f"{day_name} is missing a valid '{m_type}' definition.")
                format_ok = False
                continue

            all_meals.append(meal)
            m_name = str(meal.get("name", "")).strip()
            all_meal_names.append(m_name)
            if m_type == "dinner":
                dinner_names.append(m_name.lower())

            # Cost accumulation
            m_cost = float(meal.get("estimated_cost", 0.0) or 0.0)
            total_plan_cost += m_cost

            # Cook time check
            c_time = int(meal.get("cooking_time_minutes", 0) or 0)
            if c_time > max_observed_cook_time:
                max_observed_cook_time = c_time
            if c_time > max_cook_time:
                cooking_time_exceeded_meals.append(f"{day_name} {m_type.capitalize()} ({m_name}: {c_time}m > {max_cook_time}m)")

            # Ingredients inspection
            raw_ings = meal.get("ingredients", [])
            if isinstance(raw_ings, str):
                raw_ings = [raw_ings]
            
            for ing in raw_ings:
                clean_ing = str(ing).strip().lower()
                if not clean_ing:
                    continue
                all_ingredients.append(clean_ing)
                
                # Ingredient mapping for reuse calculation
                ing_key = _normalize_ingredient_name(clean_ing)
                if ing_key not in ingredient_meal_map:
                    ingredient_meal_map[ing_key] = []
                ingredient_meal_map[ing_key].append(f"{day_name[:3]} {m_type.capitalize()}")

                # Check vegetarian violation
                for nv in NON_VEGETARIAN_KEYWORDS:
                    if re.search(r'\b' + re.escape(nv) + r'\b', clean_ing):
                        detected_non_veg.append(f"{clean_ing} in {day_name} {m_type.capitalize()}")

                # Check allergy violation
                for alg in allergies:
                    if alg in clean_ing:
                        detected_allergens.append(f"{clean_ing} (matches allergy '{alg}') in {day_name} {m_type.capitalize()}")

    if detected_non_veg:
        vegetarian_ok = False
        violations.append(f"Non-vegetarian ingredients detected: {', '.join(set(detected_non_veg))}.")

    if detected_allergens:
        violations.append(f"Allergen violations detected: {', '.join(set(detected_allergens))}.")

    # --- 3. Weekly Budget Check ---
    # Also check if plan has an overarching summary cost or grocery list cost
    summary_cost = float(plan_data.get("summary", {}).get("estimated_total_cost", 0.0) or 0.0)
    effective_cost = summary_cost if summary_cost > 0 else total_plan_cost
    
    budget_ok = effective_cost <= budget_limit
    if not budget_ok:
        excess = effective_cost - budget_limit
        violations.append(f"Weekly grocery budget exceeded: estimated ₹{effective_cost:.2f} exceeds budget limit ₹{budget_limit:.2f} by ₹{excess:.2f}.")

    # --- 4. Cooking Time Limit ---
    cooking_time_ok = len(cooking_time_exceeded_meals) == 0
    if not cooking_time_ok:
        violations.append(f"Cooking time limit ({max_cook_time} mins) exceeded in: {', '.join(cooking_time_exceeded_meals)}.")

    # --- 5. Ingredient Reuse Metric ---
    # Metric formula: Unique ingredients used in >= 2 meals / Total unique ingredients * 100
    unique_ingredients = list(ingredient_meal_map.keys())
    total_unique_ings = len(unique_ingredients)
    reused_ingredients = [k for k, meals in ingredient_meal_map.items() if len(set(meals)) >= 2]
    
    reuse_rate = (len(reused_ingredients) / total_unique_ings * 100) if total_unique_ings > 0 else 0.0
    ingredient_reuse_ok = reuse_rate >= min_reuse_target
    if not ingredient_reuse_ok:
        violations.append(f"Ingredient reuse rate is {reuse_rate:.1f}%, which is below the target minimum of {min_reuse_target:.1f}%.")

    # --- 6. Pantry Utilization ---
    pantry_ok = True
    pantry_names = [p.get("name", "").strip().lower() for p in pantry_items if p.get("name")]
    used_pantry_items = set()
    
    if pantry_names:
        for p_name in pantry_names:
            p_norm = _normalize_ingredient_name(p_name)
            for ing_k in unique_ingredients:
                if p_norm in ing_k or ing_k in p_norm:
                    used_pantry_items.add(p_name)
                    break
        
        pantry_utilization_rate = (len(used_pantry_items) / len(pantry_names) * 100) if pantry_names else 100.0
        if pantry_utilization_rate < 30.0 and len(pantry_names) >= 3:
            warnings.append(f"Pantry utilization is low ({len(used_pantry_items)}/{len(pantry_names)} items used). Prioritizing in-stock items reduces grocery costs.")
    else:
        pantry_utilization_rate = 100.0

    # --- 7. Weekly Variety Constraint ---
    # Rule 1: No identical dinner dishes across the week
    unique_dinners = set(dinner_names)
    dinner_variety_ok = len(unique_dinners) >= max(1, len(dinner_names) - 1)  # allow max 1 repeat if 7 days
    
    # Rule 2: Protein source variety (at least 3 distinct protein sources across week)
    protein_sources_found = set()
    for meal in all_meals:
        p_src = str(meal.get("protein_source", "")).strip().lower()
        if p_src:
            for veg_p in PROTEIN_SOURCES_VEG:
                if veg_p in p_src:
                    protein_sources_found.add(veg_p)
        # Also scan ingredients
        for ing in meal.get("ingredients", []):
            for veg_p in PROTEIN_SOURCES_VEG:
                if veg_p in str(ing).lower():
                    protein_sources_found.add(veg_p)

    protein_variety_ok = len(protein_sources_found) >= 3 if len(all_meals) >= 6 else True

    variety_ok = dinner_variety_ok and protein_variety_ok
    if not dinner_variety_ok:
        violations.append(f"Dinner variety violation: found duplicate dinners across the week ({len(dinner_names) - len(unique_dinners)} duplicates).")
    if not protein_variety_ok:
        warnings.append(f"Low protein variety: only {len(protein_sources_found)} distinct protein sources found ({', '.join(protein_sources_found)}). Recommend adding lentils, paneer, tofu, or sprouts.")

    # --- 8. Non-Medical Nutrition Balance Heuristic ---
    # Checks whether each day includes: (a) a protein source, (b) vegetable components, (c) whole grains/carbs
    daily_balance_checks = []
    days_balanced_count = 0

    for d_idx, day_obj in enumerate(days_list):
        day_name = day_obj.get("day", f"Day {d_idx + 1}")
        day_proteins = set()
        day_veggies = set()
        day_carbs = set()

        for m_type in ["breakfast", "lunch", "dinner"]:
            meal = day_obj.get(m_type, {})
            # Check declared fields or scan ingredients
            p_source = str(meal.get("protein_source", "")).lower()
            if p_source:
                day_proteins.add(p_source)
            for v_comp in meal.get("vegetable_components", []):
                day_veggies.add(str(v_comp).lower())
            carb = str(meal.get("grain_or_carb", "")).lower()
            if carb:
                day_carbs.add(carb)

            # Fallback heuristic scan on ingredients list
            for ing in meal.get("ingredients", []):
                ing_l = str(ing).lower()
                for p in PROTEIN_SOURCES_VEG:
                    if p in ing_l:
                        day_proteins.add(p)
                for v in VEGETABLE_KEYWORDS:
                    if v in ing_l:
                        day_veggies.add(v)
                for c in CARB_KEYWORDS:
                    if c in ing_l:
                        day_carbs.add(c)

        is_balanced = bool(day_proteins) and bool(day_veggies) and bool(day_carbs)
        if is_balanced:
            days_balanced_count += 1
        daily_balance_checks.append({
            "day": day_name,
            "balanced": is_balanced,
            "proteins": list(day_proteins)[:3],
            "veggies": list(day_veggies)[:3],
            "carbs": list(day_carbs)[:3]
        })

    nutrition_balance_ok = (days_balanced_count / len(days_list) >= 0.7) if days_list else False
    if not nutrition_balance_ok:
        warnings.append(f"Nutrition balance check: {len(days_list) - days_balanced_count} days have incomplete combinations of protein, vegetables, and complex carbohydrates.")

    # Overall validity (all hard constraints must pass)
    is_overall_valid = (
        format_ok and
        vegetarian_ok and
        budget_ok and
        cooking_time_ok and
        ingredient_reuse_ok and
        variety_ok and
        len(detected_allergens) == 0
    )

    return {
        "valid": is_overall_valid,
        "vegetarian_ok": vegetarian_ok,
        "budget_ok": budget_ok,
        "cooking_time_ok": cooking_time_ok,
        "ingredient_reuse_ok": ingredient_reuse_ok,
        "pantry_ok": pantry_ok,
        "variety_ok": variety_ok,
        "nutrition_balance_ok": nutrition_balance_ok,
        "format_ok": format_ok,
        "violations": violations,
        "warnings": warnings,
        "metrics": {
            "total_estimated_cost": round(effective_cost, 2),
            "budget_limit": budget_limit,
            "budget_headroom": round(budget_limit - effective_cost, 2),
            "max_cooking_time_observed": max_observed_cook_time,
            "cooking_time_limit": max_cook_time,
            "ingredient_reuse_rate": round(reuse_rate, 1),
            "ingredient_reuse_target": min_reuse_target,
            "unique_ingredients_count": total_unique_ings,
            "reused_ingredients_count": len(reused_ingredients),
            "pantry_utilization_rate": round(pantry_utilization_rate, 1),
            "pantry_items_used": list(used_pantry_items),
            "distinct_dinners_count": len(unique_dinners),
            "protein_sources_count": len(protein_sources_found),
            "days_balanced_count": days_balanced_count,
            "total_days": len(days_list)
        },
        "daily_balance": daily_balance_checks
    }


# ==========================================
# 4. Grocery List Consolidation Engine
# ==========================================

def consolidate_grocery_list(
    days_list: List[Dict[str, Any]],
    pantry_items: Optional[List[Dict[str, Any]]] = None,
    default_cost_per_unit: float = 30.0
) -> Dict[str, Any]:
    """
    Consolidates ingredients across all days and meals.
    Aggregates:
    - Same ingredient
    - Quantities and units
    - Pantry quantity available
    - Net purchase required
    - Meals where used
    - Estimated cost
    """
    pantry_items = pantry_items or []
    pantry_lookup = {}
    for p in pantry_items:
        p_name = _normalize_ingredient_name(p.get("name", ""))
        pantry_lookup[p_name] = {
            "name": p.get("name", ""),
            "quantity": float(p.get("quantity", 0) or 0),
            "unit": str(p.get("unit", "")).strip().lower(),
            "category": p.get("category", "Pantry")
        }

    # Consolidated registry
    registry: Dict[str, Dict[str, Any]] = {}

    for d_idx, day_obj in enumerate(days_list):
        day_name = day_obj.get("day", f"Day {d_idx + 1}")
        
        for m_type in ["breakfast", "lunch", "dinner"]:
            meal = day_obj.get(m_type, {})
            raw_ings = meal.get("ingredients", [])
            if isinstance(raw_ings, str):
                raw_ings = [raw_ings]

            for ing_entry in raw_ings:
                ing_str = str(ing_entry).strip()
                if not ing_str:
                    continue

                parsed_qty, parsed_unit, ing_clean_name = _parse_ingredient_string(ing_str)
                norm_key = _normalize_ingredient_name(ing_clean_name)
                
                meal_tag = f"{day_name[:3]} {m_type.capitalize()}"

                if norm_key not in registry:
                    # Check pantry match
                    pantry_match = pantry_lookup.get(norm_key, None)
                    pantry_avail = pantry_match["quantity"] if pantry_match else 0.0
                    pantry_unit = pantry_match["unit"] if pantry_match else parsed_unit

                    registry[norm_key] = {
                        "name": ing_clean_name.capitalize(),
                        "norm_key": norm_key,
                        "required_qty": 0.0,
                        "unit": parsed_unit or pantry_unit or "items",
                        "pantry_available": pantry_avail,
                        "used_in_meals": [],
                        "category": pantry_match["category"] if pantry_match else _guess_category(ing_clean_name)
                    }

                reg_item = registry[norm_key]
                reg_item["required_qty"] += parsed_qty
                if meal_tag not in reg_item["used_in_meals"]:
                    reg_item["used_in_meals"].append(meal_tag)

    # Calculate net quantities to buy and costs
    pantry_used_list = []
    to_buy_list = []
    total_grocery_cost = 0.0

    for norm_key, item in registry.items():
        req_qty = round(item["required_qty"], 2)
        pantry_qty = round(item["pantry_available"], 2)
        need_to_buy = max(0.0, round(req_qty - pantry_qty, 2))
        
        # Estimate item cost
        unit_price = _estimate_unit_cost(item["name"], item["unit"])
        estimated_item_cost = round(need_to_buy * unit_price, 2)
        total_grocery_cost += estimated_item_cost

        item_record = {
            "name": item["name"],
            "required_qty": req_qty,
            "unit": item["unit"],
            "pantry_available": pantry_qty,
            "need_to_buy": need_to_buy,
            "estimated_cost": estimated_item_cost,
            "used_in_meals": item["used_in_meals"],
            "usage_count": len(item["used_in_meals"]),
            "category": item["category"]
        }

        if pantry_qty > 0:
            pantry_used_list.append(item_record)
        
        if need_to_buy > 0:
            to_buy_list.append(item_record)

    # Sort items by usage count descending
    to_buy_list.sort(key=lambda x: x["usage_count"], reverse=True)
    pantry_used_list.sort(key=lambda x: x["usage_count"], reverse=True)

    return {
        "pantry_items_used": pantry_used_list,
        "items_to_buy": to_buy_list,
        "total_items_to_buy": len(to_buy_list),
        "total_pantry_items_used": len(pantry_used_list),
        "estimated_total_grocery_cost": round(total_grocery_cost, 2)
    }


# ==========================================
# 5. Helper Utilities for Parsing & Normalization
# ==========================================

def _normalize_ingredient_name(name: str) -> str:
    """Normalize ingredient name for matching (e.g., 'Chopped Red Tomatoes' -> 'tomato')."""
    clean = name.lower().strip()
    clean = re.sub(r'\(.*?\)', '', clean)  # remove parentheses
    clean = re.sub(r'[\d\./\\]+', '', clean)  # remove numbers
    
    # Common descriptors to strip
    descriptors = [
        "fresh", "chopped", "diced", "sliced", "grated", "boiled", "cooked",
        "raw", "organic", "large", "small", "medium", "finely", "roughly",
        "red", "green", "yellow", "white", "black", "pureed", "crushed"
    ]
    words = clean.split()
    filtered_words = [w for w in words if w not in descriptors]
    result = " ".join(filtered_words).strip()
    
    # Simple singularization
    if result.endswith("toes"):
        result = result[:-2]  # tomatoes -> tomato
    elif result.endswith("ies"):
        result = result[:-3] + "y"
    elif result.endswith("s") and not result.endswith("ss") and len(result) > 3:
        result = result[:-1]

    return result if result else clean


def _parse_ingredient_string(ing_str: str) -> Tuple[float, str, str]:
    """
    Extract quantity, unit, and ingredient name from strings like:
    '200 g Paneer', '2 cups Basmati Rice', '4 pieces Tomato', 'Salt to taste'
    """
    clean = ing_str.strip()
    # Pattern for number + unit + name
    pattern = r'^([\d\.\/]+)\s*([a-zA-Z]+)?\s+(.*)$'
    match = re.match(pattern, clean)

    if match:
        qty_str, unit_cand, name_cand = match.groups()
        try:
            if "/" in qty_str:
                num, denom = qty_str.split("/")
                qty = float(num) / float(denom)
            else:
                qty = float(qty_str)
        except ValueError:
            qty = 1.0

        unit = unit_cand.lower() if unit_cand else "pieces"
        recognized_units = ["g", "kg", "ml", "l", "litre", "cup", "cups", "tbsp", "tsp", "piece", "pieces", "bunch", "pack", "clove", "cloves", "pinch"]
        if unit in recognized_units:
            norm_unit = "pieces" if unit in ["piece", "pieces"] else unit
            return qty, norm_unit, name_cand.strip()
        else:
            return qty, "pieces", f"{unit_cand} {name_cand}".strip()

    return 1.0, "pieces", clean


def _guess_category(name: str) -> str:
    """Guess grocery category for UI presentation."""
    name_l = name.lower()
    for v in VEGETABLE_KEYWORDS:
        if v in name_l:
            return "Vegetables"
    for p in ["paneer", "curd", "milk", "cheese", "butter", "ghee"]:
        if p in name_l:
            return "Dairy"
    for d in ["dal", "lentil", "tofu", "chickpea", "rajma", "soya", "sprouts"]:
        if d in name_l:
            return "Protein / Legumes"
    for g in CARB_KEYWORDS:
        if g in name_l:
            return "Grains"
    for s in ["masala", "turmeric", "cumin", "chili", "mustard", "salt", "pepper", "oil"]:
        if s in name_l:
            return "Spices & Oils"
    return "Pantry"


def _estimate_unit_cost(name: str, unit: str) -> float:
    """Provides sensible heuristic unit prices in INR for grocery estimation."""
    name_l = name.lower()
    unit_l = unit.lower()

    if "paneer" in name_l or "tofu" in name_l:
        return 0.4 if "g" in unit_l else 80.0
    elif "dal" in name_l or "lentil" in name_l or "rajma" in name_l or "chole" in name_l:
        return 0.15 if "g" in unit_l else 40.0
    elif "rice" in name_l or "flour" in name_l or "atta" in name_l:
        return 0.06 if "g" in unit_l else 25.0
    elif "tomato" in name_l or "onion" in name_l or "potato" in name_l:
        return 8.0 if "piece" in unit_l else 30.0
    elif "oil" in name_l or "ghee" in name_l:
        return 0.3 if "ml" in unit_l else 40.0
    else:
        return 15.0 if "piece" in unit_l else 20.0
