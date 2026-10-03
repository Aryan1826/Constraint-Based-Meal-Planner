"""
NutriGen AI - Personal Nutrition & Meal Planner
Main entry point configuring page layout, global styling, session state, and navigation routing.
"""

import streamlit as st
from utils.helpers import render_sidebar_brand, init_session_state, load_css

# Configure global page settings
st.set_page_config(
    page_title="NutriGen AI — Personal Nutrition & Meal Planner",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State & Custom CSS
init_session_state()
load_css()

# Render Brand Header in Sidebar
render_sidebar_brand()

# Define Multi-page Navigation
pages = [
    st.Page("pages/dashboard.py", title="Dashboard", icon="🏠", default=True),
    st.Page("pages/preferences.py", title="My Preferences", icon="👤"),
    st.Page("pages/fridge.py", title="My Fridge", icon="🥕"),
    st.Page("pages/meal_planner.py", title="Meal Planner", icon="🍽️"),
    st.Page("pages/recipes.py", title="Recipes", icon="📖"),
    st.Page("pages/ai_assistant.py", title="AI Assistant", icon="🤖"),
]

nav = st.navigation(pages)

# Execute the routed page
nav.run()
