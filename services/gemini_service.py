"""
NutriGen AI - Google Gemini Generative AI Service
Simple, reusable service layer to configure Gemini client with google-genai,
build requests, handle 503 high demand retries with backoff & fallback, and generate responses.
"""

import os
import time
from typing import Tuple, Optional
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Primary and Fallback model definitions
PRIMARY_MODEL = "gemini-3.7-flash"
FALLBACK_MODEL = "gemini-3.6-flash"
FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash"]


def get_gemini_api_key() -> Optional[str]:
    """
    Retrieve Gemini API key from environment variable or Streamlit secrets.
    Never exposes or logs the key.
    """
    # 1. Check OS environment (.env)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key and api_key != "your_api_key_here":
        return api_key

    # 2. Check Streamlit secrets if available
    try:
        if "GEMINI_API_KEY" in st.secrets:
            secret_key = str(st.secrets["GEMINI_API_KEY"]).strip()
            if secret_key and secret_key != "your_api_key_here":
                return secret_key
    except Exception:
        pass

    return None


def is_gemini_configured() -> bool:
    """Return True if a valid Gemini API key is configured."""
    key = get_gemini_api_key()
    return key is not None and len(key) > 5


def _is_temporary_unavailable_error(error_msg: str) -> bool:
    """Check if the error is a temporary 503 / high-demand / service unavailable error."""
    indicators = ["503", "UNAVAILABLE", "high demand", "overloaded", "Service Unavailable", "temporarily unavailable"]
    return any(ind.lower() in error_msg.lower() for ind in indicators)


def _is_quota_error(error_msg: str) -> bool:
    """Check if the error is a 429 rate limit or resource exhausted quota error."""
    indicators = ["429", "RESOURCE_EXHAUSTED", "quota", "rate limit"]
    return any(ind.lower() in error_msg.lower() for ind in indicators)


def _is_client_fatal_error(error_msg: str) -> bool:
    """Check if the error is a non-retryable client error (400, 401, 403, invalid key)."""
    fatal_indicators = ["400", "401", "403", "API_KEY_INVALID", "PERMISSION_DENIED", "UNAUTHENTICATED", "INVALID_ARGUMENT"]
    return any(ind in error_msg for ind in fatal_indicators)


def generate_ai_response(
    prompt: str,
    model_name: str = PRIMARY_MODEL
) -> Tuple[bool, str]:
    """
    Send prompt to Google Gemini using the official google-genai SDK.
    Handles temporary 503 high demand errors and 429 rate limits with backoff and multi-model fallback.
    
    Returns:
        (success: bool, response_text_or_error_message: str)
    """
    api_key = get_gemini_api_key()
    if not api_key:
        return (
            False,
            "⚠️ **Gemini API key is not configured.**\n\n"
            "Please create a `.env` file in the project root with:\n"
            "```text\nGEMINI_API_KEY=your_actual_gemini_api_key\n```\n"
            "Then restart the application."
        )

    try:
        from google import genai
    except ImportError:
        return (
            False,
            "⚠️ **google-genai SDK is not installed.**\n\n"
            "Please install it using `pip install google-genai`."
        )

    client = genai.Client(api_key=api_key)

    # Retry delays for temporary 503 or 429 errors (exponential backoff)
    retry_delays = [2.0, 4.0, 8.0]
    last_error_msg = ""

    # --- Step 1: Try Primary Model with Exponential Backoff ---
    for attempt, delay in enumerate(retry_delays, start=1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            
            if response and response.text:
                return (True, response.text.strip())
            else:
                return (False, "Received an empty response from Gemini. Please try rephrasing your question.")

        except Exception as e:
            last_error_msg = str(e)

            # Do NOT retry client errors (400, 401, 403, invalid key, etc.)
            if _is_client_fatal_error(last_error_msg):
                break

            # Check if temporary 503 / high demand error or 429 quota burst
            if _is_temporary_unavailable_error(last_error_msg) or _is_quota_error(last_error_msg):
                time.sleep(delay)
                continue
            else:
                break

    # --- Step 2: Fallback Models if Primary Model is Busy (503) or Rate-Limited (429) ---
    if _is_temporary_unavailable_error(last_error_msg) or _is_quota_error(last_error_msg):
        for fb_model in FALLBACK_MODELS:
            if fb_model == model_name:
                continue
            try:
                fallback_response = client.models.generate_content(
                    model=fb_model,
                    contents=prompt
                )
                if fallback_response and fallback_response.text:
                    return (True, fallback_response.text.strip())
            except Exception as fb_err:
                last_error_msg = str(fb_err)
                if not (_is_temporary_unavailable_error(last_error_msg) or _is_quota_error(last_error_msg)):
                    break

    # Redact API key from error output if present
    if api_key and api_key in last_error_msg:
        last_error_msg = last_error_msg.replace(api_key, "[REDACTED_API_KEY]")

    # --- Step 3: Friendly Error Classification ---
    if _is_temporary_unavailable_error(last_error_msg):
        return (
            False,
            "⚠️ **Gemini model service is temporarily busy (503 High Demand).**\n\n"
            "Both primary and fallback models are currently experiencing high demand. Please wait a moment and try again."
        )
    elif "429" in last_error_msg or "RESOURCE_EXHAUSTED" in last_error_msg or "quota" in last_error_msg.lower():
        return (
            False,
            "⚠️ **API rate limit or quota reached (429).**\n\n"
            "Please wait a moment before sending another request."
        )
    elif _is_client_fatal_error(last_error_msg):
        return (
            False,
            "❌ **Invalid API key or permission denied.**\n\n"
            "Please verify your `GEMINI_API_KEY` in `.env`."
        )
    else:
        return (
            False,
            f"❌ **Unable to generate an AI response right now.**\n\n"
            f"Please check your API key and network connection.\n\n"
            f"*Details: {last_error_msg}*"
        )

