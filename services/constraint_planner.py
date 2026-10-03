"""
NutriGen AI - Constraint-Based Meal Planner Service & Prompt Chaining Orchestrator
Executes Problem 14 Prompt Chaining Pipeline:
Step 1: Normalize constraints & run input guardrails
Step 2: Generate candidate weekly plan with Google Gemini
Step 3: Run deterministic Python constraint validation
Step 4: If invalid, send violations back via repair prompt (up to 2 repair iterations)
Step 5: Consolidate grocery list across meals and pantry
Step 6: Maintain timestamped prompt audit trail from 11:00 AM onward
"""

import json
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import streamlit as st

from services.gemini_service import generate_ai_response, PRIMARY_MODEL, FALLBACK_MODEL
from utils.prompts import (
    build_meal_plan_prompt_v1,
    build_constraint_meal_plan_prompt_final,
    build_constraint_repair_prompt
)
from utils.constraint_validator import (
    validate_planner_inputs,
    check_off_topic_query,
    check_non_veg_intent,
    validate_meal_plan_constraints,
    consolidate_grocery_list
)


# ==========================================
# 1. JSON Extraction & Sanitization
# ==========================================

def extract_json_from_response(response_text: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Safely extract and parse JSON from model responses, handling code blocks,
    markdown fences, trailing commas, or preliminary thoughts.
    """
    if not response_text or not response_text.strip():
        return False, None, "Empty response received from model."

    cleaned = response_text.strip()

    # Pattern 1: Markdown codeblock ```json ... ```
    json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned, re.DOTALL)
    if json_block_match:
        cleaned = json_block_match.group(1).strip()
    else:
        # Pattern 2: First { to last }
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            cleaned = cleaned[first_brace:last_brace + 1].strip()

    # Attempt direct JSON parse
    try:
        data = json.loads(cleaned)
        return True, data, "JSON parsed successfully."
    except json.JSONDecodeError as direct_err:
        # Attempt heuristic repair for trailing commas
        repaired = re.sub(r',\s*([\]}])', r'\1', cleaned)
        try:
            data = json.loads(repaired)
            return True, data, "JSON parsed after trailing comma repair."
        except json.JSONDecodeError as rep_err:
            return False, None, f"Failed to parse model JSON: {str(direct_err)}"


# ==========================================
# 2. Timestamped Prompt History Audit Trail
# ==========================================

def log_prompt_history_event(
    step_name: str,
    prompt_version: str,
    prompt_text: str,
    model_name: str,
    raw_response: str,
    validation_result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Records an immutable timestamped event into st.session_state.prompt_history.
    Ensures complete traceability from 11:00 AM onward as required by hackathon guidelines.
    """
    # Initialize prompt history in session state if missing
    if "prompt_history" not in st.session_state:
        st.session_state.prompt_history = []

    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    event = {
        "id": f"evt_{len(st.session_state.prompt_history) + 1}",
        "timestamp": now_iso,
        "step_name": step_name,
        "prompt_version": prompt_version,
        "model": model_name,
        "prompt_preview": prompt_text[:200] + ("..." if len(prompt_text) > 200 else ""),
        "full_prompt": prompt_text,
        "response_preview": raw_response[:200] + ("..." if len(raw_response) > 200 else ""),
        "full_response": raw_response,
        "is_valid": validation_result.get("valid", False) if validation_result else False,
        "violations": validation_result.get("violations", []) if validation_result else [],
        "warnings": validation_result.get("warnings", []) if validation_result else [],
        "error": error_message
    }

    st.session_state.prompt_history.append(event)
    return event


# ==========================================
# 3. Prompt Chaining Execution Engine
# ==========================================

def run_constraint_meal_planner_chain(
    user_profile: Dict[str, Any],
    pantry_items: List[Dict[str, Any]],
    budget: float = 500.0,
    max_cook_time: int = 30,
    num_days: int = 7,
    reuse_target: float = 40.0,
    variety_level: str = "High",
    servings: int = 2,
    cuisine: Optional[str] = None,
    max_repair_attempts: int = 2,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """
    Full 7-Step Chained Constraint-Based Meal Planner Pipeline:
    1. Guardrails check
    2. Prompt Generation & Gemini Call
    3. JSON extraction
    4. Deterministic Python validation
    5. Repair Loop (if violations found)
    6. Grocery consolidation
    7. Structured Return
    """
    # ----------------------------------------------------
    # STEP 1: Guardrail Check on Inputs
    # ----------------------------------------------------
    is_valid_input, input_errors = validate_planner_inputs(
        budget=budget,
        max_cook_time=max_cook_time,
        num_days=num_days,
        reuse_target=reuse_target,
        diet=user_profile.get("dietary_preference", "Vegetarian")
    )
    if not is_valid_input:
        return {
            "success": False,
            "error_type": "INPUT_GUARDRAIL_VIOLATION",
            "message": "Input validation failed before calling model.",
            "violations": input_errors,
            "chain_steps": ["Step 1: Input guardrail blocked execution."]
        }

    # Check for adversarial non-vegetarian keywords in profile dislikes/allergies
    allergies = user_profile.get("allergies", [])
    dislikes = user_profile.get("foods_to_avoid", [])
    for text_val in allergies + dislikes:
        is_non_veg, reason = check_non_veg_intent(str(text_val))
        if is_non_veg:
            return {
                "success": False,
                "error_type": "ADVERSARIAL_NON_VEG_GUARDRAIL",
                "message": reason,
                "violations": [reason],
                "chain_steps": ["Step 1: Blocked non-vegetarian adversarial request."]
            }

    chain_steps = []
    repair_events = []

    # ----------------------------------------------------
    # STEP 2: Candidate Plan Generation (Technique 2: Self-Critique)
    # ----------------------------------------------------
    if progress_callback:
        progress_callback("Step 2/6: Synthesizing candidate plan with Gemini (Self-Critique)...")

    prompt = build_constraint_meal_plan_prompt_final(
        user_profile=user_profile,
        pantry_items=pantry_items,
        budget=budget,
        max_cook_time=max_cook_time,
        num_days=num_days,
        reuse_target=reuse_target,
        variety_level=variety_level,
        servings=servings,
        cuisine=cuisine
    )

    success, raw_response = generate_ai_response(prompt, model_name=PRIMARY_MODEL)

    if not success:
        log_prompt_history_event(
            step_name="Step 2: Initial Generation",
            prompt_version="FINAL_SYSTEM_PROMPT",
            prompt_text=prompt,
            model_name=PRIMARY_MODEL,
            raw_response=raw_response,
            error_message="Gemini API failure"
        )
        return {
            "success": False,
            "error_type": "API_FAILURE",
            "message": raw_response,
            "chain_steps": chain_steps
        }

    chain_steps.append("Step 2: Candidate weekly plan generated via Gemini 3.7 Flash.")

    # ----------------------------------------------------
    # STEP 3: Deterministic Python Constraint Validation
    # ----------------------------------------------------
    if progress_callback:
        progress_callback("Step 3/6: Running deterministic Python constraint validation...")

    json_ok, plan_data, parse_msg = extract_json_from_response(raw_response)
    
    if not json_ok or not plan_data:
        val_result = {
            "valid": False,
            "violations": [f"Malformed AI output: {parse_msg}"],
            "warnings": [],
            "format_ok": False,
            "metrics": {}
        }
    else:
        val_result = validate_meal_plan_constraints(
            plan_data=plan_data,
            budget_limit=budget,
            max_cook_time=max_cook_time,
            pantry_items=pantry_items,
            min_reuse_target=reuse_target,
            required_days=num_days,
            allergies=allergies,
            dislikes=dislikes
        )

    log_prompt_history_event(
        step_name="Step 3: Initial Validation",
        prompt_version="FINAL_SYSTEM_PROMPT",
        prompt_text=prompt,
        model_name=PRIMARY_MODEL,
        raw_response=raw_response,
        validation_result=val_result
    )

    chain_steps.append(f"Step 3: Python validation complete — Valid: {val_result['valid']}. Found {len(val_result['violations'])} violations.")

    # ----------------------------------------------------
    # STEP 4: Chained Repair Loop (Technique 1: Prompt Chaining)
    # ----------------------------------------------------
    attempt = 0
    active_json_str = raw_response

    while not val_result["valid"] and attempt < max_repair_attempts:
        attempt += 1
        msg = f"Step 4/6: Auto-Regenerating (Attempt {attempt}/{max_repair_attempts}) to resolve: {', '.join(val_result['violations'][:2])}..."
        if progress_callback:
            progress_callback(msg)

        repair_prompt = build_constraint_repair_prompt(
            candidate_json_str=active_json_str,
            violations=val_result["violations"],
            budget=budget,
            max_cook_time=max_cook_time
        )

        repair_success, repair_response = generate_ai_response(repair_prompt, model_name=PRIMARY_MODEL)

        if not repair_success:
            chain_steps.append(f"Repair attempt {attempt} failed API call.")
            break

        active_json_str = repair_response
        repair_json_ok, repaired_plan_data, rep_parse_msg = extract_json_from_response(repair_response)

        if repair_json_ok and repaired_plan_data:
            plan_data = repaired_plan_data
            val_result = validate_meal_plan_constraints(
                plan_data=plan_data,
                budget_limit=budget,
                max_cook_time=max_cook_time,
                pantry_items=pantry_items,
                min_reuse_target=reuse_target,
                required_days=num_days,
                allergies=allergies,
                dislikes=dislikes
            )
            repair_events.append({
                "attempt": attempt,
                "repaired": val_result["valid"],
                "remaining_violations": val_result["violations"]
            })
            log_prompt_history_event(
                step_name=f"Step 4: Chained Repair #{attempt}",
                prompt_version="CHAINED_REPAIR_PROMPT",
                prompt_text=repair_prompt,
                model_name=PRIMARY_MODEL,
                raw_response=repair_response,
                validation_result=val_result
            )
            chain_steps.append(f"Repair #{attempt}: Re-evaluated plan — Valid: {val_result['valid']}.")
            if val_result["valid"]:
                break
        else:
            chain_steps.append(f"Repair #{attempt}: Could not parse repaired JSON.")

    # ----------------------------------------------------
    # STEP 5: Consolidated Grocery Aggregation
    # ----------------------------------------------------
    if progress_callback:
        progress_callback("Step 5/6: Consolidating weekly grocery list across all meals and pantry...")

    if plan_data and "days" in plan_data:
        consolidated_grocery = consolidate_grocery_list(
            days_list=plan_data["days"],
            pantry_items=pantry_items
        )
    else:
        consolidated_grocery = {
            "pantry_items_used": [],
            "items_to_buy": [],
            "total_items_to_buy": 0,
            "total_pantry_items_used": 0,
            "estimated_total_grocery_cost": 0.0
        }

    # Re-verify grocery cost against budget
    grocery_cost = consolidated_grocery["estimated_total_grocery_cost"]
    grocery_budget_ok = grocery_cost <= budget
    if not grocery_budget_ok:
        val_result["warnings"].append(
            f"Consolidated grocery purchase estimate (₹{grocery_cost:.2f}) exceeds budget allocation (₹{budget:.2f})."
        )

    chain_steps.append("Step 5: Grocery list successfully consolidated.")

    # ----------------------------------------------------
    # STEP 6: Final Result Assembly
    # ----------------------------------------------------
    return {
        "success": True,
        "plan": plan_data,
        "raw_text": active_json_str,
        "validation": val_result,
        "consolidated_grocery": consolidated_grocery,
        "chain_steps": chain_steps,
        "repair_events": repair_events,
        "attempts_made": attempt + 1
    }


# ==========================================
# 4. Side-by-Side Prompt Comparison Runner (Phase 13)
# ==========================================

def run_prompt_comparison_v1_vs_final(
    user_profile: Dict[str, Any],
    pantry_items: List[Dict[str, Any]],
    budget: float = 500.0,
    max_cook_time: int = 30,
    num_days: int = 7
) -> Dict[str, Any]:
    """
    Runs both PROMPT V1 (baseline naive) and FINAL PROMPT (constraint-aware chained)
    on the EXACT SAME user inputs. Compares:
    - Output format validity
    - Hard constraint violations
    - Budget compliance
    - Cooking time compliance
    - Ingredient reuse rate
    """
    # 1. Run V1 Baseline
    v1_prompt = build_meal_plan_prompt_v1(
        user_profile=user_profile,
        budget=budget,
        max_cook_time=max_cook_time,
        num_days=num_days
    )
    v1_success, v1_raw = generate_ai_response(v1_prompt, model_name=PRIMARY_MODEL)

    v1_json_ok, v1_plan, _ = extract_json_from_response(v1_raw)
    if v1_json_ok and v1_plan:
        v1_val = validate_meal_plan_constraints(
            plan_data=v1_plan,
            budget_limit=budget,
            max_cook_time=max_cook_time,
            pantry_items=pantry_items,
            required_days=num_days
        )
    else:
        # V1 returns unformatted text; deterministic validator flags format failure
        v1_val = {
            "valid": False,
            "vegetarian_ok": True,
            "budget_ok": False,
            "cooking_time_ok": False,
            "ingredient_reuse_ok": False,
            "pantry_ok": False,
            "variety_ok": False,
            "nutrition_balance_ok": False,
            "format_ok": False,
            "violations": ["Format violation: V1 baseline did not return parseable structured JSON."],
            "warnings": ["Unstructured plain text response lacks schema validation."],
            "metrics": {
                "total_estimated_cost": 0.0,
                "ingredient_reuse_rate": 0.0,
                "pantry_utilization_rate": 0.0
            }
        }

    log_prompt_history_event(
        step_name="Side-by-Side: Prompt V1",
        prompt_version="PROMPT_V1_BASELINE",
        prompt_text=v1_prompt,
        model_name=PRIMARY_MODEL,
        raw_response=v1_raw,
        validation_result=v1_val
    )

    # 2. Run Final Chained Prompt
    final_result = run_constraint_meal_planner_chain(
        user_profile=user_profile,
        pantry_items=pantry_items,
        budget=budget,
        max_cook_time=max_cook_time,
        num_days=num_days
    )

    if "validation" not in final_result:
        final_result["validation"] = {
            "valid": False,
            "format_ok": False,
            "budget_ok": False,
            "cooking_time_ok": False,
            "ingredient_reuse_ok": False,
            "pantry_ok": False,
            "variety_ok": False,
            "nutrition_balance_ok": False,
            "violations": [final_result.get("message", "Model execution failed.")],
            "warnings": [],
            "metrics": {
                "total_estimated_cost": 0.0,
                "ingredient_reuse_rate": 0.0,
                "max_cooking_time_observed": 0
            }
        }

    return {
        "v1": {
            "prompt": v1_prompt,
            "raw_response": v1_raw,
            "validation": v1_val,
            "plan": v1_plan if v1_json_ok else None
        },
        "final": final_result
    }
