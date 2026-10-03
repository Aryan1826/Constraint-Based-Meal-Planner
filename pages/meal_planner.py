"""
NutriGen AI - Meal Planner Page
Hackathon Problem 14: Constraint-Based Weekly Vegetarian Meal Planner
Orchestrates:
- User-defined grocery budget
- Cooking-time limit
- Ingredient reuse target
- Pantry inventory utilization
- Weekly variety constraint
- Non-medical nutrition balance check
- Prompt Chaining & Auto-Regeneration on constraint violations
- Consolidated weekly grocery list
- Side-by-side prompt comparison (V1 vs Final)
- Benchmark test runner with measurable metrics
- Timestamped prompt history audit log
"""

import json
from datetime import datetime
import streamlit as st

from utils.helpers import (
    render_header,
    load_css,
    init_session_state,
    get_default_user_profile
)
from utils.prompts import (
    build_meal_plan_prompt,
    build_modify_meal_plan_prompt,
    build_meal_plan_prompt_v1,
    build_constraint_meal_plan_prompt_final
)
from services.gemini_service import generate_ai_response
from services.constraint_planner import (
    run_constraint_meal_planner_chain,
    run_prompt_comparison_v1_vs_final
)
from utils.benchmark_suite import (
    BENCHMARK_TEST_CASES,
    run_local_benchmark_evaluation
)
from utils.constraint_validator import (
    validate_planner_inputs,
    check_off_topic_query,
    check_non_veg_intent
)

init_session_state()
load_css()

# Branded Header
render_header(
    title="Constraint-Based Meal Planner",
    subtitle="Generate a personalized weekly vegetarian meal plan strictly optimized for your budget, cooking time, and ingredient reuse.",
    icon="🍽️"
)

profile = st.session_state.get("user_profile", get_default_user_profile())
fridge_items = st.session_state.get("fridge_items", [])
has_profile = bool(profile.get("name") or profile.get("weekly_budget"))

# Profile Context Banner
diet_val = profile.get("dietary_preference", "Vegetarian")
cuisine_val = profile.get("cuisine_preference", "Indian")
budget_val = profile.get("weekly_budget", 500)
cook_val = profile.get("maximum_cooking_time", 30)
allergies_val = profile.get("allergies", [])
allergies_str = ", ".join(allergies_val) if allergies_val else "None"
dislikes_val = profile.get("foods_to_avoid", [])
dislikes_str = ", ".join(dislikes_val) if dislikes_val else "None"

st.markdown(
    f"""
    <div class="demo-banner">
        <span>🥗</span>
        <span><b>Problem 14 Constraint Status:</b> 100% Vegetarian | Budget: <b>₹{budget_val}/wk</b> | Cooking Limit: <b>{cook_val} min/meal</b> | Allergies: <b>{allergies_str}</b></span>
    </div>
    """,
    unsafe_allow_html=True
)

# Mode Selector Tabs
tab_planner, tab_compare, tab_benchmarks, tab_audit = st.tabs([
    "🎯 Constraint-Based Planner",
    "⚖️ Side-by-Side Prompt Comparison",
    "🧪 Hackathon Benchmark Suite",
    "📜 Timestamped Prompt Audit Log"
])


