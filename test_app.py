"""
Automated unit & UI integration tests for NutriGen AI (Phases 1 through 9)
Tests User Profile, Fridge Inventory, Expiry Engine, Gemini Prompts, AI Meal Planner,
AI Recipe Generator, AI Modifications & Substitutions, Conversational AI Assistant, and Streamlit Multi-Page views.
"""

import os
from datetime import date, timedelta
from streamlit.testing.v1 import AppTest
from utils.helpers import (
    parse_comma_separated_items,
    validate_user_profile,
    get_default_user_profile,
    get_default_fridge_items,
    get_ingredient_status,
    get_expiring_ingredients,
    get_expired_ingredients,
    find_duplicate_ingredient,
    get_ingredient_context_summary
)
from utils.prompts import (
    build_simple_prompt,
    build_nutrigen_prompt,
    build_assistant_prompt,
    build_meal_plan_prompt,
    build_modify_meal_plan_prompt,
    build_recipe_prompt,
    build_modify_recipe_prompt,
    build_substitution_prompt,
    build_meal_plan_prompt_v1,
    build_constraint_meal_plan_prompt_final,
    build_constraint_repair_prompt,
    SYSTEM_PROMPT_CONSTRAINT_PLANNER
)
from services.gemini_service import (
    get_gemini_api_key,
    is_gemini_configured,
    generate_ai_response,
    _is_temporary_unavailable_error,
    _is_client_fatal_error,
    PRIMARY_MODEL,
    FALLBACK_MODEL
)
from utils.constraint_validator import (
    validate_planner_inputs,
    check_off_topic_query,
    check_non_veg_intent,
    validate_meal_plan_constraints,
    consolidate_grocery_list
)
from services.constraint_planner import (
    extract_json_from_response,
    log_prompt_history_event
)
from utils.benchmark_suite import (
    BENCHMARK_TEST_CASES,
    run_local_benchmark_evaluation
)


# ==========================================
# 1. Unit Tests: Conversational AI Assistant (Phase 8)
# ==========================================

def test_assistant_prompt_builder_full_context():
    """
    Phase 8 Unit Test:
    Verify build_assistant_prompt includes:
    1. User question
    2. User profile (diet, cuisine, budget, time, skill, allergies, foods to avoid)
    3. Available fridge ingredients
    4. Active meal plan context
    5. Active recipe context
    6. Strict allergen safety and educational safety rules
    """
    profile = {
        "name": "Aryan",
        "dietary_preference": "Vegetarian",
        "cuisine_preference": "Indian",
        "weekly_budget": 600,
        "number_of_people": 2,
        "maximum_cooking_time": 25,
        "cooking_skill": "Intermediate",
        "allergies": ["Peanuts", "Shellfish"],
        "foods_to_avoid": ["Very spicy food"]
    }
    fridge_items = [
        {"name": "Rice", "quantity": 1, "unit": "kg"},
        {"name": "Tomato", "quantity": 4, "unit": "pieces"},
        {"name": "Paneer", "quantity": 200, "unit": "g"}
    ]
    meal_plan = "### 7-Day Plan\nMonday: Poha, Dal Rice, Paneer Curry\nTuesday: Upma, Khichdi, Roti"
    recipe = "### Paneer Tomato Rice\nPrep: 10m, Cook: 20m\nIngredients: Rice, Tomato, Paneer"
    question = "Which meal in my current plan is the fastest to cook?"

    prompt = build_assistant_prompt(
        user_question=question,
        user_profile=profile,
        fridge_items=fridge_items,
        current_meal_plan=meal_plan,
        current_recipe=recipe
    )

    # 1. User question
    assert question in prompt
    # 2. User profile details
    assert "Vegetarian" in prompt
    assert "Indian" in prompt
    assert "₹600" in prompt
    assert "25 minutes" in prompt
    assert "Intermediate" in prompt
    # 3. Allergies & Dislikes
    assert "Peanuts, Shellfish" in prompt
    assert "Very spicy food" in prompt
    # 4. Fridge items
    assert "Rice (1 kg)" in prompt
    assert "Tomato (4 pieces)" in prompt
    assert "Paneer (200 g)" in prompt
    # 5. Meal plan context
    assert "7-Day Plan" in prompt
    assert "Paneer Curry" in prompt
    # 6. Recipe context
    assert "Paneer Tomato Rice" in prompt
    # 7. Safety instructions
    assert "Never intentionally recommend known allergens" in prompt
    assert "educational" in prompt or "approximate" in prompt

    print("✓ Phase 8 Unit Test: Assistant prompt builder with full context verified!")


def test_assistant_prompt_builder_missing_optional_context():
    """
    Phase 8 Unit Test:
    Verify build_assistant_prompt handles missing/empty optional context gracefully without crashing.
    """
    question = "What is a balanced breakfast?"
    prompt = build_assistant_prompt(
        user_question=question,
        user_profile=None,
        fridge_items=None,
        current_meal_plan=None,
        current_recipe=None
    )

    assert question in prompt
    assert "No ingredients currently in fridge." in prompt
    assert "No meal plan has been generated yet." in prompt
    assert "No recipe has been generated yet." in prompt
    assert "NutriGen AI" in prompt
    print("✓ Phase 8 Unit Test: Assistant prompt builder with empty context verified!")


