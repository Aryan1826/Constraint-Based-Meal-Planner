"""
NutriGen AI - Recipes Page (Phase 7)
Personalized AI Recipe Generation, Natural Language Recipe Modifications,
and AI Ingredient Substitution with Google Gemini alongside curated sample recipes.
"""

import streamlit as st
from utils.helpers import (
    render_header,
    load_css,
    init_session_state,
    get_default_user_profile
)
from utils.prompts import (
    build_recipe_prompt,
    build_modify_recipe_prompt,
    build_substitution_prompt
)
from services.gemini_service import generate_ai_response, is_gemini_configured

init_session_state()
load_css()

# Branded Header
render_header(
    title="AI Recipes",
    subtitle="Generate recipes from your meal plan or ingredients.",
    icon="📖"
)

profile = st.session_state.get("user_profile", get_default_user_profile())
fridge_items = st.session_state.get("fridge_items", [])

diet_name = profile.get("dietary_preference", "Vegetarian")
time_limit = profile.get("maximum_cooking_time", 30)
allergies_val = profile.get("allergies", [])
allergies_str = ", ".join(allergies_val) if allergies_val else "None"

# Profile Context Banner
st.markdown(
    f"""
    <div class="demo-banner">
        <span>🤖</span>
        <span><b>Active Profile Context:</b> {diet_name} • Max Time: <b>{time_limit} mins</b> • Skill: <b>{profile.get('cooking_skill', 'Beginner')}</b> • Allergies: <b>{allergies_str}</b></span>
    </div>
    """,
    unsafe_allow_html=True
)

# ==========================================
# Section 1: AI Recipe Generator & Modifications (Phase 6 & 7)
# ==========================================

st.markdown("### ✨ AI Recipe Generator")
st.caption("Select any meal to synthesize a step-by-step recipe tailored to your diet, cooking skill, and available pantry items:")

# Meal Options List
default_meal_options = [
    "Paneer Tomato Rice",
    "Vegetable Poha",
    "Dal Rice",
    "Vegetable Khichdi",
    "Aloo Roti",
    "Upma with Veggies",
    "Rajma Chawal",
    "Palak Paneer with Roti",
    "Moong Dal Chilla",
    "Vegetable Biryani",
    "Custom Meal (Enter name)..."
]

# Ensure currently selected meal from session state is valid
current_selected = st.session_state.get("selected_recipe_meal", "Paneer Tomato Rice")
current_idx = default_meal_options.index(current_selected) if current_selected in default_meal_options else 0

gen_col1, gen_col2 = st.columns([2.5, 1.2], gap="medium")
with gen_col1:
    selected_option = st.selectbox("Select a Meal to Cook", options=default_meal_options, index=current_idx)
    if selected_option == "Custom Meal (Enter name)...":
        meal_to_generate = st.text_input("Enter Custom Meal Name", placeholder="e.g., Mushroom Corn Stir Fry, Oats Chilla").strip()
    else:
        meal_to_generate = selected_option

with gen_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    generate_recipe_btn = st.button("✨ Generate Recipe", type="primary", use_container_width=True)

# Handle Recipe Generation
if generate_recipe_btn:
    if not meal_to_generate:
        st.warning("Please specify a meal name to generate.")
    else:
        st.session_state.selected_recipe_meal = meal_to_generate
        prompt = build_recipe_prompt(
            meal_name=meal_to_generate,
            user_profile=profile,
            fridge_items=fridge_items
        )
        with st.spinner(f"🤖 NutriGen AI is creating your personalized recipe for '{meal_to_generate}'..."):
            success, response_text = generate_ai_response(prompt)
            
        if success:
            st.session_state.generated_recipe = response_text
            st.toast(f"Recipe for '{meal_to_generate}' generated successfully!", icon="🍳")
            st.rerun()
        else:
            st.error(response_text)

# Display AI Generated Recipe (if available)
generated_recipe = st.session_state.get("generated_recipe")