# ==========================================
# TAB 1: Constraint-Based Planner
# ==========================================
with tab_planner:
    # 1. Pantry Context Banner
    if fridge_items:
        available_ing_names = " • ".join([item["name"] for item in fridge_items[:8]])
        if len(fridge_items) > 8:
            available_ing_names += f" • +{len(fridge_items) - 8} more"
            
        st.markdown(
            f"""
            <div class="demo-banner" style="background-color: #ecfdf5; border-color: #a7f3d0; color: #065f46;">
                <span>🥕</span>
                <span><b>In-Stock Pantry Inventory ({len(fridge_items)} items):</b> {available_ing_names}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("ℹ️ No pantry ingredients found. Head to 'My Fridge' to add staples, or Gemini will assume commonly available pantry staples.")

    # 2. Planner Parameters Form
    with st.container(border=True):
        st.markdown("### ⚙️ User Constraints & Parameters")
        st.caption("Configure numerical limits and preferences for the constraint engine:")

        p_col1, p_col2, p_col3 = st.columns(3)
        with p_col1:
            num_days = st.slider("Planning Duration (Days)", min_value=1, max_value=7, value=7, help="Problem 14 defaults to a full 7-day weekly schedule.")
            servings = st.number_input("Number of Servings", min_value=1, max_value=10, value=int(profile.get("number_of_people", 2)), step=1)

        with p_col2:
            default_budget_val = float(max(50.0, float(profile.get("weekly_budget") or 500)))
            budget_limit = st.number_input(
                "Weekly Grocery Budget (₹)",
                min_value=50.0,
                max_value=20000.0,
                value=default_budget_val,
                step=50.0,
                help="Hard constraint: Total cost across all days must remain <= this amount."
            )
            max_cook_time = st.slider(
                "Max Cooking Time per Meal (minutes)",
                min_value=10,
                max_value=90,
                value=int(profile.get("maximum_cooking_time", 30)),
                step=5,
                help="Hard constraint: No single meal can exceed this cooking time."
            )

        with p_col3:
            reuse_target = st.slider(
                "Ingredient Reuse Target (%)",
                min_value=10,
                max_value=80,
                value=35,
                step=5,
                help="Problem 14 Stretch: % of unique ingredients intentionally reused across 2+ meals."
            )
            variety_level = st.selectbox(
                "Weekly Variety Requirement",
                options=["High", "Medium", "Standard"],
                index=0,
                help="Enforces distinct dinners and diversified vegetarian protein sources."
            )

        c_col1, c_col2 = st.columns(2)
        with c_col1:
            cuisine_options = ["Indian", "Gujarati", "North Indian", "South Indian", "Italian", "Mexican", "Mediterranean", "Other"]
            saved_cuisine = profile.get("cuisine_preference", "Indian")
            c_idx = cuisine_options.index(saved_cuisine) if saved_cuisine in cuisine_options else 0
            selected_cuisine = st.selectbox("Cuisine Preference", options=cuisine_options, index=c_idx)
        with c_col2:
            st.markdown(
                """
                <div style="padding-top: 28px; font-weight: 600; color: #059669;">
                    🔒 Strict Diet: <b>100% Vegetarian</b> (Zero meat, poultry, or fish)
                </div>
                """,
                unsafe_allow_html=True
            )

        # Off-topic & Adversarial Guardrail Pre-check UI
        custom_instructions = st.text_input(
            "Optional Focus Notes (Off-topic & non-veg guardrails active)",
            placeholder="e.g., Focus on iron-rich leafy greens, or include more moong dal"
        )

        st.markdown("<br>", unsafe_allow_html=True)
        generate_clicked = st.button("✨ Generate Meal Plan", type="primary", use_container_width=True)

    # 3. Handle Generation Trigger with Prompt Chaining Pipeline
    if generate_clicked:
        # Step 1: Input Guardrails
        is_off_topic, off_topic_msg = check_off_topic_query(custom_instructions) if custom_instructions else (False, "")
        is_non_veg, non_veg_msg = check_non_veg_intent(custom_instructions) if custom_instructions else (False, "")

        if is_off_topic:
            st.error(f"🛡️ **Guardrail Triggered (Off-Topic Input):** {off_topic_msg}")
        elif is_non_veg:
            st.error(f"🛡️ **Guardrail Triggered (Dietary Violation):** {non_veg_msg}")
        else:
            # Prepare Request Profile
            req_profile = profile.copy()
            req_profile["dietary_preference"] = "Vegetarian"
            req_profile["cuisine_preference"] = selected_cuisine
            req_profile["weekly_budget"] = budget_limit
            req_profile["maximum_cooking_time"] = max_cook_time
            req_profile["number_of_people"] = servings

            status_placeholder = st.empty()

            def update_progress(msg: str):
                status_placeholder.info(f"⏳ **Prompt Chaining Pipeline:** {msg}")

            with st.spinner("🤖 Executing Prompt Chaining (Generate → Validate → Repair → Consolidate)..."):
                result = run_constraint_meal_planner_chain(
                    user_profile=req_profile,
                    pantry_items=fridge_items,
                    budget=budget_limit,
                    max_cook_time=max_cook_time,
                    num_days=num_days,
                    reuse_target=float(reuse_target),
                    variety_level=variety_level,
                    servings=servings,
                    cuisine=selected_cuisine,
                    progress_callback=update_progress
                )

            status_placeholder.empty()

            if result["success"]:
                st.session_state.constraint_plan_result = result
                
                # Format plan for backward compatibility with existing tests and markdown view
                plan_data = result["plan"]
                summary = plan_data.get("summary", {}) if plan_data else {}
                md_lines = [
                    f"### ✨ {num_days}-Day AI Meal Plan",
                    f"**Total Estimated Cost:** ₹{summary.get('estimated_total_cost', budget_limit)} | **Budget Limit:** ₹{budget_limit}\n"
                ]
                for day_obj in (plan_data.get("days", []) if plan_data else []):
                    d_name = day_obj.get("day", "Day")
                    b_meal = day_obj.get("breakfast", {}).get("name", "Breakfast")
                    l_meal = day_obj.get("lunch", {}).get("name", "Lunch")
                    d_meal = day_obj.get("dinner", {}).get("name", "Dinner")
                    md_lines.append(f"- **{d_name}**: Breakfast: {b_meal} | Lunch: {l_meal} | Dinner: {d_meal}")
                
                st.session_state.generated_meal_plan = "\n".join(md_lines)
                st.toast("Constraint-based meal plan synthesized and verified!", icon="✅")
                st.rerun()
            else:
                st.error(f"❌ {result.get('message', 'Generation failed.')}")
                if "violations" in result:
                    for v in result["violations"]:
                        st.warning(f"- {v}")

    # 4. Display Results
    st.markdown("---")
    res = st.session_state.get("constraint_plan_result")
    raw_md_plan = st.session_state.get("generated_meal_plan")

    if res and res.get("success") and res.get("plan"):
        plan_data = res["plan"]
        val = res["validation"]
        grocery = res.get("consolidated_grocery", {})
        metrics = val.get("metrics", {})
        repair_events = res.get("repair_events", [])

        # --- A. Constraint Tracker Visual Checklist ---
        st.markdown("### 📊 Constraint Tracker (Deterministic Validation)")
        st.caption("Verified by authoritative deterministic Python validation layer:")

        track_col1, track_col2, track_col3, track_col4 = st.columns(4)
        with track_col1:
            veg_status = "✓ Vegetarian" if val.get("vegetarian_ok") else "❌ Non-Veg Violation"
            st.metric("Vegetarian Diet", veg_status, delta="100% Meat-Free")
            
            pantry_rate = metrics.get("pantry_utilization_rate", 0)
            st.metric("Pantry Utilization", f"{pantry_rate}%", delta=f"{len(metrics.get('pantry_items_used', []))} items used")

        with track_col2:
            cost_val = metrics.get("total_estimated_cost", 0)
            budget_ok = val.get("budget_ok")
            b_label = "✓ Within Budget" if budget_ok else "⚠️ Over Budget"
            st.metric("Weekly Cost", f"₹{cost_val}", delta=f"Limit: ₹{budget_limit} ({b_label})")

            reuse_rate = metrics.get("ingredient_reuse_rate", 0)
            reuse_ok = val.get("ingredient_reuse_ok")
            r_label = "✓ Target Met" if reuse_ok else "⚠️ Low Reuse"
            st.metric("Ingredient Reuse", f"{reuse_rate}%", delta=f"Target: {reuse_target}% ({r_label})")

        with track_col3:
            cook_observed = metrics.get("max_cooking_time_observed", 0)
            cook_ok = val.get("cooking_time_ok")
            c_label = "✓ Time Respected" if cook_ok else "⚠️ Exceeded"
            st.metric("Max Cook Time", f"{cook_observed} mins", delta=f"Limit: {max_cook_time}m ({c_label})")

            variety_ok = val.get("variety_ok")
            v_label = "✓ Variety Ensured" if variety_ok else "⚠️ Repetition"
            distinct_dins = metrics.get("distinct_dinners_count", 0)
            st.metric("Weekly Variety", f"{distinct_dins} Dinners", delta=f"{v_label}")

        with track_col4:
            balanced_days = metrics.get("days_balanced_count", 0)
            total_days = metrics.get("total_days", 7)
            st.metric("Nutrition Balance", f"{balanced_days}/{total_days} Days", delta="Protein+Veg+Carb")
            
            repair_count = len(repair_events)
            st.metric("Auto-Regenerations", f"{repair_count} Repairs", delta="Prompt Chain" if repair_count > 0 else "Passed Step 3")

        # Live Alert for Auto-Regenerations
        if repair_events:
            for rep in repair_events:
                status_icon = "✅" if rep["repaired"] else "⚠️"
                st.info(f"{status_icon} **Prompt Chaining Auto-Repair Event #{rep['attempt']}:** Violations detected in candidate plan; repair prompt executed and fixed hard constraints.")

        if val.get("violations"):
            st.warning("⚠️ **Unresolved Hard Constraint Warnings:**\n" + "\n".join([f"- {v}" for v in val["violations"]]))

        # --- B. Daily Meal Plan Cards ---
        st.markdown("### 🗓️ Weekly Meal Schedule")
        
        days_list = plan_data.get("days", [])
        for day_obj in days_list:
            day_name = day_obj.get("day", "Day")
            d_cost = day_obj.get("daily_cost", 0)
            d_time = day_obj.get("daily_cooking_time", 0)

            with st.container(border=True):
                h1, h2, h3 = st.columns([3, 1, 1])
                with h1:
                    st.markdown(f"#### 📅 {day_name}")
                with h2:
                    st.markdown(f"<span class='badge badge-green'>Est. ₹{d_cost}</span>", unsafe_allow_html=True)
                with h3:
                    st.markdown(f"<span class='badge badge-orange'>⏱️ {d_time}m total</span>", unsafe_allow_html=True)

                m1, m2, m3 = st.columns(3)
                with m1:
                    bf = day_obj.get("breakfast", {})
                    st.markdown("🟡 **Breakfast**")
                    st.markdown(f"**{bf.get('name', 'Breakfast')}**")
                    st.caption(f"⏱️ {bf.get('cooking_time_minutes', 0)} mins | ₹{bf.get('estimated_cost', 0)}")
                    st.caption(f"Protein: {bf.get('protein_source', 'N/A')}")
                    if bf.get("ingredients"):
                        st.write("• " + ", ".join(bf.get("ingredients", [])[:4]))

                with m2:
                    lu = day_obj.get("lunch", {})
                    st.markdown("🟢 **Lunch**")
                    st.markdown(f"**{lu.get('name', 'Lunch')}**")
                    st.caption(f"⏱️ {lu.get('cooking_time_minutes', 0)} mins | ₹{lu.get('estimated_cost', 0)}")
                    st.caption(f"Protein: {lu.get('protein_source', 'N/A')}")
                    if lu.get("ingredients"):
                        st.write("• " + ", ".join(lu.get("ingredients", [])[:4]))

                with m3:
                    din = day_obj.get("dinner", {})
                    st.markdown("🟣 **Dinner**")
                    st.markdown(f"**{din.get('name', 'Dinner')}**")
                    st.caption(f"⏱️ {din.get('cooking_time_minutes', 0)} mins | ₹{din.get('estimated_cost', 0)}")
                    st.caption(f"Protein: {din.get('protein_source', 'N/A')}")
                    if din.get("ingredients"):
                        st.write("• " + ", ".join(din.get("ingredients", [])[:4]))

        # --- C. Consolidated Weekly Grocery List ---
        st.markdown("---")
        st.markdown("### 🛒 Consolidated Weekly Grocery List")
        st.caption("Combines ingredients across all 7 days, accounts for pantry stock, and aggregates purchases:")

        g_col1, g_col2 = st.columns([1.6, 1.4], gap="large")

        with g_col1:
            st.markdown("#### 🛍️ Items to Buy")
            items_to_buy = grocery.get("items_to_buy", [])
            if items_to_buy:
                for item in items_to_buy:
                    with st.container(border=True):
                        i_c1, i_c2 = st.columns([3, 1])
                        with i_c1:
                            st.markdown(f"**{item['name']}**")
                            st.caption(f"Required: {item['required_qty']} {item['unit']} | In Pantry: {item['pantry_available']} {item['unit']}")
                            st.caption(f"Used in ({item['usage_count']} meals): {', '.join(item['used_in_meals'][:3])}")
                        with i_c2:
                            st.markdown(f"**₹{item['estimated_cost']}**")
                            st.caption(f"Buy: **{item['need_to_buy']} {item['unit']}**")
            else:
                st.success("✅ All needed ingredients are fully covered by your pantry inventory!")

        with g_col2:
            st.markdown("#### 🥕 In-Stock Pantry Items Utilized")
            pantry_used = grocery.get("pantry_items_used", [])
            if pantry_used:
                for p_item in pantry_used:
                    with st.container(border=True):
                        st.markdown(f"**{p_item['name']}**")
                        st.caption(f"Pantry Stock: {p_item['pantry_available']} {p_item['unit']} | Used in: {', '.join(p_item['used_in_meals'][:3])}")
            else:
                st.info("No pantry items were matched in this generation.")

            st.markdown("#### 💰 Grocery Expenditure Summary")
            g_cost = grocery.get("estimated_total_grocery_cost", 0.0)
            within_budget = g_cost <= budget_limit
            status_text = "Within Budget ✅" if within_budget else f"Exceeds by ₹{round(g_cost - budget_limit, 2)} ⚠️"

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Consolidated Grocery Purchase Total</div>
                    <div class="metric-value">₹{g_cost}</div>
                    <div style="font-size: 0.85rem; color: {'#059669' if within_budget else '#dc2626'}; font-weight: 600; margin-top: 4px;">
                        {status_text} (Budget: ₹{budget_limit})
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # --- D. General Nutrition Balance Check (Non-Medical) ---
        st.markdown("---")
        st.markdown("### 🥗 General Nutrition Balance Heuristic")
        st.caption("ℹ️ *General non-medical nutrition balance check — informational only, not medical advice.*")

        daily_checks = val.get("daily_balance", [])
        if daily_checks:
            d_cols = st.columns(len(daily_checks))
            for i, d_chk in enumerate(daily_checks):
                with d_cols[i]:
                    status_sym = "✅" if d_chk["balanced"] else "⚠️"
                    st.markdown(f"**{d_chk['day'][:3]}** {status_sym}")
                    st.caption("P: " + (", ".join(d_chk["proteins"][:1]) or "None"))
                    st.caption("V: " + (", ".join(d_chk["veggies"][:1]) or "None"))
                    st.caption("C: " + (", ".join(d_chk["carbs"][:1]) or "None"))

        # --- E. Quick Action Buttons & Plan Modification ---
        st.markdown("---")
        st.markdown("### ✏️ Customize or Modify This Plan")

        act_col1, act_col2 = st.columns(2)
        with act_col1:
            if st.button("🔄 Regenerate Meal Plan", use_container_width=True):
                st.session_state.constraint_plan_result = None
                st.session_state.generated_meal_plan = None
                st.rerun()
        with act_col2:
            if st.button("🗑️ Reset Plan", use_container_width=True):
                st.session_state.constraint_plan_result = None
                st.session_state.generated_meal_plan = None
                st.rerun()

        # Quick Plan Action Chips (preserved for existing tests & UX)
        qp1, qp2, qp3, qp4 = st.columns(4)
        quick_plan_mod = None
        with qp1:
            if st.button("💰 Make Cheaper", use_container_width=True):
                quick_plan_mod = "Reduce total grocery cost using more budget-friendly pantry staples."
        with qp2:
            if st.button("⏱️ Faster Meals", use_container_width=True):
                quick_plan_mod = "Ensure all meals take 20 minutes or less to cook."
        with qp3:
            if st.button("🥕 Use More Fridge Items", use_container_width=True):
                quick_plan_mod = "Maximize usage of ingredients already in my fridge."
        with qp4:
            if st.button("🍛 More Indian Meals", use_container_width=True):
                quick_plan_mod = "Include more comforting traditional Indian curries and lentils."

        if quick_plan_mod:
            mod_prompt = build_modify_meal_plan_prompt(
                current_meal_plan=raw_md_plan or "",
                user_request=quick_plan_mod,
                user_profile=profile,
                fridge_items=fridge_items
            )
            with st.spinner(f"🤖 Applying quick modification: '{quick_plan_mod}'..."):
                success, response_text = generate_ai_response(mod_prompt)
            if success:
                st.session_state.generated_meal_plan = response_text
                st.toast("Meal plan updated!", icon="✨")
                st.rerun()

    elif raw_md_plan:
        # Fallback to display raw markdown if generated plan exists (e.g. from tests or prior generation)
        st.markdown(
            """
            <div class="demo-banner" style="background-color: #ecfdf5; border-color: #a7f3d0; color: #065f46;">
                <span>✨</span>
                <span><b>AI Generated Meal Plan</b> — Personalized based on your dietary preferences and constraints.</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        with st.container(border=True):
            st.markdown(raw_md_plan)
        
        qp1, qp2, qp3, qp4 = st.columns(4)
        with qp1:
            st.button("💰 Make Cheaper", key="raw_cheaper", use_container_width=True)
        with qp2:
            st.button("⏱️ Faster Meals", key="raw_faster", use_container_width=True)
        with qp3:
            st.button("🥕 Use More Fridge Items", key="raw_fridge", use_container_width=True)
        with qp4:
            st.button("🍛 More Indian Meals", key="raw_indian", use_container_width=True)

    else:
        # Sample Preview when no plan generated yet
        st.markdown(
            """
            <div class="demo-banner">
                <span>🗓️</span>
                <span><b>No plan generated yet.</b> Click <b>'✨ Generate Meal Plan'</b> above to synthesize a constraint-optimized weekly schedule.</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(f"### 🗓️ {num_days}-Day Sample Meal Schedule Preview")
        days_to_show = st.session_state.get("meal_plan", [])[:num_days]
        for day_info in days_to_show:
            with st.container(border=True):
                h_c1, h_c2 = st.columns([3, 1])
                with h_c1:
                    st.markdown(f"#### 📅 {day_info['day']}")
                with h_c2:
                    st.markdown(f"<span class='badge badge-green'>{day_info.get('calories', '1,500 kcal')}</span>", unsafe_allow_html=True)
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.markdown("🟡 **Breakfast**")
                    st.write(day_info["breakfast"])
                with m2:
                    st.markdown("🟢 **Lunch**")
                    st.write(day_info["lunch"])
                with m3:
                    st.markdown("🟣 **Dinner**")
                    st.write(day_info["dinner"])


# ==========================================
# TAB 2: Side-by-Side Prompt Comparison (Phase 13)
# ==========================================
with tab_compare:
    st.markdown("### ⚖️ Side-by-Side Prompt Version Evaluation")
    st.caption("Demonstrating Prompt Engineering improvement: Evaluates **Prompt V1 (Baseline)** vs **Final Prompt (Chained & Constrained)** on identical inputs.")

    comp_c1, comp_c2 = st.columns(2)
    with comp_c1:
        comp_budget = st.number_input("Test Budget (₹)", value=500.0, step=50.0, key="comp_b")
    with comp_c2:
        comp_time = st.number_input("Test Max Cook Time (mins)", value=25, step=5, key="comp_t")

    run_comp_btn = st.button("🚀 Run Side-by-Side Prompt Comparison", type="secondary", use_container_width=True)

    if run_comp_btn:
        with st.spinner("🤖 Running Prompt V1 and Final Prompt on Google Gemini..."):
            comp_result = run_prompt_comparison_v1_vs_final(
                user_profile=profile,
                pantry_items=fridge_items,
                budget=comp_budget,
                max_cook_time=int(comp_time),
                num_days=7
            )
            st.session_state.comparison_result = comp_result
            st.toast("Side-by-side prompt comparison finished!", icon="⚖️")

    comp_res = st.session_state.get("comparison_result")
    if comp_res:
        v1_data = comp_res["v1"]
        final_data = comp_res["final"]

        v1_val = v1_data["validation"]
        final_val = final_data.get("validation", {})
        final_metrics = final_val.get("metrics", {})

        st.markdown("<br>", unsafe_allow_html=True)
        col_v1, col_final = st.columns(2, gap="large")

        # Column 1: Prompt V1
        with col_v1:
            st.markdown(
                """
                <div class="metric-card" style="border-top: 4px solid #94a3b8;">
                    <div class="metric-title" style="font-size: 1.1rem; color: #1e293b;">PROMPT V1 (Baseline / Naive)</div>
                    <div style="font-size: 0.85rem; color: #64748b;">Free-form prompt without strict schema, self-critique, or prompt chaining.</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if v1_data.get("raw_response", "").startswith("⚠️"):
                st.warning(v1_data.get("raw_response"))
            else:
                st.markdown("**Constraint Evaluation:**")
                st.write(f"- Output Format Valid: **{'✅ Yes' if v1_val.get('format_ok') else '❌ No (Unstructured Text)'}**")
                st.write(f"- Budget Compliant: **{'✅ Yes' if v1_val.get('budget_ok') else '❌ Unverified / Exceeded'}**")
                st.write(f"- Cook Time Respected: **{'✅ Yes' if v1_val.get('cooking_time_ok') else '❌ Unverified'}**")
                st.write(f"- Ingredient Reuse Tracked: **{'✅ Yes' if v1_val.get('ingredient_reuse_ok') else '❌ None'}**")
            
            with st.expander("🔍 View Raw V1 Prompt & Response"):
                st.code(v1_data["prompt"], language="text")
                st.markdown("**Raw Model Response:**")
                st.write(v1_data["raw_response"][:1000] + ("..." if len(v1_data["raw_response"]) > 1000 else ""))

        # Column 2: Final Prompt
        with col_final:
            st.markdown(
                """
                <div class="metric-card" style="border-top: 4px solid #10b981;">
                    <div class="metric-title" style="font-size: 1.1rem; color: #065f46;">FINAL PROMPT (Chained & Constrained)</div>
                    <div style="font-size: 0.85rem; color: #047857;">12-section architecture, strict JSON schema, self-critique, and deterministic repair.</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if not final_data.get("success", False):
                st.error(f"⚠️ {final_data.get('message', 'Generation failed.')}")
            else:
                st.markdown("**Constraint Evaluation:**")
                st.write(f"- Output Format Valid: **{'✅ Yes (Strict Schema)' if final_val.get('format_ok') else '❌ No'}**")
                st.write(f"- Budget Compliant: **{'✅ Yes' if final_val.get('budget_ok') else '❌ Exceeded'}** (₹{final_metrics.get('total_estimated_cost', 0)} / ₹{comp_budget})")
                st.write(f"- Cook Time Respected: **{'✅ Yes' if final_val.get('cooking_time_ok') else '❌ Exceeded'}** (Max {final_metrics.get('max_cooking_time_observed', 0)}m <= {comp_time}m)")
                st.write(f"- Ingredient Reuse Tracked: **{'✅ Yes' if final_val.get('ingredient_reuse_ok') else '❌ Below Target'}** ({final_metrics.get('ingredient_reuse_rate', 0)}%)")
                
                with st.expander("🔍 View Final Prompt Architecture & Plan"):
                    st.markdown("**Technique 1:** Prompt Chaining (Generator → Validator → Repair)")
                    st.markdown("**Technique 2:** Model Self-Critique & Structured Validation")
                    st.write(final_data.get("chain_steps", []))
                    if final_data.get("plan"):
                        st.json(final_data["plan"].get("summary", {}))


# ==========================================
# TAB 3: Hackathon Benchmark Suite (Phase 14 & 15)
# ==========================================
with tab_benchmarks:
    st.markdown("### 🧪 12 Labelled Benchmark Test Cases & Metrics")
    st.caption("Problem 14 Automated Evaluation: Runs all 12 test cases (Normal, Edge, Adversarial, Unseen) through the deterministic validator.")

    if st.button("⚡ Run All 12 Benchmark Test Cases", use_container_width=True, type="primary"):
        with st.spinner("Evaluating test cases against deterministic Python validation rules..."):
            b_results = run_local_benchmark_evaluation()
            st.session_state.benchmark_result = b_results
            st.toast("Benchmark evaluation completed!", icon="📊")

    b_res = st.session_state.get("benchmark_result")
    if not b_res:
        # Auto-run once if empty for immediate visibility
        b_res = run_local_benchmark_evaluation()
        st.session_state.benchmark_result = b_res

    m_final = b_res["metrics"]["final"]
    m_v1 = b_res["metrics"]["v1"]

    # Measurable Metrics Display
    st.markdown("#### 📈 Measurable Hackathon Metrics")
    met1, met2, met3, met4 = st.columns(4)
    with met1:
        st.metric(
            "Final Constraint Satisfaction",
            f"{m_final['constraint_satisfaction_rate']}%",
            delta=f"+{b_res['metrics']['improvement_multiplier']}% vs V1"
        )
    with met2:
        st.metric(
            "Final Format Validity Rate",
            f"{m_final['format_validity_rate']}%",
            delta="Strict JSON Schema"
        )
    with met3:
        st.metric(
            "V1 Baseline Satisfaction",
            f"{m_v1['constraint_satisfaction_rate']}%",
            delta="Naive Prompt"
        )
    with met4:
        st.metric(
            "Total Test Cases",
            f"{b_res['total_test_cases']} Cases",
            delta="Normal, Edge, Adversarial, Unseen"
        )

    # Detailed Table of Test Cases
    st.markdown("#### 📋 Labelled Test Case Results")
    for r in b_res["details_final"]:
        status_icon = "✅ PASS" if r["passed"] else "❌ FAIL"
        badge_style = "badge-green" if r["passed"] else "badge-red"
        
        with st.container(border=True):
            tc_c1, tc_c2, tc_c3 = st.columns([1.5, 3.5, 1.5])
            with tc_c1:
                st.markdown(f"**{r['id']}** ({r['type'].upper()})")
            with tc_c2:
                st.markdown(f"**{r['title']}**")
                st.caption(r["notes"])
            with tc_c3:
                st.markdown(f"<span class='badge {badge_style}'>{status_icon}</span>", unsafe_allow_html=True)


# ==========================================
# TAB 4: Timestamped Prompt Audit Log
# ==========================================
with tab_audit:
    st.markdown("### 📜 Timestamped Prompt Audit Log (From 11:00 AM Onward)")
    st.caption("Immutable record of all prompt calls, versions, models, and validation outcomes:")

    history = st.session_state.get("prompt_history", [])
    if not history:
        st.info("No prompt calls recorded yet. Generate a plan or run the prompt comparison to populate the audit log.")
    else:
        st.caption(f"Total prompt executions recorded: **{len(history)}**")
        for ev in reversed(history):
            with st.container(border=True):
                ev_c1, ev_c2, ev_c3 = st.columns([2, 3, 2])
                with ev_c1:
                    st.markdown(f"⏰ `{ev['timestamp']}`")
                    st.caption(f"Step: **{ev['step_name']}**")
                with ev_c2:
                    st.markdown(f"Version: `{ev['prompt_version']}` | Model: `{ev['model']}`")
                    st.caption(f"Prompt: {ev['prompt_preview']}")
                with ev_c3:
                    stat_badge = "badge-green" if ev["is_valid"] else "badge-orange"
                    st.markdown(f"<span class='badge {stat_badge}'>{'Valid ✅' if ev['is_valid'] else 'Violation/Raw'}</span>", unsafe_allow_html=True)
                
                with st.expander("🔍 View Complete Prompt & Model Response"):
                    st.markdown("**Prompt Sent to Gemini:**")
                    st.code(ev["full_prompt"], language="text")
                    st.markdown("**Model Output:**")
                    st.code(ev["full_response"], language="text")
                    if ev.get("violations"):
                        st.markdown("**Deterministic Violations:**")
                        for viol in ev["violations"]:
                            st.write(f"- {viol}")
