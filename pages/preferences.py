"""
NutriGen AI - My Preferences Page (Phase 2)
Provides structured User Profile and Preference Management with input validation,
comma-separated restriction parsing, session-based persistence, and profile summary.
"""

import streamlit as st
from utils.helpers import (
    render_header,
    load_css,
    init_session_state,
    parse_comma_separated_items,
    validate_user_profile,
    get_default_user_profile
)

init_session_state()
load_css()

# Branded Header
render_header(
    title="Your Preferences",
    subtitle="Tell us about your diet, budget, and cooking preferences.",
    icon="👤"
)

current_profile = st.session_state.get("user_profile", get_default_user_profile())

# Two-column layout: Configuration Form on Left, Live Profile Summary on Right
col_form, col_summary = st.columns([1.6, 1.2], gap="large")

with col_form:
    st.markdown("### 📝 Profile Configuration")
    
    # Pre-compute form defaults from session profile
    default_name = current_profile.get("name", "")
    default_age = current_profile.get("age", 21)
    if default_age is None or default_age == "":
        default_age = 21
        
    default_people = int(current_profile.get("number_of_people", 2))
    
    diet_options = ["Vegetarian", "Vegan", "Non-Vegetarian", "Jain", "Eggetarian", "Other"]
    saved_diet = current_profile.get("dietary_preference", "Vegetarian")
    diet_idx = diet_options.index(saved_diet) if saved_diet in diet_options else 0
    
    cuisine_options = ["Indian", "Gujarati", "North Indian", "South Indian", "Chinese", "Italian", "Mexican", "Mediterranean", "Other"]
    saved_cuisine = current_profile.get("cuisine_preference", "Indian")
    cuisine_idx = cuisine_options.index(saved_cuisine) if saved_cuisine in cuisine_options else 0
    
    default_budget = float(current_profile.get("weekly_budget", 500))
    default_cook_time = int(current_profile.get("maximum_cooking_time", 30))
    
    skill_options = ["Beginner", "Intermediate", "Advanced"]
    saved_skill = current_profile.get("cooking_skill", "Intermediate")
    skill_idx = skill_options.index(saved_skill) if saved_skill in skill_options else 1
    
    # Format allergies and foods_to_avoid for text areas
    allergies_list = current_profile.get("allergies", [])
    allergies_str = ", ".join(allergies_list) if isinstance(allergies_list, list) else str(allergies_list)
    
    avoid_list = current_profile.get("foods_to_avoid", [])
    avoid_str = ", ".join(avoid_list) if isinstance(avoid_list, list) else str(avoid_list)

    with st.form("user_preferences_form", clear_on_submit=False):
        # Section A: Personal Information
        st.markdown("#### Section A — Personal Information")
        p_c1, p_c2, p_c3 = st.columns(3)
        with p_c1:
            name_input = st.text_input("Name", value=default_name, placeholder="e.g., Aryan")
        with p_c2:
            age_input = st.number_input("Age (optional)", min_value=1, max_value=120, value=int(default_age), step=1)
        with p_c3:
            people_input = st.number_input("Number of People", min_value=1, max_value=20, value=default_people, step=1)

        st.markdown("---")
        # Section B: Dietary Preferences
        st.markdown("#### Section B — Dietary Preferences")
        diet_input = st.selectbox("Primary Dietary Style", options=diet_options, index=diet_idx)

        st.markdown("---")
        # Section C: Cuisine Preference
        st.markdown("#### Section C — Cuisine Preference")
        cuisine_input = st.selectbox("Preferred Cuisine", options=cuisine_options, index=cuisine_idx)

        st.markdown("---")
        # Section D: Weekly Budget
        st.markdown("#### Section D — Weekly Budget")
        budget_input = st.number_input(
            "Weekly Food Budget (₹)",
            min_value=0.0,
            max_value=100000.0,
            value=default_budget,
            step=50.0,
            help="Weekly target maximum expenditure for food and ingredients"
        )

        st.markdown("---")
        # Section E: Cooking Preferences
        st.markdown("#### Section E — Cooking Preferences")
        cook_c1, cook_c2 = st.columns(2)
        with cook_c1:
            cook_time_input = st.slider(
                "Maximum Cooking Time per Meal (minutes)",
                min_value=10,
                max_value=120,
                value=default_cook_time,
                step=5
            )
        with cook_c2:
            skill_input = st.selectbox("Cooking Skill Level", options=skill_options, index=skill_idx)

        st.markdown("---")
        # Section F: Food Restrictions
        st.markdown("#### Section F — Food Restrictions & Allergies")
        allergies_input = st.text_input(
            "Allergies (comma-separated)",
            value=allergies_str,
            placeholder="e.g., Peanuts, Shellfish, Gluten"
        )
        foods_to_avoid_input = st.text_area(
            "Foods to Avoid / Dislikes (comma-separated)",
            value=avoid_str,
            placeholder="e.g., Mushrooms, Very spicy food, Excess oil"
        )

        st.markdown("<br>", unsafe_allow_html=True)
        btn_label = "💾 Update Preferences" if current_profile.get("name") else "💾 Save Preferences"
        save_submitted = st.form_submit_button(btn_label, use_container_width=True, type="primary")

    if save_submitted:
        # Construct candidate profile
        cleaned_name = name_input.strip()
        parsed_allergies = parse_comma_separated_items(allergies_input)
        parsed_avoid = parse_comma_separated_items(foods_to_avoid_input)
        
        candidate_data = {
            "name": cleaned_name,
            "age": int(age_input) if age_input else None,
            "number_of_people": int(people_input),
            "dietary_preference": diet_input,
            "cuisine_preference": cuisine_input,
            "weekly_budget": float(budget_input),
            "maximum_cooking_time": int(cook_time_input),
            "cooking_skill": skill_input,
            "allergies": parsed_allergies,
            "foods_to_avoid": parsed_avoid
        }

        is_valid, validation_errors = validate_user_profile(candidate_data)

        if not is_valid:
            for err in validation_errors:
                st.error(f"❌ {err}")
            st.warning("Please correct the validation errors above before saving.")
        else:
            # Commit to session state
            st.session_state.user_profile = candidate_data
            
            # Synchronize backward-compatible preferences dict
            st.session_state.preferences = {
                "name": candidate_data["name"],
                "age": candidate_data["age"],
                "people_count": candidate_data["number_of_people"],
                "diet": candidate_data["dietary_preference"],
                "cuisine": candidate_data["cuisine_preference"],
                "budget": candidate_data["weekly_budget"],
                "max_cooking_time": candidate_data["maximum_cooking_time"],
                "cooking_skill": candidate_data["cooking_skill"],
                "allergies": ", ".join(candidate_data["allergies"]),
                "foods_to_avoid": ", ".join(candidate_data["foods_to_avoid"])
            }
            st.success("✅ Preferences saved successfully!")
            st.rerun()

    # Reset / Clear Profile Action
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Reset to Defaults", use_container_width=True, help="Reset profile back to default template without altering fridge inventory."):
        st.session_state.user_profile = {
            "name": "",
            "age": None,
            "number_of_people": 1,
            "dietary_preference": "Vegetarian",
            "cuisine_preference": "Indian",
            "weekly_budget": 500,
            "maximum_cooking_time": 30,
            "cooking_skill": "Beginner",
            "allergies": [],
            "foods_to_avoid": []
        }
        st.session_state.preferences = {
            "name": "",
            "age": None,
            "people_count": 1,
            "diet": "Vegetarian",
            "cuisine": "Indian",
            "budget": 500,
            "max_cooking_time": 30,
            "cooking_skill": "Beginner",
            "allergies": "",
            "foods_to_avoid": ""
        }
        st.info("🔄 Preferences have been reset to empty defaults.")
        st.rerun()

