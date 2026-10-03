"""
NutriGen AI - Prompt Builder Utilities
Constructs structured context-aware prompts for Google Gemini GenAI inference,
including conversational Q&A, meal planning, recipe generation, and modifications.
"""

from typing import Dict, Any, List, Optional
from utils.helpers import get_ingredient_context_summary


def build_simple_prompt(user_question: str) -> str:
    """Construct a basic NutriGen AI prompt without extended context."""
    return f"""You are NutriGen AI, a helpful, polite, and practical personal nutrition and meal planning assistant.

Answer the user's question clearly, concisely, and accurately.

User Question:
{user_question}
"""


def build_assistant_prompt(
    user_question: str,
    user_profile: Optional[Dict[str, Any]] = None,
    fridge_items: Optional[List[Dict[str, Any]]] = None,
    current_meal_plan: Optional[str] = None,
    current_recipe: Optional[str] = None
) -> str:
    """
    Construct a comprehensive context-aware prompt for the NutriGen AI Assistant (Phase 8).
    Injects user profile, available fridge ingredients, generated meal plan, and active recipe.
    Enforces strict safety, dietary compliance, and practical formatting.
    """
    prof = user_profile or {}
    name = prof.get("name", "User")
    diet = prof.get("dietary_preference", "Vegetarian")
    cuisine = prof.get("cuisine_preference", "Indian")
    budget = prof.get("weekly_budget", 500)
    people = prof.get("number_of_people", 1)
    max_cook_time = prof.get("maximum_cooking_time", 30)
    skill = prof.get("cooking_skill", "Intermediate")
    
    allergies = prof.get("allergies", [])
    allergies_str = ", ".join(allergies) if isinstance(allergies, list) and allergies else "None"
    
    avoids = prof.get("foods_to_avoid", [])
    avoids_str = ", ".join(avoids) if isinstance(avoids, list) and avoids else "None"

    # Fridge Context
    if fridge_items and len(fridge_items) > 0:
        fridge_text = get_ingredient_context_summary(fridge_items)
    else:
        fridge_text = "No ingredients currently in fridge."

    # Meal Plan Context
    meal_plan_text = current_meal_plan.strip() if current_meal_plan and current_meal_plan.strip() else "No meal plan has been generated yet."

    # Recipe Context
    recipe_text = current_recipe.strip() if current_recipe and current_recipe.strip() else "No recipe has been generated yet."

    prompt = f"""You are NutriGen AI, a helpful personal meal-planning and cooking assistant.

Answer the user's question using the available user context.

USER QUESTION:
{user_question}

USER PROFILE:
- Name: {name}
- Dietary Preference: {diet}
- Cuisine Preference: {cuisine}
- Weekly Budget: ₹{budget} (for {people} person{'s' if people > 1 else ''})
- Maximum Cooking Time: {max_cook_time} minutes
- Cooking Skill: {skill}
- Allergies: {allergies_str}
- Foods to Avoid: {avoids_str}

AVAILABLE FRIDGE INGREDIENTS:
{fridge_text}

CURRENT MEAL PLAN:
{meal_plan_text}

CURRENT RECIPE:
{recipe_text}

IMPORTANT RULES:
1. Respect the user's dietary preference ({diet}).
2. Never intentionally recommend known allergens ({allergies_str}).
3. Avoid foods the user has explicitly asked to avoid ({avoids_str}).
4. Prefer available fridge ingredients when relevant to minimize waste.
5. Consider the user's cooking time ({max_cook_time} mins) and skill level ({skill}).
6. Consider the user's budget (₹{budget}) when giving meal suggestions.
7. Give practical, encouraging, and easy-to-understand answers formatted in clean Markdown.
8. Do not invent information about the user's fridge or profile.
9. If information is unavailable, say so clearly.
10. You are an AI assistant and your nutrition estimates or recommendations are approximate; encourage professional advice for medical or serious dietary concerns.
"""
    return prompt.strip()