if generated_recipe:
    st.markdown("---")
    st.markdown(
        f"""
        <div class="demo-banner" style="background-color: #ecfdf5; border-color: #a7f3d0; color: #065f46;">
            <span>🍳</span>
            <span><b>AI Generated Recipe:</b> Customized for {diet_name} cuisine within {time_limit} mins.</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Render AI Generated Recipe Markdown
    with st.container(border=True):
        st.markdown(generated_recipe)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Actions: Regenerate & Clear
    r_col1, r_col2 = st.columns([1, 1])
    with r_col1:
        if st.button("🔄 Regenerate Recipe", use_container_width=True, help="Ask Gemini to generate another variation of this recipe."):
            target_meal = st.session_state.get("selected_recipe_meal", "Paneer Tomato Rice")
            prompt = build_recipe_prompt(
                meal_name=target_meal,
                user_profile=profile,
                fridge_items=fridge_items
            )
            with st.spinner(f"🤖 Regenerating recipe for '{target_meal}'..."):
                success, response_text = generate_ai_response(prompt)
            if success:
                st.session_state.generated_recipe = response_text
                st.toast("Regenerated recipe variation!", icon="🔄")
                st.rerun()
            else:
                st.error(response_text)
                
    with r_col2:
        if st.button("🗑️ Clear Recipe", use_container_width=True):
            st.session_state.generated_recipe = None
            st.rerun()

    # Section: Recipe Modifications & Quick Actions
    st.markdown("#### ✏️ Quick Recipe Adjustments")
    st.caption("Apply quick natural-language adjustments or enter specific cooking instructions:")

    # Quick Action Chips
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    quick_mod_request = None
    
    with q_col1:
        if st.button("💰 Make Cheaper", use_container_width=True, help="Reduce ingredient cost using affordable staples."):
            quick_mod_request = "Modify this recipe to reduce its estimated ingredient cost while keeping it practical and nutritious."
    with q_col2:
        if st.button("⏱️ Make Faster", use_container_width=True, help="Shorten prep and cooking time to under 20 mins."):
            quick_mod_request = "Modify this recipe so that total preparation and cooking time is under 20 minutes with streamlined steps."
    with q_col3:
        if st.button("🌶️ Make Less Spicy", use_container_width=True, help="Make mild, kid-friendly, and reduce heat."):
            quick_mod_request = "Modify this recipe to make it mild, kid-friendly, and significantly less spicy."
    with q_col4:
        if st.button("🫒 Use Less Oil", use_container_width=True, help="Minimize oil and butter usage."):
            quick_mod_request = "Modify this recipe to minimize oil/butter usage, recommending light steaming or non-stick methods."

    # Handle Quick Modification Click
    if quick_mod_request:
        mod_prompt = build_modify_recipe_prompt(
            current_recipe=generated_recipe,
            user_request=quick_mod_request,
            user_profile=profile,
            fridge_items=fridge_items
        )
        with st.spinner(f"🤖 Applying quick modification: '{quick_mod_request}'..."):
            success, response_text = generate_ai_response(mod_prompt)
        if success:
            st.session_state.generated_recipe = response_text
            st.toast("Recipe updated with quick action!", icon="✨")
            st.rerun()
        else:
            st.error(response_text)

    # Custom Natural Language Modification Form
    with st.form("modify_recipe_form", clear_on_submit=True):
        recipe_mod_request = st.text_input(
            "Custom Modification Request",
            placeholder="e.g., Make it extra crispy, suitable for beginner, or replace dairy"
        )
        submit_recipe_mod = st.form_submit_button("✨ Modify Recipe", type="secondary", use_container_width=True)
        
    if submit_recipe_mod:
        if not recipe_mod_request.strip():
            st.warning("Please enter a modification request.")
        else:
            mod_prompt = build_modify_recipe_prompt(
                current_recipe=generated_recipe,
                user_request=recipe_mod_request.strip(),
                user_profile=profile,
                fridge_items=fridge_items
            )
            with st.spinner(f"🤖 Applying recipe adjustments: '{recipe_mod_request}'..."):
                success, response_text = generate_ai_response(mod_prompt)
            if success:
                st.session_state.generated_recipe = response_text
                st.toast("Recipe updated successfully!", icon="✅")
                st.rerun()
            else:
                st.error(response_text)

st.markdown("---")

# ==========================================
# Section 2: AI Ingredient Substitution (Phase 7)
# ==========================================

st.markdown("### 🔄 AI Ingredient Substitution")
st.caption(
    "Missing an ingredient or need an alternative? Ask Gemini for practical substitutes "
    "tailored to your dietary style, allergies, and available fridge stock:"
)

# Fridge stock summary notice for substitutions
if fridge_items:
    fridge_preview = " • ".join([f"{item['name']}" for item in fridge_items[:6]])
    st.markdown(
        f"""
        <div class="demo-banner" style="background-color: #f0fdf4; border-color: #bbf7d0; color: #166534;">
            <span>🧊</span>
            <span><b>Fridge Inventory Available for Substitutions:</b> {fridge_preview}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

sub_form_col1, sub_form_col2 = st.columns([1.5, 2], gap="medium")

with sub_form_col1:
    sub_ing_input = st.text_input(
        "Ingredient to Replace",
        value=st.session_state.get("substitution_ingredient", "Paneer"),
        placeholder="e.g., Paneer, Milk, Tomato, Egg, Ghee"
    ).strip()

with sub_form_col2:
    sub_reason_input = st.text_input(
        "Reason / Preference (Optional)",
        value=st.session_state.get("substitution_reason", "I don't have paneer"),
        placeholder="e.g., I don't have it at home / Want a cheaper option / High protein alternative"
    ).strip()

# Quick Suggestion Chips for Substitution
st.caption("Quick preset reasons:")
sq1, sq2, sq3, sq4 = st.columns(4)
with sq1:
    if st.button("🚫 Don't have it at home", use_container_width=True):
        st.session_state.substitution_reason = "I don't have this ingredient at home. Suggest what I can use instead from common staples."
        st.rerun()
with sq2:
    if st.button("💰 Cheaper alternative", use_container_width=True):
        st.session_state.substitution_reason = "Suggest a more economical, budget-friendly replacement for this ingredient."
        st.rerun()
with sq3:
    if st.button("💪 High protein substitute", use_container_width=True):
        st.session_state.substitution_reason = "Suggest a high-protein vegetarian/plant-based replacement with similar nutritional density."
        st.rerun()
with sq4:
    if st.button("🌱 Dairy-Free / Vegan", use_container_width=True):
        st.session_state.substitution_reason = "Suggest a 100% dairy-free and plant-based vegan substitute."
        st.rerun()

find_sub_btn = st.button("🔄 Find Substitute", type="primary", use_container_width=True)

if find_sub_btn:
    if not sub_ing_input:
        st.warning("Please enter an ingredient name to replace.")
    else:
        st.session_state.substitution_ingredient = sub_ing_input
        st.session_state.substitution_reason = sub_reason_input
        
        # Build Substitution Prompt
        sub_prompt = build_substitution_prompt(
            ingredient_to_replace=sub_ing_input,
            reason_or_request=sub_reason_input,
            current_recipe=generated_recipe,
            user_profile=profile,
            fridge_items=fridge_items
        )
        
        with st.spinner(f"🤖 Finding smart AI substitutions for '{sub_ing_input}' with Google Gemini..."):
            success, response_text = generate_ai_response(sub_prompt)
            
        if success:
            st.session_state.substitution_result = response_text
            st.toast(f"Found substitutes for '{sub_ing_input}'!", icon="🔄")
            st.rerun()
        else:
            st.error(response_text)

# Render AI Substitution Results (if available)
substitution_result = st.session_state.get("substitution_result")
if substitution_result:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(substitution_result)
        
    if st.button("🗑️ Clear Substitutions", use_container_width=True):
        st.session_state.substitution_result = None
        st.rerun()

st.markdown("---")

# ==========================================
# Section 3: Curated Sample Recipe Catalog
# ==========================================

st.markdown("### 📚 Curated Recipe Library")
st.caption("Browse curated quick-cook home recipes with ingredients and cooking instructions:")

recipes = st.session_state.get("recipes", [])

# Search / Filter Bar
col_search, col_diff = st.columns([2, 1])
with col_search:
    search_query = st.text_input("🔍 Search curated recipes by name or ingredient...", placeholder="e.g., Poha, Paneer, Rice")
with col_diff:
    diff_filter = st.selectbox("Filter by Difficulty", options=["All Levels", "Beginner", "Intermediate", "Advanced"])

# Filter logic
filtered_recipes = []
for r in recipes:
    matches_search = (not search_query) or (search_query.lower() in r["name"].lower()) or any(search_query.lower() in ing["name"].lower() for ing in r["ingredients"])
    matches_diff = (diff_filter == "All Levels") or (r["difficulty"] == diff_filter)
    if matches_search and matches_diff:
        filtered_recipes.append(r)

st.caption(f"Showing **{len(filtered_recipes)}** curated recipes:")

# Recipe Cards Grid
for r in filtered_recipes:
    with st.container(border=True):
        head_col1, head_col2 = st.columns([3, 1.5])
        
        with head_col1:
            st.markdown(f"#### 🍲 {r['name']}")
            st.caption(r["description"])
        
        with head_col2:
            st.markdown(f"**Prep:** ⏱️ `{r['prep_time']}` • **Cook:** 🔥 `{r['cook_time']}`")
            badge_class = "badge-green" if r["difficulty"] == "Beginner" else "badge-orange"
            st.markdown(f"<span class='badge {badge_class}'>{r['difficulty']}</span> <span class='badge badge-blue'>{r.get('calories', '')}</span>", unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Action Row: Expander & AI Generate Button
        c_exp, c_gen = st.columns([3, 1.2])
        with c_exp:
            with st.expander(f"📖 View Curated Steps for {r['name']}", expanded=False):
                ing_col, steps_col = st.columns([1.2, 1.8], gap="medium")
                with ing_col:
                    st.markdown("##### 🥕 Ingredients")
                    for ing in r["ingredients"]:
                        st.markdown(f"- **{ing['name']}**: `{ing['qty']}`")
                with steps_col:
                    st.markdown("##### 👩‍🍳 Preparation Steps")
                    for idx, step in enumerate(r["steps"], 1):
                        st.markdown(f"**{idx}.** {step}")
        with c_gen:
            if st.button(f"✨ AI Recipe", key=f"ai_gen_{r['id']}", help=f"Generate dynamic AI recipe with Gemini for {r['name']}", use_container_width=True):
                st.session_state.selected_recipe_meal = r["name"]
                prompt = build_recipe_prompt(
                    meal_name=r["name"],
                    user_profile=profile,
                    fridge_items=fridge_items
                )
                with st.spinner(f"🤖 Generating AI recipe for {r['name']}..."):
                    success, response_text = generate_ai_response(prompt)
                if success:
                    st.session_state.generated_recipe = response_text
                    st.toast(f"Generated AI recipe for {r['name']}!", icon="🍳")
                    st.rerun()
                else:
                    st.error(response_text)