with col_summary:
    st.markdown("### 📋 Active Profile Summary")
    
    prof = st.session_state.get("user_profile", get_default_user_profile())
    has_profile = bool(prof.get("name") or prof.get("weekly_budget"))
    
    if has_profile:
        with st.container(border=True):
            st.markdown("#### 👤 Current User Profile")
            st.markdown(f"**Name:** {prof.get('name') if prof.get('name') else '*(Not set)*'}")
            if prof.get("age"):
                st.markdown(f"**Age:** {prof.get('age')} years")
            st.markdown(f"**Household:** {prof.get('number_of_people', 1)} person(s)")
            st.markdown(f"**Diet Style:** <span class='badge badge-green'>{prof.get('dietary_preference', 'Vegetarian')}</span>", unsafe_allow_html=True)
            st.markdown(f"**Cuisine:** <span class='badge badge-blue'>{prof.get('cuisine_preference', 'Indian')}</span>", unsafe_allow_html=True)
            st.markdown(f"**Weekly Budget:** `₹{prof.get('weekly_budget', 500)}`")
            st.markdown(f"**Max Cooking Time:** `⏱️ {prof.get('maximum_cooking_time', 30)} mins`")
            st.markdown(f"**Cooking Skill:** <span class='badge badge-purple'>{prof.get('cooking_skill', 'Intermediate')}</span>", unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("##### ⚠️ Allergies & Restrictions")
            allergies = prof.get("allergies", [])
            if allergies:
                allergy_badges = "".join([f"<span class='badge badge-red'>{a}</span>" for a in allergies])
                st.markdown(f"**Allergies:**<br>{allergy_badges}", unsafe_allow_html=True)
            else:
                st.caption("No allergies recorded.")
                
            st.markdown("<br>", unsafe_allow_html=True)
            avoids = prof.get("foods_to_avoid", [])
            if avoids:
                avoid_badges = "".join([f"<span class='badge badge-orange'>{a}</span>" for a in avoids])
                st.markdown(f"**Foods to Avoid:**<br>{avoid_badges}", unsafe_allow_html=True)
            else:
                st.caption("No food dislikes recorded.")
    else:
        st.info("No active profile configured. Fill in the form on the left to save your preferences.")
