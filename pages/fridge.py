"""
NutriGen AI - My Fridge Page (Phase 3)
Structured Ingredient Inventory Management System with unit tracking, category filtering,
expiry status calculation (Fresh / Expiring Soon / Expired), duplicate prevention, and editing.
"""

from datetime import date, timedelta
import streamlit as st
from utils.helpers import (
    render_header,
    load_css,
    init_session_state,
    get_default_user_profile,
    get_ingredient_status,
    get_expiry_countdown_text,
    get_expiring_ingredients,
    get_expired_ingredients,
    find_duplicate_ingredient,
    get_ingredient_context_summary,
    parse_expiry_date,
    ALLOWED_INGREDIENT_UNITS,
    ALLOWED_INGREDIENT_CATEGORIES
)

init_session_state()
load_css()

# Branded Header
render_header(
    title="My Fridge",
    subtitle="Keep track of ingredients you already have.",
    icon="🥕"
)

# User Profile Context Integration
user_prof = st.session_state.get("user_profile", get_default_user_profile())
if user_prof.get("name") or user_prof.get("weekly_budget"):
    diet_info = user_prof.get("dietary_preference", "Vegetarian")
    cuisine_info = user_prof.get("cuisine_preference", "Indian")
    budget_info = user_prof.get("weekly_budget", 500)
    st.markdown(
        f"""
        <div class="demo-banner">
            <span>👤</span>
            <span><b>Planning for:</b> {diet_info} • {cuisine_info} • ₹{budget_info}/week</span>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <div class="demo-banner">
            <span>💡</span>
            <span>Complete your preferences to enable personalized meal planning.</span>
        </div>
        """,
        unsafe_allow_html=True
    )

# Current inventory data
fridge_items = st.session_state.get("fridge_items", [])
expiring_items = get_expiring_ingredients(fridge_items)
expired_items = get_expired_ingredients(fridge_items)
distinct_categories = len(set([item.get("category", "Other") for item in fridge_items]))

