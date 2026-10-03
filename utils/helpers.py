"""
NutriGen AI - Helper Functions & Data Store
Provides session state initialization, CSS injection, user profile validation,
ingredient inventory management, expiry tracking, and mock datasets for Phase 3.
"""

import os
from datetime import date, datetime, timedelta
from typing import List, Tuple, Dict, Any, Union, Optional
import streamlit as st


# ==========================================
# 1. User Profile Data Model & Helpers (Phase 2)
# ==========================================

def get_default_user_profile() -> Dict[str, Any]:
    """Return default structured user profile data model."""
    return {
        "name": "Aryan",
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


def parse_comma_separated_items(items_input: Union[str, List[str]]) -> List[str]:
    """
    Parse a comma-separated string or list into a clean, stripped list of non-empty strings.
    Example: 'Peanuts, shellfish,  ' -> ['Peanuts', 'shellfish']
    """
    if isinstance(items_input, list):
        return [str(item).strip() for item in items_input if str(item).strip()]
    
    if not isinstance(items_input, str) or not items_input.strip():
        return []
        
    return [item.strip() for item in items_input.split(",") if item.strip()]


def validate_user_profile(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate structured user profile fields.
    Returns (is_valid, list_of_error_messages).
    """
    errors: List[str] = []

    # 1. Number of people validation
    people = data.get("number_of_people")
    if people is None or not isinstance(people, (int, float)) or int(people) < 1:
        errors.append("Number of people must be at least 1.")
    elif int(people) > 20:
        errors.append("Number of people cannot exceed 20.")

    # 2. Weekly budget validation
    budget = data.get("weekly_budget")
    if budget is None or not isinstance(budget, (int, float)) or float(budget) <= 0:
        errors.append("Weekly food budget must be greater than ₹0.")
    elif float(budget) > 100000:
        errors.append("Weekly food budget cannot exceed ₹1,00,000.")

    # 3. Maximum cooking time validation
    cook_time = data.get("maximum_cooking_time")
    if cook_time is None or not isinstance(cook_time, (int, float)) or int(cook_time) <= 0:
        errors.append("Maximum cooking time must be a positive number of minutes.")

    # 4. Age validation (optional)
    age = data.get("age")
    if age is not None and age != "":
        try:
            age_int = int(age)
            if age_int < 1 or age_int > 120:
                errors.append("Age must be a reasonable number between 1 and 120.")
        except (ValueError, TypeError):
            errors.append("Age must be a valid integer.")

    # 5. Dietary preference check
    valid_diets = ["Vegetarian", "Vegan", "Non-Vegetarian", "Jain", "Eggetarian", "Other"]
    diet = data.get("dietary_preference")
    if diet and diet not in valid_diets:
        errors.append(f"Invalid dietary preference. Allowed options: {', '.join(valid_diets)}.")

    return len(errors) == 0, errors


# ==========================================
# 2. Ingredient & Fridge Data Model & Helpers (Phase 3)
# ==========================================

ALLOWED_INGREDIENT_UNITS = ["g", "kg", "ml", "litre", "pieces"]
ALLOWED_INGREDIENT_CATEGORIES = [
    "Vegetables",
    "Fruits",
    "Grains",
    "Dairy",
    "Protein",
    "Spices",
    "Pantry",
    "Beverages",
    "Other"
]


def get_default_fridge_items() -> List[Dict[str, Any]]:
    """
    Return default structured fridge ingredient inventory.
    Generates relative expiry dates to ensure dynamic and accurate status testing.
    """
    today = date.today()
    return [
        {
            "id": "ing_1",
            "name": "Rice",
            "quantity": 1.0,
            "unit": "kg",
            "category": "Grains",
            "expiry_date": (today + timedelta(days=45)).isoformat()
        },
        {
            "id": "ing_2",
            "name": "Potato",
            "quantity": 500.0,
            "unit": "g",
            "category": "Vegetables",
            "expiry_date": (today + timedelta(days=12)).isoformat()
        },
        {
            "id": "ing_3",
            "name": "Tomato",
            "quantity": 4.0,
            "unit": "pieces",
            "category": "Vegetables",
            "expiry_date": (today + timedelta(days=2)).isoformat()
        },
        {
            "id": "ing_4",
            "name": "Onion",
            "quantity": 3.0,
            "unit": "pieces",
            "category": "Vegetables",
            "expiry_date": (today + timedelta(days=8)).isoformat()
        },
        {
            "id": "ing_5",
            "name": "Paneer",
            "quantity": 200.0,
            "unit": "g",
            "category": "Dairy",
            "expiry_date": (today + timedelta(days=1)).isoformat()
        },
        {
            "id": "ing_6",
            "name": "Curd",
            "quantity": 500.0,
            "unit": "ml",
            "category": "Dairy",
            "expiry_date": (today + timedelta(days=2)).isoformat()
        }
    ]


def parse_expiry_date(expiry_date_val: Union[str, date]) -> date:
    """Parse string or date to datetime.date object safely."""
    if isinstance(expiry_date_val, date):
        return expiry_date_val
    try:
        return datetime.strptime(str(expiry_date_val).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return date.today()


def get_ingredient_status(expiry_date_val: Union[str, date]) -> str:
    """
    Determine ingredient expiry status based on current system date:
    - 'Expired': expiry date is before today (days < 0)
    - 'Expiring Soon': expiry date is today or within the next 3 days (0 <= days <= 3)
    - 'Fresh': expiry date is more than 3 days away (days > 3)
    """
    exp_date = parse_expiry_date(expiry_date_val)
    today = date.today()
    days_diff = (exp_date - today).days

    if days_diff < 0:
        return "Expired"
    elif 0 <= days_diff <= 3:
        return "Expiring Soon"
    else:
        return "Fresh"


def get_expiry_countdown_text(expiry_date_val: Union[str, date]) -> str:
    """Return human-readable countdown string like 'expires today', 'expires tomorrow', or 'expired 2 days ago'."""
    exp_date = parse_expiry_date(expiry_date_val)
    today = date.today()
    days_diff = (exp_date - today).days

    if days_diff < 0:
        abs_days = abs(days_diff)
        return f"expired {abs_days} day{'s' if abs_days > 1 else ''} ago"
    elif days_diff == 0:
        return "expires today"
    elif days_diff == 1:
        return "expires tomorrow"
    elif days_diff <= 3:
        return f"expires in {days_diff} days"
    else:
        return f"expires in {days_diff} days"


def get_expiring_ingredients(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return all ingredients expiring today or within 3 days."""
    return [item for item in items if get_ingredient_status(item.get("expiry_date", "")) == "Expiring Soon"]


def get_expired_ingredients(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return all ingredients whose expiry date has passed."""
    return [item for item in items if get_ingredient_status(item.get("expiry_date", "")) == "Expired"]


def find_duplicate_ingredient(
    name: str,
    unit: str,
    items: List[Dict[str, Any]],
    exclude_id: Optional[Union[str, int]] = None
) -> Optional[Dict[str, Any]]:
    """
    Case-insensitive check for existing ingredient with matching name and unit.
    Returns the matching ingredient dictionary if found, else None.
    """
    clean_name = name.strip().lower()
    clean_unit = unit.strip().lower()

    for item in items:
        if exclude_id and str(item.get("id")) == str(exclude_id):
            continue
        item_name = str(item.get("name", "")).strip().lower()
        item_unit = str(item.get("unit", "")).strip().lower()
        if item_name == clean_name and item_unit == clean_unit:
            return item
    return None


def get_ingredient_context_summary(items: List[Dict[str, Any]]) -> str:
    """Format in-stock ingredients as a structured context summary for future GenAI prompts."""
    if not items:
        return "No ingredients currently in fridge."
    
    formatted_items = []
    for item in items:
        qty = item.get("quantity", 0)
        qty_str = f"{int(qty) if isinstance(qty, (int, float)) and float(qty).is_integer() else qty} {item.get('unit', '')}"
        formatted_items.append(f"{item.get('name', 'Unknown')} ({qty_str})")
    
    return ", ".join(formatted_items)


# ==========================================
# 3. Global App Styling & Navigation Branding
# ==========================================

def load_css():
    """Load and inject custom CSS from assets/styles.css."""
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "styles.css")
    if os.path.exists(css_path):
        with open(css_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables with default structured data if not already set."""
    
    # 1. User Profile & Preferences (Phase 2 Data Model)
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = get_default_user_profile()

    # Maintain backward compatibility alias for Phase 1 components
    if "preferences" not in st.session_state:
        profile = st.session_state.user_profile
        st.session_state.preferences = {
            "name": profile.get("name", "Aryan"),
            "age": profile.get("age", 21),
            "people_count": profile.get("number_of_people", 2),
            "diet": profile.get("dietary_preference", "Vegetarian"),
            "cuisine": profile.get("cuisine_preference", "Indian"),
            "budget": profile.get("weekly_budget", 500),
            "max_cooking_time": profile.get("maximum_cooking_time", 30),
            "cooking_skill": profile.get("cooking_skill", "Intermediate"),
            "allergies": ", ".join(profile.get("allergies", ["Peanuts"])),
            "foods_to_avoid": ", ".join(profile.get("foods_to_avoid", ["Excess oily food"]))
        }

    # 2. Fridge Ingredients (Phase 3 Structured Inventory)
    if "fridge_items" not in st.session_state:
        st.session_state.fridge_items = get_default_fridge_items()

    # 3. Recipes Database (Mock)
    if "recipes" not in st.session_state:
        st.session_state.recipes = [
            {
                "id": "poha",
                "name": "Vegetable Poha",
                "prep_time": "10 mins",
                "cook_time": "15 mins",
                "difficulty": "Beginner",
                "calories": "280 kcal",
                "tags": ["Quick", "Breakfast", "Vegetarian"],
                "description": "A light and nutritious flattened rice breakfast dish cooked with onions, potatoes, green chilies, and roasted peanuts.",
                "ingredients": [
                    {"name": "Flattened Rice (Poha)", "qty": "1.5 cups"},
                    {"name": "Potato (finely chopped)", "qty": "1 small"},
                    {"name": "Onion (chopped)", "qty": "1 medium"},
                    {"name": "Green Chilies", "qty": "2 pieces"},
                    {"name": "Mustard Seeds", "qty": "1/2 tsp"},
                    {"name": "Turmeric Powder", "qty": "1/4 tsp"},
                    {"name": "Lemon Juice", "qty": "1 tbsp"},
                    {"name": "Fresh Coriander", "qty": "2 tbsp"}
                ],
                "steps": [
                    "Rinse the poha in a colander under running water gently until soft, then drain completely and set aside.",
                    "Heat 1 tbsp oil in a pan, add mustard seeds and let them splutter.",
                    "Add chopped onions and green chilies. Sauté until translucent.",
                    "Add diced potatoes, turmeric, and salt. Cover and cook on low heat until potatoes are tender.",
                    "Add the rinsed poha and mix gently to combine all ingredients evenly.",
                    "Cover with lid and steam on low flame for 2 minutes.",
                    "Turn off heat, drizzle lemon juice, and garnish with fresh chopped coriander before serving."
                ]
            },
            {
                "id": "paneer_tomato_rice",
                "name": "Paneer Tomato Rice",
                "prep_time": "15 mins",
                "cook_time": "20 mins",
                "difficulty": "Intermediate",
                "calories": "420 kcal",
                "tags": ["High Protein", "Lunch", "Vegetarian"],
                "description": "Fragrant basmati rice tossed with spiced tangy tomato gravy and golden pan-seared paneer cubes.",
                "ingredients": [
                    {"name": "Cooked Basmati Rice", "qty": "2 cups"},
                    {"name": "Paneer (cubed)", "qty": "150 grams"},
                    {"name": "Tomatoes (pureed)", "qty": "3 large"},
                    {"name": "Onion (finely chopped)", "qty": "1 medium"},
                    {"name": "Ginger-Garlic Paste", "qty": "1 tsp"},
                    {"name": "Garam Masala", "qty": "1/2 tsp"},
                    {"name": "Cumin Seeds", "qty": "1 tsp"},
                    {"name": "Oil or Ghee", "qty": "1.5 tbsp"}
                ],
                "steps": [
                    "Lightly pan-fry paneer cubes in 1/2 tbsp ghee until edges are light golden, then set aside.",
                    "In the same pan, heat remaining oil, crackle cumin seeds, and sauté onions until golden brown.",
                    "Add ginger-garlic paste and sauté for 1 minute until raw aroma dissipates.",
                    "Pour in tomato puree, chili powder, coriander powder, and salt. Cook until oil separates from the masala.",
                    "Add garam masala and pan-seared paneer cubes, stirring gently to coat with sauce.",
                    "Gently fold in the cooked rice without breaking the grains.",
                    "Simmer on low flame for 3 minutes to allow flavors to meld. Serve hot with raita."
                ]
            },
            {
                "id": "dal_rice",
                "name": "Dal Rice",
                "prep_time": "10 mins",
                "cook_time": "25 mins",
                "difficulty": "Beginner",
                "calories": "350 kcal",
                "tags": ["Comfort Food", "Protein", "Everyday"],
                "description": "Classic comforting yellow toor dal tempered with cumin, garlic, and ghee served alongside steaming fluffy rice.",
                "ingredients": [
                    {"name": "Toor Dal (Yellow Pigeon Peas)", "qty": "1/2 cup"},
                    {"name": "Rice", "qty": "1 cup"},
                    {"name": "Tomato (chopped)", "qty": "1 small"},
                    {"name": "Garlic (crushed)", "qty": "4 cloves"},
                    {"name": "Cumin Seeds & Mustard Seeds", "qty": "1/2 tsp each"},
                    {"name": "Ghee", "qty": "1 tbsp"},
                    {"name": "Turmeric & Salt", "qty": "To taste"}
                ],
                "steps": [
                    "Pressure cook toor dal with 2 cups water, turmeric, and chopped tomato for 4 whistles until soft and mushy.",
                    "Cook rice separately in 2 cups of boiling water until tender and drained.",
                    "Whisk the cooked dal smoothly with a ladle, adjusting consistency with warm water.",
                    "In a small tadka pan, heat ghee. Add mustard seeds, cumin seeds, and crushed garlic.",
                    "Pour the sizzling tadka over the dal immediately and cover with lid for 2 minutes to trap aroma.",
                    "Serve steaming hot dal poured over fluffy rice with a dollop of ghee."
                ]
            },
            {
                "id": "khichdi",
                "name": "Vegetable Khichdi",
                "prep_time": "10 mins",
                "cook_time": "20 mins",
                "difficulty": "Beginner",
                "calories": "310 kcal",
                "tags": ["Light", "One-Pot", "Healthy"],
                "description": "A wholesome, easy-to-digest one-pot meal combining rice, yellow moong dal, and seasonal garden vegetables.",
                "ingredients": [
                    {"name": "Rice & Moong Dal (equal parts)", "qty": "1 cup total"},
                    {"name": "Mixed Veggies (Carrots, Peas, Beans)", "qty": "1 cup"},
                    {"name": "Cumin Seeds & Hing", "qty": "1/2 tsp each"},
                    {"name": "Ginger (grated)", "qty": "1 tsp"},
                    {"name": "Turmeric Powder", "qty": "1/2 tsp"},
                    {"name": "Ghee", "qty": "1 tbsp"},
                    {"name": "Water", "qty": "4 cups"}
                ],
                "steps": [
                    "Wash rice and moong dal together and soak in water for 15 minutes.",
                    "Heat ghee in a pressure cooker. Add cumin seeds and a pinch of asafoetida (hing).",
                    "Add grated ginger and mixed vegetables; sauté for 2 minutes.",
                    "Add drained rice-dal mixture, turmeric, salt, and 4 cups of water.",
                    "Close the cooker and cook on medium flame for 3 to 4 whistles for a soft, comforting texture.",
                    "Release pressure naturally, top with fresh ghee, and serve with curd or papad."
                ]
            },
            {
                "id": "aloo_roti",
                "name": "Aloo Roti",
                "prep_time": "15 mins",
                "cook_time": "15 mins",
                "difficulty": "Intermediate",
                "calories": "260 kcal per roti",
                "tags": ["Traditional", "Wholesome", "Dinner"],
                "description": "Soft, golden whole wheat flatbreads stuffed with spiced mashed potatoes and herbs.",
                "ingredients": [
                    {"name": "Whole Wheat Flour", "qty": "2 cups"},
                    {"name": "Boiled Potatoes (mashed)", "qty": "3 medium"},
                    {"name": "Green Chilies (chopped)", "qty": "1 piece"},
                    {"name": "Chaat Masala & Cumin Powder", "qty": "1/2 tsp each"},
                    {"name": "Fresh Coriander (chopped)", "qty": "2 tbsp"},
                    {"name": "Ghee or Butter", "qty": "For roasting"}
                ],
                "steps": [
                    "Knead wheat flour with warm water and a pinch of salt into a soft, pliable dough. Rest for 10 minutes.",
                    "In a bowl, mix mashed potatoes, green chilies, chaat masala, cumin powder, salt, and coriander.",
                    "Divide dough into balls, flatten slightly, place a portion of potato stuffing in the center, and seal edges.",
                    "Roll gently on a dusted board into an even round disc.",
                    "Cook on a hot tawa (griddle), flipping once, and apply ghee on both sides until golden spots appear.",
                    "Serve warm with curd, fresh mint chutney, or homemade pickle."
                ]
            }
        ]

    # 4. Mock 7-Day Meal Plan
    if "meal_plan" not in st.session_state:
        st.session_state.meal_plan = [
            {"day": "Monday", "breakfast": "Vegetable Poha", "lunch": "Dal Rice", "dinner": "Paneer Vegetable Curry", "calories": "1,450 kcal"},
            {"day": "Tuesday", "breakfast": "Upma with Veggies", "lunch": "Rajma Chawal (Kidney Beans & Rice)", "dinner": "Aloo Roti with Curd", "calories": "1,520 kcal"},
            {"day": "Wednesday", "breakfast": "Methi Thepla", "lunch": "Vegetable Khichdi with Kadhi", "dinner": "Vegetable Pulao with Raita", "calories": "1,410 kcal"},
            {"day": "Thursday", "breakfast": "Moong Dal Chilla", "lunch": "Chole with Rice", "dinner": "Mixed Vegetable Sabzi & Phulka", "calories": "1,480 kcal"},
            {"day": "Friday", "breakfast": "Idli Sambar", "lunch": "Paneer Tomato Rice", "dinner": "Palak Paneer with Roti", "calories": "1,550 kcal"},
            {"day": "Saturday", "breakfast": "Masala Dosa", "lunch": "Curd Rice with Potato Roast", "dinner": "Vegetable Biryani with Cucumber Raita", "calories": "1,600 kcal"},
            {"day": "Sunday", "breakfast": "Stuffed Paratha with Butter", "lunch": "Special Gujarati Thali (Dal, Rice, Roti, Shaak)", "dinner": "Light Vegetable Soup & Toast", "calories": "1,500 kcal"}
        ]

    # 5. AI Assistant Chat History (Phase 8)
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {
                "role": "user",
                "content": "What can I cook with the ingredients in my fridge?"
            },
            {
                "role": "assistant",
                "content": "Based on your fridge inventory (Rice, Tomato, Onion, Paneer, Curd), you can make a delicious **Paneer Tomato Rice** or **Curd Rice with Sautéed Veggies** in under 25 minutes! Both fit your vegetarian diet and budget."
            }
        ]
    
    # Maintain chat_messages alias for backward compatibility
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = st.session_state.chat_history

    # 6. AI Generated Meal Plan (Phase 5)
    if "generated_meal_plan" not in st.session_state:
        st.session_state.generated_meal_plan = None

    # 7. AI Generated Recipe (Phase 6)
    if "generated_recipe" not in st.session_state:
        st.session_state.generated_recipe = None
    if "selected_recipe_meal" not in st.session_state:
        st.session_state.selected_recipe_meal = "Paneer Tomato Rice"

    # 8. AI Ingredient Substitution (Phase 7)
    if "substitution_result" not in st.session_state:
        st.session_state.substitution_result = None
    if "substitution_ingredient" not in st.session_state:
        st.session_state.substitution_ingredient = "Paneer"
    if "substitution_reason" not in st.session_state:
        st.session_state.substitution_reason = "I don't have paneer"

    # 9. Hackathon Problem 14: Constraint-Based Planner & Audit State
    if "prompt_history" not in st.session_state:
        st.session_state.prompt_history = []
    if "constraint_plan_result" not in st.session_state:
        st.session_state.constraint_plan_result = None
    if "comparison_result" not in st.session_state:
        st.session_state.comparison_result = None
    if "benchmark_result" not in st.session_state:
        st.session_state.benchmark_result = None


def render_header(title: str, subtitle: str, icon: str = "🥗"):
    """Render the standard branded header."""
    st.markdown(
        f"""
        <div class="main-header">
            <h1>{icon} {title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_sidebar_brand():
    """Render sidebar branding."""
    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div style="font-size: 2rem; margin-bottom: 4px;">🥗</div>
            <div class="sidebar-title">NutriGen AI</div>
            <div class="sidebar-subtitle">Personal Nutrition & Meal Planner</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.sidebar.caption("Powered by Generative AI")
    st.sidebar.markdown("---")