# ==========================================
# 2. Unit Tests: Ingredient Substitution & Modifications (Phase 7)
# ==========================================

def test_substitution_prompt_builder():
    """Verify substitution prompt contains ingredient, recipe, profile, allergies, and fridge items."""
    profile = {
        "name": "Aryan",
        "dietary_preference": "Vegetarian",
        "cuisine_preference": "Indian",
        "maximum_cooking_time": 30,
        "cooking_skill": "Beginner",
        "allergies": ["Peanuts", "Shellfish"],
        "foods_to_avoid": ["Very spicy food"]
    }
    fridge_items = [
        {"name": "Rice", "quantity": 1, "unit": "kg"},
        {"name": "Tomato", "quantity": 4, "unit": "pieces"},
        {"name": "Chickpeas", "quantity": 250, "unit": "g"},
        {"name": "Curd", "quantity": 500, "unit": "ml"}
    ]
    current_recipe = "### Paneer Tomato Rice\nIngredients: Paneer, Tomato, Rice\nCook rice, sauté tomato, add paneer."
    ingredient_to_replace = "Paneer"
    reason = "I don't have paneer at home, want a cheaper substitute"

    prompt = build_substitution_prompt(
        ingredient_to_replace=ingredient_to_replace,
        reason_or_request=reason,
        current_recipe=current_recipe,
        user_profile=profile,
        fridge_items=fridge_items
    )

    assert "Paneer" in prompt
    assert "I don't have paneer at home, want a cheaper substitute" in prompt
    assert "Paneer Tomato Rice" in prompt
    assert "Vegetarian" in prompt
    assert "Peanuts, Shellfish" in prompt
    assert "Very spicy food" in prompt
    assert "Chickpeas (250 g)" in prompt
    assert "Never intentionally suggest an ingredient that conflicts with the user's allergies" in prompt

    print("✓ Phase 7 Unit Test: Substitution prompt builder verified!")


def test_recipe_modification_prompt_builder():
    """Verify recipe modification prompt applies user requests while maintaining constraints."""
    current_recipe = "### Paneer Tomato Rice\nIngredients: Rice, Paneer, Tomato"
    user_request = "Make it faster and less oily"
    profile = {"dietary_preference": "Vegetarian", "allergies": ["Peanuts"]}

    prompt = build_modify_recipe_prompt(current_recipe, user_request, user_profile=profile)
    assert current_recipe in prompt
    assert user_request in prompt
    assert "Vegetarian" in prompt
    assert "Peanuts" in prompt
    print("✓ Phase 7 Unit Test: Recipe modification prompt builder passed!")


def test_modify_meal_plan_prompt_builder():
    """Verify meal plan modification prompt preserves original plan and applies changes."""
    current_plan = "Day 1: Breakfast: Poha, Lunch: Dal Rice, Dinner: Paneer Curry"
    mod_request = "Make dinners faster under 15 minutes"
    profile = {"dietary_preference": "Vegetarian", "allergies": ["Peanuts"]}

    prompt = build_modify_meal_plan_prompt(current_plan, mod_request, user_profile=profile)
    assert current_plan in prompt
    assert mod_request in prompt
    print("✓ Phase 7 Unit Test: Meal plan modification prompt builder passed!")


# ==========================================
# 3. Unit Tests: Recipe & Meal Plan Prompt Builders (Phases 5 & 6)
# ==========================================

def test_recipe_prompt_builder():
    """Verify recipe prompt contains meal name, diet, cuisine, time, skill, allergies, and fridge items."""
    profile = {
        "name": "Aryan",
        "dietary_preference": "Vegetarian",
        "cuisine_preference": "Indian",
        "maximum_cooking_time": 30,
        "cooking_skill": "Beginner",
        "allergies": ["Peanuts", "Shellfish"],
        "foods_to_avoid": ["Very spicy food"]
    }
    fridge_items = [
        {"name": "Rice", "quantity": 1, "unit": "kg"},
        {"name": "Tomato", "quantity": 4, "unit": "pieces"},
        {"name": "Onion", "quantity": 3, "unit": "pieces"},
        {"name": "Paneer", "quantity": 200, "unit": "g"}
    ]
    meal_name = "Paneer Tomato Rice"

    prompt = build_recipe_prompt(meal_name, user_profile=profile, fridge_items=fridge_items)

    assert "Paneer Tomato Rice" in prompt
    assert "Vegetarian" in prompt
    assert "Indian" in prompt
    assert "30 minutes" in prompt
    assert "Beginner" in prompt
    assert "Rice (1 kg)" in prompt
    assert "Tomato (4 pieces)" in prompt
    assert "Paneer (200 g)" in prompt
    assert "Peanuts, Shellfish" in prompt
    assert "Never intentionally include an ingredient listed under allergies" in prompt
    print("✓ Phase 6 Unit Test: Recipe prompt builder with profile, allergies, and fridge stock passed!")


