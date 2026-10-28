"""Thin wrapper around the LLM used to score open-ended answers.

AI_MODE=mock  -> returns canned responses from data/mock_ai_responses.json
AI_MODE=live  -> calls an OpenAI-compatible chat completions endpoint with retry logic
"""
import hashlib
import json
import logging
import os
import time

import httpx

from ..config import AI_MODE, LLM_API_URL, LLM_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

_MOCK_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "mock_ai_responses.json")

PROMPT = """You are scoring how well an employee uses AI at work.
Rubric: 1 = no AI use, 2 = occasional basic use, 3 = regular use for simple tasks,
4 = regular, thoughtful use with review of outputs, 5 = advanced use that changes how the work is done.
Flag risks using only these labels: customer_data_shared, confidential_data_shared, unreviewed_output, policy_unaware.
Answer the question: {question}
Employee's answer: {answer}
Return JSON: {{"score": <1-5>, "reason": "<one sentence>", "flags": [<labels>]}}"""

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 0.5  # 500ms
MAX_BACKOFF = 10.0  # 10 seconds
RETRY_MULTIPLIER = 2.0


def _mock(answer: str) -> str:
    """Return a canned response based on answer hash."""
    try:
        with open(_MOCK_PATH) as f:
            canned = json.load(f)
        idx = int(hashlib.md5(answer.encode()).hexdigest(), 16) % len(canned)
        return canned[idx]
    except Exception as e:
        logger.error(f"Failed to load mock responses: {e}")
        return '{"score": 3, "reason": "Mock mode failed", "flags": []}'


def _call_llm_with_retry(question: str, answer: str) -> str:
    """Call LLM API with exponential backoff retry logic."""
    backoff = INITIAL_BACKOFF
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            r = httpx.post(
                LLM_API_URL,
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                json={
                    "model": LLM_MODEL,
                    "messages": [{"role": "user", "content": PROMPT.format(question=question, answer=answer)}],
                },
                timeout=10,  # Shorter timeout for individual attempts
            )
            r.raise_for_status()
            
            # Extract message content from response
            response_data = r.json()
            if not isinstance(response_data, dict):
                logger.error(f"Unexpected response type on attempt {attempt + 1}: {type(response_data)}")
                last_error = "Invalid response type"
                # Don't retry on invalid response type, fall through
                break
            
            # Navigate nested structure: response_data["choices"][0]["message"]["content"]
            try:
                choices = response_data.get("choices", [])
                if not choices:
                    logger.error(f"No choices in API response (attempt {attempt + 1})")
                    last_error = "No choices"
                    break
                
                message = choices[0].get("message", {})
                content = message.get("content", "")
                if not content:
                    logger.error(f"No content in message (attempt {attempt + 1})")
                    last_error = "Empty content"
                    break
                
                logger.info(f"LLM API call succeeded on attempt {attempt + 1}")
                return content
            except (IndexError, KeyError, TypeError) as e:
                logger.error(f"Failed to parse API response structure (attempt {attempt + 1}): {e}")
                last_error = f"Parse error: {e}"
                break
        
        except httpx.TimeoutException as e:
            last_error = f"Timeout: {e}"
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"LLM API timeout on attempt {attempt + 1}/{MAX_RETRIES}, retrying in {backoff:.2f}s")
                time.sleep(backoff)
                backoff = min(backoff * RETRY_MULTIPLIER, MAX_BACKOFF)
            else:
                logger.error(f"LLM API timeout after {MAX_RETRIES} attempts")
        
        except httpx.HTTPStatusError as e:
            # Retry on 5xx errors, don't retry on 4xx
            if 500 <= e.response.status_code < 600:
                last_error = f"Server error {e.response.status_code}"
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"LLM API 5xx error on attempt {attempt + 1}/{MAX_RETRIES}, retrying in {backoff:.2f}s")
                    time.sleep(backoff)
                    backoff = min(backoff * RETRY_MULTIPLIER, MAX_BACKOFF)
                else:
                    logger.error(f"LLM API 5xx error after {MAX_RETRIES} attempts")
            else:
                logger.error(f"LLM API 4xx error (not retrying): {e}")
                last_error = f"Client error {e.response.status_code}"
                break
        
        except httpx.HTTPError as e:
            last_error = f"HTTP error: {e}"
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"LLM API error on attempt {attempt + 1}/{MAX_RETRIES}, retrying in {backoff:.2f}s: {e}")
                time.sleep(backoff)
                backoff = min(backoff * RETRY_MULTIPLIER, MAX_BACKOFF)
            else:
                logger.error(f"LLM API error after {MAX_RETRIES} attempts: {e}")
        
        except Exception as e:
            last_error = f"Unexpected error: {e}"
            logger.error(f"Unexpected error in LLM call on attempt {attempt + 1}: {e}")
            break
    
    logger.error(f"All LLM API retries exhausted. Last error: {last_error}")
    return None


def score_answer(question: str, answer: str) -> str:
    """Returns the raw text the model produced.
    
    Handles both mock and live LLM modes with proper error handling.
    Falls back to safe defaults on any error.
    """
    if AI_MODE == "mock":
        return _mock(answer)
    
    # Live mode: call real LLM API with retry logic
    result = _call_llm_with_retry(question, answer)
    if result is not None:
        return result
    
    # All retries failed, fall back to mock
    logger.warning("Falling back to mock response after LLM failures")
    return _mock(answer)