def build_nutrigen_prompt(
    user_question: str,
    user_profile: Optional[Dict[str, Any]] = None,
    fridge_items: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Backward-compatible wrapper for conversational assistance.
    Calls build_assistant_prompt with user_profile and fridge_items.
    """
    return build_assistant_prompt(
        user_question=user_question,
        user_profile=user_profile,
        fridge_items=fridge_items
    )



def build_meal_plan_prompt(
    user_profile: Optional[Dict[str, Any]],
    fridge_items: Optional[List[Dict[str, Any]]],
    num_days: int = 7,
    meal_types: Optional[List[str]] = None,
    target_budget: Optional[float] = None
) -> str:
    """
    Construct a structured prompt for Google Gemini to generate a personalized meal plan.
    Enforces allergy exclusions, fridge ingredient prioritization, budget limits, and time constraints.
    """
    meal_types_str = ", ".join(meal_types) if meal_types else "Breakfast, Lunch, Dinner"
    
    prof = user_profile or {}
    diet = prof.get("dietary_preference", "Vegetarian")
    cuisine = prof.get("cuisine_preference", "Indian")
    budget = target_budget if target_budget is not None else prof.get("weekly_budget", 500)
    people = prof.get("number_of_people", 1)
    max_cook_time = prof.get("maximum_cooking_time", 30)
    skill = prof.get("cooking_skill", "Intermediate")
    
    allergies = prof.get("allergies", [])
    allergies_str = ", ".join(allergies) if isinstance(allergies, list) and allergies else "None"
    
    avoids = prof.get("foods_to_avoid", [])
    avoids_str = ", ".join(avoids) if isinstance(avoids, list) and avoids else "None"

    if fridge_items and len(fridge_items) > 0:
        fridge_text = get_ingredient_context_summary(fridge_items)
        fridge_instructions = f"""--- AVAILABLE INGREDIENTS IN FRIDGE ---
{fridge_text}

PRIORITY RULE: Prefer and prioritize utilizing the ingredients listed above that are already available in the user's fridge to reduce food waste and save costs."""
    else:
        fridge_instructions = """--- AVAILABLE INGREDIENTS IN FRIDGE ---
No ingredients are currently available in the fridge. Suggest meals using commonly available, budget-friendly pantry staples."""

    prompt = f"""You are NutriGen AI, an expert personal nutrition and meal planning assistant.

Create a personalized {num_days}-day meal plan tailored specifically to the user's dietary preferences, cooking time constraints, budget, and available ingredients.

--- USER REQUIREMENTS & CONSTRAINTS ---
- Dietary Preference: {diet}
- Cuisine Style: {cuisine}
- Target Budget: Approximately ₹{budget} (for {people} person{'s' if people > 1 else ''})
- Maximum Cooking Time per Meal: {max_cook_time} minutes
- Cooking Skill Level: {skill}
- Meals to Include per Day: {meal_types_str}
- STRICT ALLERGIES / RESTRICTIONS: {allergies_str}
- FOODS TO AVOID / DISLIKES: {avoids_str}

{fridge_instructions}

--- CRITICAL RULES ---
1. STRICT ALLERGEN SAFETY: Never intentionally include ingredients listed under allergies ({allergies_str}) or foods to avoid ({avoids_str}).
2. COOKING TIME LIMIT: Ensure all proposed meals can realistically be cooked within {max_cook_time} minutes.
3. BUDGET CONSCIOUS: Keep meals affordable and aligned with the target budget of ~₹{budget}. Provide an approximate estimated total cost at the end.
4. STRUCTURED FORMAT:
   - For each of the {num_days} days (Day 1 through Day {num_days}, with day names like Monday, Tuesday, etc.), list each requested meal type ({meal_types_str}) with a concise meal name, main ingredients, and quick cooking tip or estimated time.
   - At the end, include a short "💰 Approximate Estimated Cost" section and a "🛒 Quick Pantry Shopping List" for items needed beyond the current fridge inventory.

Format the entire output in clean, readable GitHub Flavored Markdown with emojis and bold headers.
"""
    return prompt.strip()


def build_modify_meal_plan_prompt(
    current_meal_plan: str,
    user_request: str,
    user_profile: Optional[Dict[str, Any]] = None,
    fridge_items: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Construct a prompt to modify an existing AI-generated meal plan based on a natural language request.
    """
    prof = user_profile or {}
    diet = prof.get("dietary_preference", "Vegetarian")
    allergies = prof.get("allergies", [])
    allergies_str = ", ".join(allergies) if isinstance(allergies, list) and allergies else "None"
    
    fridge_text = get_ingredient_context_summary(fridge_items) if fridge_items else "Common pantry staples"

    prompt = f"""You are NutriGen AI, an expert meal planning assistant.

Here is the user's CURRENT meal plan:
--- CURRENT MEAL PLAN ---
{current_meal_plan}

--- USER REQUESTED MODIFICATION ---
The user wants to apply this specific change:
"{user_request}"

--- CONSTRAINTS TO MAINTAIN ---
- Dietary Style: {diet}
- Strict Allergies: {allergies_str} (Never include these!)
- Available Fridge Stock: {fridge_text}

--- INSTRUCTIONS ---
Modify the current meal plan to incorporate the user's requested changes while strictly preserving the dietary constraints and allergy safety.
Return the complete, updated meal plan in clean, structured markdown format.
"""
    return prompt.strip()


def build_recipe_prompt(
    meal_name: str,
    user_profile: Optional[Dict[str, Any]] = None,
    fridge_items: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Construct a structured prompt for Google Gemini to generate a detailed, personalized recipe
    for a specific meal, adhering to allergies, time limits, and prioritizing fridge ingredients.
    """
    prof = user_profile or {}
    diet = prof.get("dietary_preference", "Vegetarian")
    cuisine = prof.get("cuisine_preference", "Indian")
    max_cook_time = prof.get("maximum_cooking_time", 30)
    skill = prof.get("cooking_skill", "Beginner")
    people = prof.get("number_of_people", 2)
    
    allergies = prof.get("allergies", [])
    allergies_str = ", ".join(allergies) if isinstance(allergies, list) and allergies else "None"
    
    avoids = prof.get("foods_to_avoid", [])
    avoids_str = ", ".join(avoids) if isinstance(avoids, list) and avoids else "None"

    if fridge_items and len(fridge_items) > 0:
        fridge_text = get_ingredient_context_summary(fridge_items)
        fridge_note = f"""--- AVAILABLE INGREDIENTS IN FRIDGE ---
{fridge_text}

PRIORITY INSTRUCTION: Prioritize and prefer utilizing the ingredients already available in the user's fridge where appropriate for this recipe."""
    else:
        fridge_note = """--- AVAILABLE INGREDIENTS IN FRIDGE ---
No ingredients currently in fridge. Use common, easy-to-find ingredients."""

    prompt = f"""You are NutriGen AI, an expert culinary and nutrition assistant.

Generate a detailed, delicious, and easy-to-follow recipe for:
🍳 **{meal_name}**

--- USER PROFILE & CONSTRAINTS ---
- Dietary Style: {diet}
- Cuisine Preference: {cuisine}
- Maximum Total Cooking Time: {max_cook_time} minutes
- Cooking Skill Level: {skill}
- Servings: {people} person{'s' if people > 1 else ''}
- STRICT ALLERGIES / RESTRICTIONS: {allergies_str}
- FOODS TO AVOID / DISLIKES: {avoids_str}

{fridge_note}

--- CRITICAL RULES ---
1. STRICT ALLERGY SAFETY: Never intentionally include an ingredient listed under allergies ({allergies_str}) or foods to avoid ({avoids_str}).
2. TIME CONSTRAINTS: Ensure total preparation + cooking time fits comfortably within {max_cook_time} minutes.
3. CLEAR FORMAT: Provide:
   - ⏱️ Preparation Time, 🔥 Cooking Time, and 📊 Difficulty Level (aligned with {skill} skill).
   - 🥕 Ingredients List with exact quantities/measurements (proportioned for {people} serving{'s' if people > 1 else ''}).
   - 👩‍🍳 Step-by-Step Cooking Instructions (numbered, concise, and clear).
   - 🍽️ Serving Suggestion & Quick Chef's Pro-Tip.
   - ⚡ Approximate Nutritional Estimate (Calories and Protein per serving).

Format the output in clean, readable GitHub Flavored Markdown with bold headers and emojis.
"""
    return prompt.strip()


def build_modify_recipe_prompt(
    current_recipe: str,
    user_request: str,
    user_profile: Optional[Dict[str, Any]] = None,
    fridge_items: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Construct a prompt to modify an existing AI-generated recipe based on natural language feedback.
    """
    prof = user_profile or {}
    diet = prof.get("dietary_preference", "Vegetarian")
    allergies = prof.get("allergies", [])
    allergies_str = ", ".join(allergies) if isinstance(allergies, list) and allergies else "None"
    
    fridge_text = get_ingredient_context_summary(fridge_items) if fridge_items else "Common staples"

    prompt = f"""You are NutriGen AI, an expert culinary assistant.

Here is the user's CURRENT recipe:
--- CURRENT RECIPE ---
{current_recipe}

--- USER REQUESTED MODIFICATION ---
"{user_request}"

--- CONSTRAINTS TO MAINTAIN ---
- Dietary Style: {diet}
- Strict Allergies: {allergies_str} (Never include these!)
- Available Fridge Stock: {fridge_text}

--- INSTRUCTIONS ---
Modify the recipe to fulfill the user's request while strictly respecting dietary preferences and allergy constraints.
Return the complete, modified recipe in clean, structured markdown format.
"""
    return prompt.strip()


def build_substitution_prompt(
    ingredient_to_replace: str,
    reason_or_request: Optional[str] = "",
    current_recipe: Optional[str] = None,
    user_profile: Optional[Dict[str, Any]] = None,
    fridge_items: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Construct a structured prompt for Google Gemini to suggest practical, dietary-safe ingredient substitutions.
    Prioritizes available fridge stock, strictly excludes allergens and avoided foods, and provides clear culinary guidance.
    """
    prof = user_profile or {}
    diet = prof.get("dietary_preference", "Vegetarian")
    cuisine = prof.get("cuisine_preference", "Indian")
    max_cook_time = prof.get("maximum_cooking_time", 30)
    skill = prof.get("cooking_skill", "Beginner")
    
    allergies = prof.get("allergies", [])
    allergies_str = ", ".join(allergies) if isinstance(allergies, list) and allergies else "None"
    
    avoids = prof.get("foods_to_avoid", [])
    avoids_str = ", ".join(avoids) if isinstance(avoids, list) and avoids else "None"

    recipe_context = ""
    if current_recipe and current_recipe.strip():
        recipe_context = f"""--- CURRENT RECIPE CONTEXT ---
{current_recipe.strip()}
"""

    fridge_text = get_ingredient_context_summary(fridge_items) if fridge_items else "No ingredients currently in fridge"
    reason_context = f"\nUser Goal / Reason: {reason_or_request.strip()}" if reason_or_request and reason_or_request.strip() else ""

    prompt = f"""You are NutriGen AI, a helpful personal cooking and nutrition assistant.

The user wants to replace this ingredient:
--- INGREDIENT TO REPLACE ---
Ingredient: {ingredient_to_replace}{reason_context}

{recipe_context}--- USER PREFERENCES & CONSTRAINTS ---
- Dietary Preference: {diet}
- Cuisine Style: {cuisine}
- Cooking Skill Level: {skill}
- Maximum Cooking Time: {max_cook_time} minutes
- STRICT ALLERGIES / RESTRICTIONS: {allergies_str}
- FOODS TO AVOID / DISLIKES: {avoids_str}

--- AVAILABLE FRIDGE INGREDIENTS ---
{fridge_text}

PRIORITY INSTRUCTION:
Where practical, prefer suggesting ingredients already available in the user's fridge to reduce food waste and avoid new grocery shopping.

--- CRITICAL ALLERGY SAFETY INSTRUCTIONS ---
1. STRICT ALLERGEN SAFETY: Never intentionally suggest an ingredient that conflicts with the user's allergies ({allergies_str}) or foods to avoid ({avoids_str}).
2. DIETARY COMPLIANCE: Strictly adhere to the user's {diet} dietary preference.
3. PRACTICAL RATIOS: Suggest 2–4 practical replacements with approximate replacement quantities, texture/flavor profile, and cooking adjustments.

--- REQUIRED OUTPUT FORMAT ---
Please format the response in clean, readable Markdown:

### 🔄 AI Ingredient Substitution for **{ingredient_to_replace}**

#### 📋 Suggested Alternatives (2–4 options)
1. **[Substitute 1]** *(noting if in fridge stock)*: [Why it works, texture/flavor comparison, replacement ratio]
2. **[Substitute 2]**: [Details & replacement ratio]
3. **[Substitute 3]**: [Details & replacement ratio]

#### 🌟 Recommended Option
**[Top Recommended Substitute]** — [How to prepare, proportion, and cook it in this context]

#### 💡 Culinary & Safety Note
[Brief note confirming allergy compliance and cooking tips]
"""
    return prompt.strip()


# ==========================================
# Phase 10 & 11: Constraint-Based Prompt Engineering
# Hackathon Problem 14: Constraint-Based Meal Planner
# ==========================================

SYSTEM_PROMPT_CONSTRAINT_PLANNER = """You are a constraint-aware vegetarian weekly meal planning assistant.
Your mission is to synthesize a feasible, cost-effective, time-limited, and nutritionally varied weekly vegetarian meal plan that strictly satisfies all hard numerical and dietary constraints."""


def build_meal_plan_prompt_v1(
    user_profile: Optional[Dict[str, Any]] = None,
    budget: float = 500.0,
    max_cook_time: int = 30,
    num_days: int = 7
) -> str:
    """
    PROMPT V1 (First / Baseline Prompt Version):
    A basic, unconstrained prompt without schema enforcement, self-critique,
    or explicit numerical constraint tracking. Used for Hackathon side-by-side comparison.
    """
    prof = user_profile or {}
    diet = prof.get("dietary_preference", "Vegetarian")
    cuisine = prof.get("cuisine_preference", "Indian")
    
    return f"""Create a {num_days}-day {diet} meal plan for {cuisine} cuisine.
Weekly Budget: ₹{budget}
Cooking time per meal: {max_cook_time} mins.
Give me breakfast, lunch, and dinner for each day and a grocery list at the end with costs.
"""


def build_constraint_meal_plan_prompt_final(
    user_profile: Optional[Dict[str, Any]],
    pantry_items: Optional[List[Dict[str, Any]]],
    budget: float = 500.0,
    max_cook_time: int = 30,
    num_days: int = 7,
    reuse_target: float = 40.0,
    variety_level: str = "High",
    servings: int = 2,
    cuisine: Optional[str] = None
) -> str:
    """
    FINAL SYSTEM PROMPT (Technique 1 & 2):
    Implements all 12 required sections:
    1. ROLE
    2. USER CONSTRAINTS
    3. PANTRY
    4. HARD CONSTRAINTS
    5. SOFT PREFERENCES
    6. INGREDIENT REUSE RULES
    7. VARIETY RULES
    8. GENERAL NUTRITION BALANCE
    9. OUTPUT SCHEMA
    10. SELF-CHECK
    11. REPAIR BEHAVIOR
    12. SAFETY / NON-MEDICAL DISCLAIMER
    """
    prof = user_profile or {}
    diet = prof.get("dietary_preference", "Vegetarian")
    active_cuisine = cuisine or prof.get("cuisine_preference", "Indian")
    people = servings or prof.get("number_of_people", 2)
    
    allergies = prof.get("allergies", [])
    allergies_str = ", ".join(allergies) if isinstance(allergies, list) and allergies else "None"
    
    avoids = prof.get("foods_to_avoid", [])
    avoids_str = ", ".join(avoids) if isinstance(avoids, list) and avoids else "None"

    # Pantry formatting
    if pantry_items and len(pantry_items) > 0:
        pantry_lines = []
        for p in pantry_items:
            pantry_lines.append(f"- {p.get('name')}: {p.get('quantity')} {p.get('unit')} (Category: {p.get('category', 'Pantry')})")
        pantry_text = "\n".join(pantry_lines)
    else:
        pantry_text = "No in-stock pantry items available. All ingredients must be purchased as new groceries."

    prompt = f"""=== 1. ROLE ===
{SYSTEM_PROMPT_CONSTRAINT_PLANNER}

=== 2. USER CONSTRAINTS ===
- Number of Days: {num_days} days (Every single day from Day 1 to Day {num_days} with breakfast, lunch, and dinner)
- Number of Servings: {people} person{'s' if people > 1 else ''}
- Weekly Grocery Budget Limit: ₹{budget} (Total cost for all meals across the entire week must be <= ₹{budget})
- Maximum Cooking Time per Meal: {max_cook_time} minutes (Every single meal must take <= {max_cook_time} minutes)
- Minimum Ingredient Reuse Target: {reuse_target}% of key ingredients reused across 2 or more meals
- Weekly Variety Requirement: {variety_level}
- Target Cuisine: {active_cuisine}

=== 3. PANTRY INVENTORY ===
Available ingredients currently in user's pantry/fridge:
{pantry_text}

PRIORITY RULE: Prioritize incorporating the pantry ingredients above to prevent food waste and reduce grocery shopping cost!

=== 4. HARD CONSTRAINTS (MANDATORY ZERO-TOLERANCE) ===
1. STRICT VEGETARIAN ONLY: NEVER include any meat, poultry, fish, seafood, gelatin, or animal flesh.
2. STRICT ALLERGEN EXCLUSION: NEVER include any ingredients matching: {allergies_str}.
3. STRICT FOOD DISLIKES: NEVER include any foods listed in: {avoids_str}.
4. STRICT BUDGET LIMIT: The sum of estimated costs across all days MUST NOT EXCEED ₹{budget}.
5. STRICT COOKING TIME: No meal preparation + cooking time may exceed {max_cook_time} minutes.
6. DURATION: Must contain exactly {num_days} days.

=== 5. SOFT PREFERENCES ===
- Prefer authentic {active_cuisine} culinary traditions.
- Aim for appetizing, comforting meals suited for home cooking.

=== 6. INGREDIENT REUSE RULES ===
- Intentionally reuse versatile ingredients (e.g. Tomatoes, Onions, Rice, Lentils, Paneer/Tofu) across multiple meals.
- Target at least {reuse_target}% of unique ingredients being reused in 2 or more distinct meals across the week.
- This creates batch efficiency and lowers total grocery expenditure.

=== 7. VARIETY RULES ===
- No identical main dishes repeated across the week (especially for dinners).
- Provide diverse vegetable combinations across consecutive days.
- Incorporate multiple protein sources across the week (e.g. Yellow Dal, Chickpeas, Paneer/Tofu, Curd, Sprouts).

=== 8. GENERAL NUTRITION BALANCE (NON-MEDICAL) ===
- Each day should include a discernible protein source, vegetable component, and complex carbohydrate/grain.
- Do not claim clinical or medical nutrition advice. Label all nutrition indicators as general non-medical checks.

=== 9. OUTPUT SCHEMA ===
You MUST return ONLY a valid, parseable JSON object matching this EXACT schema (no introductory text, no markdown backticks, raw JSON only):

{{
  "summary": {{
    "title": "{num_days}-Day Vegetarian Constraint-Based Plan",
    "estimated_total_cost": 0.0,
    "budget_limit": {budget},
    "budget_status": "Within budget",
    "ingredient_reuse_rate_pct": 0.0,
    "pantry_utilization_pct": 0.0,
    "days_count": {num_days}
  }},
  "days": [
    {{
      "day": "Monday",
      "breakfast": {{
        "name": "Meal Name",
        "ingredients": ["Quantity Unit Ingredient"],
        "estimated_cost": 0.0,
        "cooking_time_minutes": 0,
        "protein_source": "Name of protein source",
        "vegetable_components": ["Veggie 1"],
        "grain_or_carb": "Grain name"
      }},
      "lunch": {{
        "name": "Meal Name",
        "ingredients": ["Quantity Unit Ingredient"],
        "estimated_cost": 0.0,
        "cooking_time_minutes": 0,
        "protein_source": "Name of protein source",
        "vegetable_components": ["Veggie 1"],
        "grain_or_carb": "Grain name"
      }},
      "dinner": {{
        "name": "Meal Name",
        "ingredients": ["Quantity Unit Ingredient"],
        "estimated_cost": 0.0,
        "cooking_time_minutes": 0,
        "protein_source": "Name of protein source",
        "vegetable_components": ["Veggie 1"],
        "grain_or_carb": "Grain name"
      }},
      "daily_cost": 0.0,
      "daily_cooking_time": 0,
      "ingredients_used": ["Item 1", "Item 2"],
      "new_ingredients": ["Item to buy"]
    }}
  ],
  "grocery_list": [
    {{
      "ingredient": "Tomato",
      "required_qty": "1.5 kg",
      "pantry_qty": "0.5 kg",
      "need_to_buy": "1.0 kg",
      "estimated_cost": 30.0,
      "used_in_days": ["Monday", "Wednesday"]
    }}
  ],
  "constraint_report": {{
    "vegetarian_verified": true,
    "budget_adhered": true,
    "cooking_time_limit_respected": true,
    "ingredient_reuse_applied": true,
    "variety_ensured": true
  }},
  "nutrition_balance": {{
    "daily_protein_verified": true,
    "daily_vegetables_verified": true,
    "whole_grains_included": true,
    "disclaimer": "General nutrition balance — informational only, not medical advice."
  }},
  "self_check": {{
    "all_meals_strictly_vegetarian": true,
    "highest_cooking_time_minutes": 0,
    "calculated_total_cost": 0.0,
    "budget_check_passed": true,
    "reused_staples": ["List of reused staples"],
    "check_notes": "Self-validation notes"
  }}
}}

=== 10. SELF-CHECK (TECHNIQUE 2) ===
Before producing the final JSON output:
1. Sum all meal estimated costs: is it <= ₹{budget}? If not, replace premium ingredients with budget staples (lentils, potatoes, rice).
2. Check cooking times: does ANY meal exceed {max_cook_time} minutes? If so, simplify the recipe.
3. Check ingredient overlap: ensure staples are intentionally reused across at least 2 days.
4. Record your verification inside the "self_check" JSON block.

=== 11. REPAIR BEHAVIOR ===
If any constraint is in conflict, prioritize hard constraints (Vegetarian > Budget > Cook Time > Allergies) above all else.

=== 12. SAFETY / NON-MEDICAL DISCLAIMER ===
All costs and times are realistic approximations for student and home kitchen planning. Not medical nutrition therapy.
"""
    return prompt.strip()


def build_constraint_repair_prompt(
    candidate_json_str: str,
    violations: List[str],
    budget: float,
    max_cook_time: int
) -> str:
    """
    PROMPT CHAINING REPAIR STEP (Technique 1):
    Feeds back the candidate plan and exact deterministic Python validation failures
    to Google Gemini for targeted surgical repair.
    """
    violations_formatted = "\n".join([f"- {v}" for v in violations])

    return f"""You are a constraint-aware vegetarian meal planning assistant executing a targeted REPAIR step.

Your previously generated meal plan FAILED our automated deterministic constraint validator with the following specific violations:

=== DETECTED CONSTRAINT VIOLATIONS ===
{violations_formatted}

=== REPAIR INSTRUCTIONS ===
1. Analyze each violation carefully.
2. If budget was exceeded: reduce meal estimated costs by swapping expensive ingredients for economical vegetarian staples (dal, potato, seasonal vegetables, rice). Ensure total cost <= ₹{budget}.
3. If cooking time was exceeded: simplify the specific meals flagged above so preparation + cooking takes <= {max_cook_time} minutes.
4. If ingredient reuse was low: deliberately reuse key pantry/staple ingredients across multiple meals.
5. If vegetarian or allergy rules were breached: immediately remove and replace the offending item.
6. Preserve the valid parts of the plan; fix only the violated items.
7. Return ONLY the repaired JSON object conforming to the required schema, with NO markdown backticks and NO commentary.

=== CANDIDATE PLAN TO REPAIR ===
{candidate_json_str}
"""