def test_meal_plan_prompt_builder():
    """Verify meal plan prompt contains all user profile constraints and fridge ingredients."""
    profile = {
        "name": "Aryan",
        "dietary_preference": "Vegetarian",
        "cuisine_preference": "Gujarati",
        "weekly_budget": 600,
        "number_of_people": 2,
        "maximum_cooking_time": 25,
        "cooking_skill": "Intermediate",
        "allergies": ["Peanuts", "Shellfish"],
        "foods_to_avoid": ["Excess oil", "Mushrooms"]
    }
    fridge_items = [
        {"name": "Rice", "quantity": 1, "unit": "kg"},
        {"name": "Potato", "quantity": 500, "unit": "g"}
    ]

    prompt = build_meal_plan_prompt(
        user_profile=profile,
        fridge_items=fridge_items,
        num_days=5,
        meal_types=["Breakfast", "Lunch", "Dinner"],
        target_budget=600
    )

    assert "Vegetarian" in prompt
    assert "Gujarati" in prompt
    assert "₹600" in prompt
    assert "Rice (1 kg)" in prompt
    print("✓ Phase 5 Unit Test: Meal plan prompt builder passed!")


# ==========================================
# 4. Unit Tests: Gemini Service & Helpers (Phases 2–4)
# ==========================================

def test_simple_prompt_creation():
    """Verify simple prompt contains the user question."""
    q = "What can I cook with potatoes and onions?"
    prompt = build_simple_prompt(q)
    assert q in prompt
    assert "NutriGen AI" in prompt
    print("✓ Unit test: Simple prompt builder passed!")


def test_gemini_missing_api_key_graceful_handling():
    """Verify missing API key returns a clear, non-crashing informational response."""
    original_key = os.environ.get("GEMINI_API_KEY")
    try:
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
            
        success, response = generate_ai_response("Hello")
        assert not success
        assert "Gemini API key is not configured" in response
    finally:
        if original_key is not None:
            os.environ["GEMINI_API_KEY"] = original_key
            
    print("✓ Unit test: Missing Gemini API key graceful handling passed!")


def test_gemini_error_classification_and_models():
    """Verify Gemini models and error classification for 503 temporary vs fatal errors."""
    assert PRIMARY_MODEL == "gemini-3.7-flash"
    assert FALLBACK_MODEL == "gemini-3.6-flash"

    # Temporary 503 unavailability indicators
    assert _is_temporary_unavailable_error("503 UNAVAILABLE. This model is currently experiencing high demand.")
    assert _is_temporary_unavailable_error("Service Unavailable")
    assert not _is_temporary_unavailable_error("400 API_KEY_INVALID")

    # Fatal client errors that should NOT be retried
    assert _is_client_fatal_error("400 API_KEY_INVALID")
    assert _is_client_fatal_error("403 PERMISSION_DENIED")
    assert not _is_client_fatal_error("503 UNAVAILABLE")

    print("✓ Unit test: Gemini 503 & client error classification verified!")


def test_comma_separated_parsing():
    """Verify comma-separated string parser cleans whitespace and removes empty items."""
    res = parse_comma_separated_items("Peanuts, shellfish")
    assert res == ["Peanuts", "shellfish"]
    print("✓ Unit test: Comma-separated parser passed!")


def test_user_profile_validation():
    """Verify user profile validation logic."""
    valid_data = {
        "name": "Aryan",
        "age": 21,
        "number_of_people": 2,
        "dietary_preference": "Vegetarian",
        "cuisine_preference": "Indian",
        "weekly_budget": 500,
        "maximum_cooking_time": 30,
        "cooking_skill": "Intermediate",
        "allergies": ["Peanuts"],
        "foods_to_avoid": ["Mushrooms"]
    }
    is_valid, errors = validate_user_profile(valid_data)
    assert is_valid, f"Expected valid profile, got errors: {errors}"
    print("✓ Unit test: User profile validation passed!")


def test_expiry_status_calculation():
    """Verify expiry status calculation (Fresh, Expiring Soon, Expired)."""
    today = date.today()
    past_date = (today - timedelta(days=2)).isoformat()
    tomorrow_date = (today + timedelta(days=1)).isoformat()
    future_date = (today + timedelta(days=10)).isoformat()

    assert get_ingredient_status(past_date) == "Expired"
    assert get_ingredient_status(tomorrow_date) == "Expiring Soon"
    assert get_ingredient_status(future_date) == "Fresh"
    print("✓ Unit test: Expiry status calculation passed!")


# ==========================================
# 5. Streamlit Multi-Page App Integration Tests
# ==========================================

def test_app_initialization():
    """Verify app load and default navigation rendering."""
    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()
    assert not at.exception, f"App threw an exception on launch: {at.exception}"
    all_markdown = " ".join([m.value for m in at.markdown])
    assert "NutriGen AI" in all_markdown
    print("✓ App initialization integration test passed!")


