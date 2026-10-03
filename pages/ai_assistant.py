"""
NutriGen AI - Conversational AI Assistant Page (Phase 8)
Context-aware personal nutrition, cooking, and meal planning assistant powered by Google Gemini.
Integrates User Profile, Fridge Stock, Generated Meal Plan, and Active Recipe into reasoning.
"""

import streamlit as st
from utils.helpers import (
    render_header,
    load_css,
    init_session_state,
    get_default_user_profile,
    get_ingredient_context_summary
)
from utils.prompts import build_assistant_prompt
from services.gemini_service import generate_ai_response, is_gemini_configured

init_session_state()
load_css()

# Branded Header
render_header(
    title="AI Assistant",
    subtitle="Ask questions about your meals, recipes, and ingredients.",
    icon="🤖"
)

profile = st.session_state.get("user_profile", get_default_user_profile())
fridge_items = st.session_state.get("fridge_items", [])
generated_meal_plan = st.session_state.get("generated_meal_plan")
generated_recipe = st.session_state.get("generated_recipe")
selected_meal = st.session_state.get("selected_recipe_meal", "Paneer Tomato Rice")

# Gemini Connection Status Banner
gemini_ready = is_gemini_configured()

if gemini_ready:
    st.markdown(
        """
        <div class="demo-banner" style="background-color: #ecfdf5; border-color: #a7f3d0; color: #065f46;">
            <span>🟢</span>
            <span><b>AI Assistant is ready.</b> Contextual reasoning active using your preferences, fridge stock, and meal plan.</span>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <div class="demo-banner" style="background-color: #fffbeb; border-color: #fde68a; color: #92400e;">
            <span>🟡</span>
            <span><b>Gemini API key is not configured.</b> Add <code>GEMINI_API_KEY</code> to your <code>.env</code> file to enable live AI responses.</span>
        </div>
        """,
        unsafe_allow_html=True
    )

# Active Injected Context Summary Expander
with st.expander("🔍 View Context Used by AI Assistant", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**👤 User Profile:**")
        st.write(f"- Name: {profile.get('name', 'User')}")
        st.write(f"- Diet: {profile.get('dietary_preference', 'Vegetarian')}")
        st.write(f"- Cuisine: {profile.get('cuisine_preference', 'Indian')}")
        st.write(f"- Budget: ₹{profile.get('weekly_budget', 500)}/week")
        st.write(f"- Max Cooking Time: {profile.get('maximum_cooking_time', 30)} mins")
        allergies = profile.get('allergies', [])
        st.write(f"- Allergies: {', '.join(allergies) if allergies else 'None'}")
        avoids = profile.get('foods_to_avoid', [])
        st.write(f"- Foods to Avoid: {', '.join(avoids) if avoids else 'None'}")
        
    with c2:
        st.markdown("**🧊 Fridge Inventory:**")
        if fridge_items:
            st.write(get_ingredient_context_summary(fridge_items))
        else:
            st.write("No fridge ingredients added.")
            
        st.markdown("**🗓️ Meal Plan Status:**")
        if generated_meal_plan:
            st.write("✅ Active AI Meal Plan available in context.")
        else:
            st.write("ℹ️ No meal plan generated yet.")
            
        st.markdown("**🍳 Recipe Status:**")
        if generated_recipe:
            st.write(f"✅ Active AI Recipe for *{selected_meal}* available in context.")
        else:
            st.write("ℹ️ No recipe generated yet.")

# Example Suggestion Questions (Feature 4)
st.markdown("### 💡 Try Asking")
st.caption("Click any suggestion to quickly ask NutriGen AI:")

suggested_query = None

row1_col1, row1_col2, row1_col3 = st.columns(3)
with row1_col1:
    if st.button("🍲 What can I cook with my fridge stock?", use_container_width=True):
        suggested_query = "What can I cook right now with the ingredients in my fridge?"
with row1_col2:
    if st.button("🍽️ What should I make for dinner today?", use_container_width=True):
        suggested_query = "What should I make for dinner today based on my preferences and fridge stock?"
with row1_col3:
    if st.button("🔄 Can I replace paneer in my recipe?", use_container_width=True):
        suggested_query = "Can you suggest practical substitutes for paneer in my recipe using what I have?"

row2_col1, row2_col2, row2_col3 = st.columns(3)
with row2_col1:
    if st.button("💰 How can I make my meals cheaper?", use_container_width=True):
        suggested_query = "How can I reduce my weekly meal planning costs while staying healthy?"
with row2_col2:
    if st.button("⏱️ Which meal takes the least time?", use_container_width=True):
        suggested_query = "Which quick meal can I cook in under 15 minutes?"
with row2_col3:
    if st.button("🍛 Suggest a quick Indian dinner", use_container_width=True):
        suggested_query = "Suggest a quick and healthy Indian dinner suitable for my cooking skill."

st.markdown("---")

# Conversational Header & Clear Action
chat_head1, chat_head2 = st.columns([3, 1])
with chat_head1:
    st.markdown("### 💬 Conversation")
    st.caption("Your questions and answers during this session:")
with chat_head2:
    if st.button("🗑️ Clear Chat", use_container_width=True, help="Clear conversation history (keeps profile, fridge, and meal plan safe)."):
        st.session_state.chat_history = []
        st.session_state.chat_messages = []
        st.rerun()

# Ensure chat_history is in session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = st.session_state.chat_history

# Display Conversation History
for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(msg["content"])

# Process Prompt Execution Helper Function
def execute_query(query_text: str):
    if not query_text or not query_text.strip():
        return
    
    # 1. Append user message
    st.session_state.chat_history.append({"role": "user", "content": query_text.strip()})
    st.session_state.chat_messages = st.session_state.chat_history
    
    # 2. Build full context prompt
    prompt = build_assistant_prompt(
        user_question=query_text.strip(),
        user_profile=profile,
        fridge_items=fridge_items,
        current_meal_plan=generated_meal_plan,
        current_recipe=generated_recipe
    )
    
    # 3. Call Gemini
    with st.spinner("🤖 NutriGen AI is analyzing your nutrition context with Google Gemini..."):
        success, response_text = generate_ai_response(prompt)
    
    # 4. Append assistant response
    st.session_state.chat_history.append({"role": "assistant", "content": response_text})
    st.session_state.chat_messages = st.session_state.chat_history
    st.rerun()

# Handle Clicked Suggestion Query
if suggested_query:
    execute_query(suggested_query)

# Chat Input Field (Feature 1)
user_query = st.chat_input("Ask something about your meals, recipes, ingredients, or cooking preferences...")

if user_query:
    execute_query(user_query)

st.markdown("<br>", unsafe_allow_html=True)
st.caption(
    "⚠️ **Educational Project Notice:** NutriGen AI provides Generative AI culinary recommendations and approximate nutrition estimates. "
    "Consult qualified healthcare professionals or dietitians for clinical dietary advice."
)
