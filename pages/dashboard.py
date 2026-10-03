"""
NutriGen AI - Dashboard Page
Overview of weekly nutrition, planned meals, budget, and quick actions.
"""

import streamlit as st
from utils.helpers import render_header, load_css, init_session_state, get_default_user_profile

init_session_state()
load_css()

# Branded Header
render_header(
    title="Welcome to NutriGen AI",
    subtitle="Plan smarter meals using your preferences, budget, and available ingredients.",
    icon="🥗"
)

profile = st.session_state.get("user_profile", get_default_user_profile())
user_name = profile.get("name", "").strip()
diet_pref = profile.get("dietary_preference", "Vegetarian")
weekly_budget = profile.get("weekly_budget", 500)
fridge_count = len(st.session_state.get("fridge_items", []))
has_ai_plan = bool(st.session_state.get("generated_meal_plan"))

# Welcome Greeting Banner
if user_name:
    st.markdown(
        f"""
        <div class="demo-banner">
            <span>👋</span>
            <span><b>Welcome back, {user_name}!</b> Your profile is set to <b>{diet_pref}</b> with a weekly budget of <b>₹{weekly_budget}</b>.</span>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <div class="demo-banner">
            <span>💡</span>
            <span>Set your diet, budget, and cooking preferences in <b>My Preferences</b> to get started.</span>
        </div>
        """,
        unsafe_allow_html=True
    )

# Summary Cards Grid
st.markdown("### 📊 Overview & Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">🥗</div>
            <div class="metric-title">Diet Style</div>
            <div class="metric-value" style="font-size: 1.35rem; padding-top: 4px;">{diet_pref}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">🥕</div>
            <div class="metric-title">Fridge Stock</div>
            <div class="metric-value">{fridge_count} <span style="font-size: 1rem; font-weight: normal; color: #6b7280;">items</span></div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">💰</div>
            <div class="metric-title">Weekly Budget</div>
            <div class="metric-value">₹{weekly_budget}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col4:
    plan_status_text = "✨ Active AI Plan" if has_ai_plan else "Sample Plan"
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">🍽️</div>
            <div class="metric-title">Meal Plan</div>
            <div class="metric-value" style="font-size: 1.25rem; padding-top: 4px;">{plan_status_text}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# Two-column layout for Today's Meal Plan & Quick Navigation
left_col, right_col = st.columns([1.6, 1.2], gap="large")

with left_col:
    st.markdown("### 📅 Today's Meal Schedule")
    st.caption("Customized meals based on your diet preferences and available ingredients:")

    # Breakfast Card
    with st.container(border=True):
        b_col1, b_col2 = st.columns([3, 1])
        with b_col1:
            st.markdown("🟡 **Breakfast**")
            st.markdown("#### Vegetable Poha")
            st.caption("⏱️ 15 mins • 280 kcal • Light & Nutritious")
        with b_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("View Recipe", key="view_breakfast", use_container_width=True):
                st.info("Vegetable Poha: Flattened rice sautéed with mustard seeds, turmeric, onions, potatoes, and lemon.")

    # Lunch Card
    with st.container(border=True):
        l_col1, l_col2 = st.columns([3, 1])
        with l_col1:
            st.markdown("🟢 **Lunch**")
            st.markdown("#### Dal Rice")
            st.caption("⏱️ 25 mins • 350 kcal • High Protein Comfort Meal")
        with l_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("View Recipe", key="view_lunch", use_container_width=True):
                st.info("Dal Rice: Yellow toor dal tempered with cumin, garlic, and ghee served with steamed rice.")

    # Dinner Card
    with st.container(border=True):
        d_col1, d_col2 = st.columns([3, 1])
        with d_col1:
            st.markdown("🟣 **Dinner**")
            st.markdown("#### Paneer Vegetable Curry")
            st.caption("⏱️ 30 mins • 410 kcal • Rich Protein & Fiber")
        with d_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("View Recipe", key="view_dinner", use_container_width=True):
                st.info("Paneer Vegetable Curry: Soft cottage cheese and garden veggies in a mildly spiced tomato gravy.")

with right_col:
    st.markdown("### ⚡ Quick Navigation")
    st.caption("Direct links to all core features:")
    
    with st.container(border=True):
        st.markdown("**1. Preferences & Dietary Profile**")
        if st.button("Set Your Preferences →", key="qa_nav_pref", use_container_width=True):
            st.switch_page("pages/preferences.py")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**2. Pantry & Available Stock**")
        if st.button("Manage Your Fridge →", key="qa_nav_fridge", use_container_width=True):
            st.switch_page("pages/fridge.py")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**3. AI Meal Planning**")
        if st.button("Create Meal Plan →", key="qa_nav_plan", use_container_width=True):
            st.switch_page("pages/meal_planner.py")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**4. AI Recipes & Substitutions**")
        if st.button("Explore Recipes →", key="qa_nav_recipes", use_container_width=True):
            st.switch_page("pages/recipes.py")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**5. Conversational Nutritionist**")
        if st.button("Ask AI Assistant →", key="qa_nav_assistant", use_container_width=True):
            st.switch_page("pages/ai_assistant.py")