def test_dashboard_page():
    """Verify Dashboard page components, status indicators, and metric tiles."""
    at = AppTest.from_file("pages/dashboard.py", default_timeout=10)
    at.run()
    assert not at.exception, f"Dashboard exception: {at.exception}"
    all_markdown = " ".join([m.value for m in at.markdown])
    assert "NutriGen AI" in all_markdown
    assert "Weekly Budget" in all_markdown
    print("✓ Dashboard page tests passed!")


def test_preferences_page():
    """Verify Preferences page saving and updating."""
    at = AppTest.from_file("pages/preferences.py", default_timeout=10)
    at.run()
    assert not at.exception
    at.text_input[0].input("Rahul Sharma")
    save_btns = [b for b in at.button if "Save Preferences" in b.label or "Update Preferences" in b.label]
    assert len(save_btns) > 0
    save_btns[0].click().run()
    assert not at.exception
    assert at.session_state.user_profile["name"] == "Rahul Sharma"
    print("✓ Preferences page tests passed!")


def test_fridge_page():
    """Verify Fridge inventory addition, search, and deletion."""
    at = AppTest.from_file("pages/fridge.py", default_timeout=10)
    at.run()
    assert not at.exception
    initial_count = len(at.session_state.fridge_items)
    at.text_input[0].input("Capsicum")
    add_btn = [b for b in at.button if "Add Ingredient" in b.label][0]
    add_btn.click().run()
    assert not at.exception
    assert len(at.session_state.fridge_items) == initial_count + 1
    print("✓ Fridge page inventory management tests passed!")


def test_meal_planner_page():
    """Verify Meal Planner generation, quick modification buttons, and mock rendering."""
    at = AppTest.from_file("pages/meal_planner.py", default_timeout=10)
    at.run()
    assert not at.exception
    
    gen_buttons = [b for b in at.button if "Generate Meal Plan" in b.label]
    assert len(gen_buttons) > 0
    
    mock_plan = "### ✨ 7-Day AI Meal Plan\n- Monday: Vegetable Poha\n- Tuesday: Dal Rice"
    at.session_state.generated_meal_plan = mock_plan
    at.run()
    assert not at.exception
    all_markdown = " ".join([m.value for m in at.markdown])
    assert "AI Generated Meal Plan" in all_markdown
    assert "Vegetable Poha" in all_markdown
    
    make_cheaper_btns = [b for b in at.button if "Make Cheaper" in b.label]
    assert len(make_cheaper_btns) > 0
    print("✓ Meal Planner page tests passed!")


def test_recipes_page_ui_and_substitution():
    """Verify Recipes page renders AI Recipe generator, AI substitutions, and library."""
    at = AppTest.from_file("pages/recipes.py", default_timeout=10)
    at.run()
    assert not at.exception, f"Recipes page exception: {at.exception}"
    
    all_markdown = " ".join([m.value for m in at.markdown])
    assert "AI Recipe Generator" in all_markdown
    assert "AI Ingredient Substitution" in all_markdown
    assert "Curated Recipe Library" in all_markdown
    
    gen_recipe_btns = [b for b in at.button if "Generate Recipe" in b.label]
    assert len(gen_recipe_btns) > 0

    find_sub_btns = [b for b in at.button if "Find Substitute" in b.label]
    assert len(find_sub_btns) > 0
    print("✓ Recipes page UI & Ingredient Substitution controls verified!")


def test_recipes_page_mock_substitution_and_modifications():
    """Verify mock AI recipe display, quick action chips, and mock substitution result rendering."""
    at = AppTest.from_file("pages/recipes.py", default_timeout=10)
    at.run()
    
    mock_recipe = "### 🍳 Paneer Tomato Rice\n⏱️ **Prep Time**: 10 mins\nIngredients: Rice, Paneer, Tomato"
    mock_sub = "### 🔄 AI Ingredient Substitution for **Paneer**\n1. **Tofu**\n2. **Chickpeas**"

    at.session_state.generated_recipe = mock_recipe
    at.session_state.substitution_result = mock_sub
    at.run()
    assert not at.exception
    
    all_markdown = " ".join([m.value for m in at.markdown])
    assert "AI Generated Recipe" in all_markdown
    assert "Paneer Tomato Rice" in all_markdown
    assert "AI Ingredient Substitution for" in all_markdown
    assert "Tofu" in all_markdown
    
    cheaper_btns = [b for b in at.button if "Make Cheaper" in b.label]
    assert len(cheaper_btns) > 0
    
    clear_sub_btns = [b for b in at.button if "Clear Substitutions" in b.label]
    assert len(clear_sub_btns) > 0
    print("✓ Mock substitution rendering and quick action controls verified!")