# Top Dynamic Summary Metrics
st.markdown("### 📊 Inventory Summary")
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">📦</div>
            <div class="metric-title">Total Ingredients</div>
            <div class="metric-value">{len(fridge_items)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">⚠️</div>
            <div class="metric-title">Expiring Soon</div>
            <div class="metric-value" style="color: {'#d97706' if expiring_items else '#111827'};">{len(expiring_items)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">❌</div>
            <div class="metric-title">Expired Items</div>
            <div class="metric-value" style="color: {'#dc2626' if expired_items else '#111827'};">{len(expired_items)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">🏷️</div>
            <div class="metric-title">Categories</div>
            <div class="metric-value">{distinct_categories}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# Expiring Soon Section
st.markdown("### ⚠️ Expiring Soon")
if expiring_items:
    st.caption("Ingredients expiring today or within the next 3 days. Your meal plan and recipes will prioritize these items:")
    for exp_item in expiring_items:
        countdown_str = get_expiry_countdown_text(exp_item.get("expiry_date", ""))
        qty_display = f"{int(exp_item['quantity']) if float(exp_item['quantity']).is_integer() else exp_item['quantity']} {exp_item['unit']}"
        st.markdown(
            f"""
            <div class="expiring-alert-card">
                <b>⚠️ {exp_item['name']}</b> ({qty_display}) — <span style="font-weight: 600;">{countdown_str}</span> (Category: {exp_item.get('category', 'Other')})
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.success("✅ No ingredients are expiring soon. Your pantry is in good shape!")

# Expired Items Section (if any)
if expired_items:
    st.markdown("### ❌ Expired Ingredients")
    st.caption("These items have passed their expiry date. Review or discard them:")
    for exp_item in expired_items:
        c1, c2, c3 = st.columns([3, 1.5, 1])
        with c1:
            st.markdown(f"🚫 **{exp_item['name']}** ({exp_item['quantity']} {exp_item['unit']})")
        with c2:
            st.markdown(f"`Expired on {exp_item.get('expiry_date')}`")
        with c3:
            if st.button("🗑️ Discard", key=f"discard_{exp_item['id']}", use_container_width=True):
                st.session_state.fridge_items = [i for i in st.session_state.fridge_items if i["id"] != exp_item["id"]]
                st.toast(f"Discarded expired item: {exp_item['name']}")
                st.rerun()

st.markdown("---")

# Main Content Layout: Add Ingredient Form on Left, Inventory & Filter on Right
col_form, col_list = st.columns([1.2, 1.8], gap="large")

with col_form:
    st.markdown("### ➕ Add Ingredient")
    st.caption("Enter ingredient details to add to your digital fridge.")

    with st.form("add_ingredient_form", clear_on_submit=True):
        name_input = st.text_input("Ingredient Name", placeholder="e.g., Rice, Milk, Capsicum, Eggs")
        
        q_col1, q_col2 = st.columns([1.2, 1])
        with q_col1:
            quantity_input = st.number_input("Quantity", min_value=0.01, max_value=10000.0, value=1.0, step=0.5)
        with q_col2:
            unit_input = st.selectbox("Unit", options=ALLOWED_INGREDIENT_UNITS, index=0)
            
        cat_input = st.selectbox("Category", options=ALLOWED_INGREDIENT_CATEGORIES, index=0)
        expiry_input = st.date_input("Expiry Date", value=date.today() + timedelta(days=7))
        
        st.markdown("<br>", unsafe_allow_html=True)
        add_submitted = st.form_submit_button("➕ Add Ingredient", use_container_width=True, type="primary")

    if add_submitted:
        cleaned_name = name_input.strip()
        if not cleaned_name:
            st.error("❌ Ingredient name cannot be empty.")
        elif quantity_input <= 0:
            st.error("❌ Quantity must be greater than 0.")
        else:
            # Check duplicate (case-insensitive)
            duplicate = find_duplicate_ingredient(cleaned_name, unit_input, st.session_state.fridge_items)
            if duplicate:
                # Merge quantities
                duplicate["quantity"] = round(duplicate["quantity"] + float(quantity_input), 2)
                duplicate["expiry_date"] = str(expiry_input)
                duplicate["category"] = cat_input
                st.success(f"✅ Updated existing '{cleaned_name}': New total quantity is {duplicate['quantity']} {unit_input}.")
                st.rerun()
            else:
                # Create unique new ID
                new_id = f"ing_{len(st.session_state.fridge_items) + 1}_{int(date.today().strftime('%Y%m%d%H%M%S'))}"
                new_item = {
                    "id": new_id,
                    "name": cleaned_name,
                    "quantity": float(quantity_input),
                    "unit": unit_input,
                    "category": cat_input,
                    "expiry_date": str(expiry_input)
                }
                st.session_state.fridge_items.append(new_item)
                st.success(f"✅ {cleaned_name} added to your fridge.")
                st.rerun()

with col_list:
    st.markdown("### 📦 Available Ingredients")
    
    # Search and Filter Bar
    s_col1, s_col2 = st.columns([1.6, 1.2])
    with s_col1:
        search_query = st.text_input("🔍 Search ingredients", placeholder="Filter by name...").strip().lower()
    with s_col2:
        category_options = ["All"] + ALLOWED_INGREDIENT_CATEGORIES
        selected_category = st.selectbox("Filter Category", options=category_options)

    # Filter Items
    filtered_items = []
    for item in st.session_state.get("fridge_items", []):
        matches_search = (not search_query) or (search_query in item.get("name", "").lower())
        matches_cat = (selected_category == "All") or (item.get("category", "Other") == selected_category)
        if matches_search and matches_cat:
            filtered_items.append(item)

    st.caption(f"Showing **{len(filtered_items)}** of **{len(fridge_items)}** ingredients:")

    if not filtered_items:
        st.info("No matching ingredients found. Try adjusting your search query or category filter.")
    else:
        for item in filtered_items:
            status = get_ingredient_status(item.get("expiry_date", ""))
            badge_class = "badge-green" if status == "Fresh" else ("badge-orange" if status == "Expiring Soon" else "badge-red")
            
            with st.container(border=True):
                c_head1, c_head2 = st.columns([3, 1.2])
                with c_head1:
                    qty_str = f"{int(item['quantity']) if float(item['quantity']).is_integer() else item['quantity']} {item['unit']}"
                    st.markdown(f"**🥬 {item['name']}** — `{qty_str}`")
                    st.caption(f"Category: **{item.get('category', 'Other')}** • Expiry: `{item.get('expiry_date')}`")
                with c_head2:
                    st.markdown(f"<span class='badge {badge_class}'>{status}</span>", unsafe_allow_html=True)
                    countdown_text = get_expiry_countdown_text(item.get("expiry_date", ""))
                    st.caption(countdown_text)

                # Edit & Delete Action Row
                act_col1, act_col2 = st.columns([3, 1])
                with act_col1:
                    with st.expander(f"✏️ Edit {item['name']}", expanded=False):
                        with st.form(f"edit_form_{item['id']}", clear_on_submit=False):
                            edit_name = st.text_input("Name", value=item["name"], key=f"name_{item['id']}")
                            
                            eq_col1, eq_col2 = st.columns(2)
                            with eq_col1:
                                edit_qty = st.number_input("Quantity", min_value=0.01, max_value=10000.0, value=float(item["quantity"]), step=0.5, key=f"qty_{item['id']}")
                            with eq_col2:
                                unit_idx = ALLOWED_INGREDIENT_UNITS.index(item["unit"]) if item["unit"] in ALLOWED_INGREDIENT_UNITS else 0
                                edit_unit = st.selectbox("Unit", options=ALLOWED_INGREDIENT_UNITS, index=unit_idx, key=f"unit_{item['id']}")
                                
                            cat_idx = ALLOWED_INGREDIENT_CATEGORIES.index(item.get("category", "Other")) if item.get("category") in ALLOWED_INGREDIENT_CATEGORIES else 0
                            edit_cat = st.selectbox("Category", options=ALLOWED_INGREDIENT_CATEGORIES, index=cat_idx, key=f"cat_{item['id']}")
                            
                            current_exp_date = parse_expiry_date(item.get("expiry_date", date.today()))
                            edit_exp = st.date_input("Expiry Date", value=current_exp_date, key=f"exp_{item['id']}")
                            
                            save_edit = st.form_submit_button("💾 Save Changes", use_container_width=True)
                            
                        if save_edit:
                            if not edit_name.strip():
                                st.error("Name cannot be empty.")
                            elif edit_qty <= 0:
                                st.error("Quantity must be greater than 0.")
                            else:
                                item["name"] = edit_name.strip()
                                item["quantity"] = float(edit_qty)
                                item["unit"] = edit_unit
                                item["category"] = edit_cat
                                item["expiry_date"] = str(edit_exp)
                                st.success("✅ Ingredient updated.")
                                st.rerun()
                with act_col2:
                    if st.button("🗑️ Delete", key=f"del_{item['id']}", help=f"Remove {item['name']} from fridge", use_container_width=True):
                        st.session_state.fridge_items = [i for i in st.session_state.fridge_items if i["id"] != item["id"]]
                        st.success("✅ Ingredient removed.")
                        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# Fridge Context Summary
st.markdown("### 🧺 Current Ingredient Context")
st.caption("Your available ingredients are automatically considered when generating meal plans and recipes:")

with st.container(border=True):
    context_text = get_ingredient_context_summary(st.session_state.get("fridge_items", []))
    st.markdown(f"**You currently have:**\n\n`{context_text}`")