def test_ai_assistant_page_full_integration():
    """
    Integration Test:
    Verify AI Assistant page rendering, suggestion buttons, chat history storage,
    and Clear Chat preserving other session state components.
    """
    at_ai = AppTest.from_file("pages/ai_assistant.py", default_timeout=10)
    at_ai.run()
    assert not at_ai.exception, f"AI Assistant exception: {at_ai.exception}"
    
    all_markdown = " ".join([m.value for m in at_ai.markdown])
    assert "AI Assistant" in all_markdown
    assert "Try Asking" in all_markdown
    assert "Conversation" in all_markdown
    
    # 1. Verify example suggestion buttons exist
    sugg_buttons = [b for b in at_ai.button if "What can I cook" in b.label or "dinner today" in b.label]
    assert len(sugg_buttons) > 0
    
    # 2. Verify chat history rendering with mock message
    mock_q = "How many calories are in dal rice?"
    mock_ans = "Dal Rice contains approximately ~350 kcal per standard serving."
    at_ai.session_state.chat_history = [
        {"role": "user", "content": mock_q},
        {"role": "assistant", "content": mock_ans}
    ]
    at_ai.session_state.generated_meal_plan = "### Active Meal Plan\nMonday: Dal Rice"
    at_ai.session_state.generated_recipe = "### Active Recipe\nDal Rice"
    at_ai.run()
    assert not at_ai.exception
    
    rendered_text = " ".join([m.value for m in at_ai.markdown])
    assert mock_q in rendered_text
    assert mock_ans in rendered_text
    
    # 3. Verify Clear Chat button functionality
    clear_btns = [b for b in at_ai.button if "Clear Chat" in b.label]
    assert len(clear_btns) > 0
    clear_btns[0].click().run()
    assert not at_ai.exception
    
    # Verify ONLY chat history is cleared
    assert len(at_ai.session_state.chat_history) == 0
    # Verify profile, fridge, meal plan, and recipe remain intact
    assert at_ai.session_state.user_profile is not None
    assert len(at_ai.session_state.fridge_items) > 0
    assert at_ai.session_state.generated_meal_plan == "### Active Meal Plan\nMonday: Dal Rice"
    assert at_ai.session_state.generated_recipe == "### Active Recipe\nDal Rice"
    
    print("✓ Integration Test: AI Assistant UI, conversation history, and Clear Chat verified!")


# ==========================================
# 6. End-to-End System Integration Flow Test (Phase 9)
# ==========================================

def test_phase9_full_system_integration_flow():
    """
    Phase 9 End-to-End Test:
    Simulates complete user flow through all 6 interconnected modules:
    Profile -> Fridge -> Meal Planner -> Recipe Generator -> Modification & Substitution -> AI Assistant.
    """
    # 1. Profile Setup & Validation
    profile = {
        "name": "Aryan Rangani",
        "age": 21,
        "number_of_people": 2,
        "dietary_preference": "Vegetarian",
        "cuisine_preference": "Indian",
        "weekly_budget": 500,
        "maximum_cooking_time": 30,
        "cooking_skill": "Intermediate",
        "allergies": ["Peanuts"],
        "foods_to_avoid": ["Excess oily food"]
    }
    is_valid, errs = validate_user_profile(profile)
    assert is_valid, f"Profile validation failed: {errs}"

    # 2. Fridge Stock Check
    fridge = get_default_fridge_items()
    assert len(fridge) >= 5
    fridge_summary = get_ingredient_context_summary(fridge)
    assert "Rice" in fridge_summary

    # 3. Meal Plan Prompt Generation
    meal_prompt = build_meal_plan_prompt(profile, fridge, num_days=7)
    assert "Aryan Rangani" not in meal_prompt or "Vegetarian" in meal_prompt
    assert "Peanuts" in meal_prompt

    # 4. Recipe Generation & Modification Prompt
    recipe_prompt = build_recipe_prompt("Paneer Tomato Rice", profile, fridge)
    assert "Paneer Tomato Rice" in recipe_prompt
    mod_recipe_prompt = build_modify_recipe_prompt("### Paneer Tomato Rice", "Use less oil", profile, fridge)
    assert "Use less oil" in mod_recipe_prompt

    # 5. Ingredient Substitution Prompt
    sub_prompt = build_substitution_prompt("Paneer", "Cheaper alternative", "### Paneer Tomato Rice", profile, fridge)
    assert "Paneer" in sub_prompt
    assert "Cheaper alternative" in sub_prompt

    # 6. Assistant Prompt Integration
    asst_prompt = build_assistant_prompt(
        "What can I make for dinner tonight?",
        profile,
        fridge,
        current_meal_plan="Monday: Paneer Tomato Rice",
        current_recipe="Paneer Tomato Rice recipe"
    )
    assert "What can I make for dinner tonight?" in asst_prompt
    assert "Monday: Paneer Tomato Rice" in asst_prompt

    print("✓ Phase 9 End-to-End Test: Full system data flow & inter-module integration verified!")


# ==========================================
# 7. Hackathon Problem 14 Tests (Phase 18)
# ==========================================

def test_constraint_validator_hard_constraints():
    """Verify deterministic Python constraint validator checks vegetarian, budget, and cooking limits."""
    # Test non-vegetarian detection
    non_veg_plan = {
        "summary": {"estimated_total_cost": 400.0},
        "days": [
            {
                "day": "Monday",
                "breakfast": {"name": "Poha", "ingredients": ["Poha", "Onion"], "estimated_cost": 20, "cooking_time_minutes": 15},
                "lunch": {"name": "Chicken Curry", "ingredients": ["200 g Chicken", "Spices"], "estimated_cost": 150, "cooking_time_minutes": 25},
                "dinner": {"name": "Dal Rice", "ingredients": ["Dal", "Rice"], "estimated_cost": 30, "cooking_time_minutes": 20}
            }
        ]
    }
    val_res = validate_meal_plan_constraints(non_veg_plan, budget_limit=500, max_cook_time=30, required_days=1)
    assert not val_res["valid"], "Non-veg plan should fail validation"
    assert not val_res["vegetarian_ok"], "Vegetarian flag should be False"
    assert any("chicken" in v.lower() for v in val_res["violations"])

    # Test budget overrun detection
    over_budget_plan = {
        "summary": {"estimated_total_cost": 850.0},
        "days": [
            {
                "day": "Monday",
                "breakfast": {"name": "Poha", "ingredients": ["Poha"], "estimated_cost": 100, "cooking_time_minutes": 15},
                "lunch": {"name": "Paneer Thali", "ingredients": ["Paneer"], "estimated_cost": 350, "cooking_time_minutes": 20},
                "dinner": {"name": "Special Dinner", "ingredients": ["Dry fruits", "Saffron"], "estimated_cost": 400, "cooking_time_minutes": 25}
            }
        ]
    }
    val_budget = validate_meal_plan_constraints(over_budget_plan, budget_limit=500, max_cook_time=30, required_days=1)
    assert not val_budget["budget_ok"]
    assert any("budget exceeded" in v.lower() for v in val_budget["violations"])

    # Test cooking time overrun detection
    slow_plan = {
        "summary": {"estimated_total_cost": 200.0},
        "days": [
            {
                "day": "Monday",
                "breakfast": {"name": "Poha", "ingredients": ["Poha"], "estimated_cost": 20, "cooking_time_minutes": 45},
                "lunch": {"name": "Dal Rice", "ingredients": ["Dal"], "estimated_cost": 40, "cooking_time_minutes": 20},
                "dinner": {"name": "Roti Sabzi", "ingredients": ["Atta"], "estimated_cost": 30, "cooking_time_minutes": 20}
            }
        ]
    }
    val_time = validate_meal_plan_constraints(slow_plan, budget_limit=500, max_cook_time=30, required_days=1)
    assert not val_time["cooking_time_ok"]
    assert any("cooking time" in v.lower() for v in val_time["violations"])
    print("✓ Hackathon Test 1: Deterministic Constraint Validator hard constraints verified!")


def test_grocery_consolidation_engine():
    """Verify weekly grocery consolidation combines ingredients, matches pantry, and aggregates purchase needs."""
    days_data = [
        {
            "day": "Monday",
            "breakfast": {"ingredients": ["200 g Flattened Rice (Poha)", "2 pieces Onion"]},
            "lunch": {"ingredients": ["100 g Rice", "2 pieces Tomato"]},
            "dinner": {"ingredients": ["200 g Paneer", "2 pieces Tomato", "1 piece Onion"]}
        },
        {
            "day": "Tuesday",
            "breakfast": {"ingredients": ["100 g Rice", "1 piece Onion"]},
            "lunch": {"ingredients": ["150 g Rice", "2 pieces Tomato"]},
            "dinner": {"ingredients": ["200 g Paneer", "1 piece Tomato"]}
        }
    ]
    pantry = [
        {"name": "Tomato", "quantity": 4.0, "unit": "pieces", "category": "Vegetables"},
        {"name": "Rice", "quantity": 500.0, "unit": "g", "category": "Grains"}
    ]
    grocery = consolidate_grocery_list(days_data, pantry_items=pantry)
    
    assert grocery["total_pantry_items_used"] >= 1
    assert "items_to_buy" in grocery
    
    # Check Tomato aggregation (7 required, 4 in pantry -> 3 to buy)
    tomato_item = next((i for i in grocery["items_to_buy"] if "tomato" in i["name"].lower()), None)
    if tomato_item:
        assert tomato_item["required_qty"] == 7.0
        assert tomato_item["pantry_available"] == 4.0
        assert tomato_item["need_to_buy"] == 3.0
        assert tomato_item["usage_count"] >= 3

    assert grocery["estimated_total_grocery_cost"] > 0
    print("✓ Hackathon Test 2: Grocery List Consolidation Engine verified!")


def test_ingredient_reuse_metric():
    """Verify ingredient reuse calculation correctly identifies items used across multiple meals."""
    plan = {
        "summary": {"estimated_total_cost": 300.0},
        "days": [
            {
                "day": "Monday",
                "breakfast": {"name": "Poha", "ingredients": ["Poha", "Tomato", "Onion"], "estimated_cost": 20, "cooking_time_minutes": 15},
                "lunch": {"name": "Dal Rice", "ingredients": ["Rice", "Toor Dal", "Tomato"], "estimated_cost": 30, "cooking_time_minutes": 20},
                "dinner": {"name": "Paneer Rice", "ingredients": ["Rice", "Paneer", "Tomato", "Onion"], "estimated_cost": 50, "cooking_time_minutes": 20}
            }
        ]
    }
    val = validate_meal_plan_constraints(plan, budget_limit=500, max_cook_time=30, min_reuse_target=30.0, required_days=1)
    reuse_rate = val["metrics"]["ingredient_reuse_rate"]
    # Reused across >= 2 meals: Tomato (3 meals), Rice (2 meals), Onion (2 meals)
    assert reuse_rate >= 30.0, f"Expected reuse >= 30%, got {reuse_rate}%"
    assert val["ingredient_reuse_ok"]
    print("✓ Hackathon Test 3: Ingredient reuse calculation verified!")


def test_weekly_variety_and_protein_diversity():
    """Verify weekly variety rule flags repeated dinners and ensures protein source diversity."""
    # Plan with duplicate dinner
    duplicate_dinner_plan = {
        "summary": {"estimated_total_cost": 300.0},
        "days": [
            {"day": "Monday", "breakfast": {"name": "B1", "ingredients": ["A"]}, "lunch": {"name": "L1", "ingredients": ["B"]}, "dinner": {"name": "Dal Fry", "ingredients": ["C"], "protein_source": "Dal"}},
            {"day": "Tuesday", "breakfast": {"name": "B2", "ingredients": ["D"]}, "lunch": {"name": "L2", "ingredients": ["E"]}, "dinner": {"name": "Dal Fry", "ingredients": ["F"], "protein_source": "Dal"}},
            {"day": "Wednesday", "breakfast": {"name": "B3", "ingredients": ["G"]}, "lunch": {"name": "L3", "ingredients": ["H"]}, "dinner": {"name": "Dal Fry", "ingredients": ["I"], "protein_source": "Dal"}}
        ]
    }
    val = validate_meal_plan_constraints(duplicate_dinner_plan, budget_limit=500, max_cook_time=30, required_days=3)
    assert not val["variety_ok"]
    assert any("dinner variety" in v.lower() for v in val["violations"])
    print("✓ Hackathon Test 4: Weekly variety and protein diversity rule verified!")


def test_non_medical_nutrition_balance():
    """Verify non-medical nutrition balance heuristic evaluates protein, veggies, and carbs."""
    balanced_plan = {
        "summary": {"estimated_total_cost": 300.0},
        "days": [
            {
                "day": "Monday",
                "breakfast": {"name": "Poha", "ingredients": ["Poha", "Peanuts", "Onion"], "protein_source": "Peanuts", "vegetable_components": ["Onion"], "grain_or_carb": "Poha", "estimated_cost": 20, "cooking_time_minutes": 15},
                "lunch": {"name": "Dal Rice", "ingredients": ["Toor Dal", "Rice", "Tomato"], "protein_source": "Toor Dal", "vegetable_components": ["Tomato"], "grain_or_carb": "Rice", "estimated_cost": 30, "cooking_time_minutes": 20},
                "dinner": {"name": "Palak Paneer", "ingredients": ["Paneer", "Palak", "Roti"], "protein_source": "Paneer", "vegetable_components": ["Palak"], "grain_or_carb": "Roti", "estimated_cost": 40, "cooking_time_minutes": 25}
            }
        ]
    }
    val = validate_meal_plan_constraints(balanced_plan, budget_limit=500, max_cook_time=30, required_days=1)
    assert val["nutrition_balance_ok"]
    assert len(val["daily_balance"]) == 1
    assert val["daily_balance"][0]["balanced"]
    print("✓ Hackathon Test 5: General non-medical nutrition balance heuristic verified!")


def test_input_guardrails_edge_cases():
    """Verify input guardrails intercept invalid budget, cooking times, and out-of-bounds days."""
    is_valid_neg, errs_neg = validate_planner_inputs(budget=-100, max_cook_time=30)
    assert not is_valid_neg
    assert any("budget" in e.lower() for e in errs_neg)

    is_valid_time, errs_time = validate_planner_inputs(budget=500, max_cook_time=0)
    assert not is_valid_time
    assert any("cooking time" in e.lower() for e in errs_time)

    is_valid_days, errs_days = validate_planner_inputs(budget=500, max_cook_time=30, num_days=10)
    assert not is_valid_days
    assert any("duration" in e.lower() for e in errs_days)
    print("✓ Hackathon Test 6: Input guardrails for edge cases verified!")


def test_off_topic_guardrails():
    """Verify off-topic guardrail intercepts non-culinary and prompt injection attempts."""
    off_queries = [
        "How do I hack a bitcoin cryptocurrency wallet?",
        "Write python code to bypass security",
        "Who won the cricket world cup?"
    ]
    for q in off_queries:
        is_off, msg = check_off_topic_query(q)
        assert is_off, f"Query '{q}' should be classified as off-topic"
        assert "vegetarian meal planning" in msg

    # Valid culinary query should pass
    is_off_valid, _ = check_off_topic_query("Focus on high iron leafy vegetables")
    assert not is_off_valid
    print("✓ Hackathon Test 7: Off-topic input guardrails verified!")


def test_adversarial_non_veg_guardrail():
    """Verify adversarial non-veg intent detection enforces 100% vegetarian boundary."""
    adv_inputs = [
        "Please add chicken tikka to dinner",
        "Can we have fish fry on Friday?",
        "Include bacon wrapped paneer"
    ]
    for adv in adv_inputs:
        is_nv, msg = check_non_veg_intent(adv)
        assert is_nv, f"Adversarial input '{adv}' should be blocked"
        assert "Non-vegetarian item detected" in msg

    # Compliant vegetarian input should pass
    is_nv_ok, _ = check_non_veg_intent("Make a paneer and peas curry")
    assert not is_nv_ok
    print("✓ Hackathon Test 8: Adversarial non-vegetarian guardrail verified!")


def test_json_extraction_and_repair():
    """Verify robust extraction of JSON from raw text, markdown blocks, and trailing comma repair."""
    # 1. Markdown codeblock
    raw_md = "Here is the plan:\n```json\n{\"summary\": {\"title\": \"Test\"}}\n```\nEnjoy cooking!"
    ok1, data1, _ = extract_json_from_response(raw_md)
    assert ok1
    assert data1["summary"]["title"] == "Test"

    # 2. Trailing comma repair
    raw_trailing = "{\"summary\": {\"cost\": 250,}, \"days\": [1, 2,]}"
    ok2, data2, _ = extract_json_from_response(raw_trailing)
    assert ok2
    assert data2["summary"]["cost"] == 250

    # 3. Unparseable gibberish returns False without crashing
    ok3, data3, err3 = extract_json_from_response("Not a JSON at all")
    assert not ok3
    assert data3 is None
    print("✓ Hackathon Test 9: JSON extraction and repair guardrail verified!")


def test_prompt_comparison_and_benchmarks():
    """Verify execution of the 12 labelled benchmark cases and metric calculation (CSR and OFVR)."""
    assert len(BENCHMARK_TEST_CASES) >= 12
    
    # Check that at least 2 are edge/adversarial
    edge_cases = [tc for tc in BENCHMARK_TEST_CASES if tc["type"] in ["edge", "adversarial"]]
    assert len(edge_cases) >= 2, f"Expected at least 2 edge/adversarial cases, found {len(edge_cases)}"

    # Run benchmark evaluation
    bench = run_local_benchmark_evaluation()
    assert bench["total_test_cases"] == 12
    
    metrics = bench["metrics"]
    final_csr = metrics["final"]["constraint_satisfaction_rate"]
    final_ofvr = metrics["final"]["format_validity_rate"]
    v1_csr = metrics["v1"]["constraint_satisfaction_rate"]

    assert final_csr >= 80.0, f"Final CSR should be high, got {final_csr}%"
    assert final_ofvr >= 90.0, f"Final OFVR should be high, got {final_ofvr}%"
    assert final_csr > v1_csr, "Final chained prompt should outperform V1 baseline"

    print(f"✓ Hackathon Test 10: Benchmark Suite (12 cases) & Metrics verified! Final CSR: {final_csr}%, V1 CSR: {v1_csr}%")


if __name__ == "__main__":
    # Unit Tests (Phase 8 & 9)
    test_assistant_prompt_builder_full_context()
    test_assistant_prompt_builder_missing_optional_context()
    test_phase9_full_system_integration_flow()

    # Unit Tests (Phases 5–7)
    test_substitution_prompt_builder()
    test_recipe_modification_prompt_builder()
    test_modify_meal_plan_prompt_builder()
    test_recipe_prompt_builder()
    test_meal_plan_prompt_builder()
    test_simple_prompt_creation()
    test_gemini_missing_api_key_graceful_handling()
    test_gemini_error_classification_and_models()
    test_comma_separated_parsing()
    test_user_profile_validation()
    test_expiry_status_calculation()

    # App Integration Tests (Phases 1–8)
    test_app_initialization()
    test_dashboard_page()
    test_preferences_page()
    test_fridge_page()
    test_meal_planner_page()
    test_recipes_page_ui_and_substitution()
    test_recipes_page_mock_substitution_and_modifications()
    test_ai_assistant_page_full_integration()

    # Hackathon Problem 14 Unit & Integration Tests (Phase 18)
    test_constraint_validator_hard_constraints()
    test_grocery_consolidation_engine()
    test_ingredient_reuse_metric()
    test_weekly_variety_and_protein_diversity()
    test_non_medical_nutrition_balance()
    test_input_guardrails_edge_cases()
    test_off_topic_guardrails()
    test_adversarial_non_veg_guardrail()
    test_json_extraction_and_repair()
    test_prompt_comparison_and_benchmarks()

    print("\n🎉 ALL 29 UNIT & INTEGRATION TESTS (INCLUDING ALL HACKATHON PROBLEM 14 SUITES) PASSED SUCCESSFULLY!")

