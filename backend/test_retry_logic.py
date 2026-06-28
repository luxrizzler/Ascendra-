"""
Additional test: Verify retry logic behavior with mock failures
This test simulates LLM failures to verify the retry mechanism works correctly
"""
import asyncio
import sys
sys.path.insert(0, '/app/backend')

from llm_retry import llm_call_with_retry, is_transient_llm_error, friendly_llm_error

async def test_retry_logic():
    """Test the retry logic with simulated failures"""
    print("=" * 80)
    print("TESTING RETRY LOGIC WITH SIMULATED FAILURES")
    print("=" * 80)
    
    # Test 1: Transient error that succeeds on retry
    print("\n--- Test 1: Transient error succeeds on 2nd attempt ---")
    attempt_count = 0
    
    async def transient_then_success():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            raise Exception("Error 429 concurrent_request_limit")
        return "Success!"
    
    try:
        result = await llm_call_with_retry(
            transient_then_success,
            max_retries=4,
            backoff=[0.1, 0.2, 0.3, 0.4],  # Short backoff for testing
            label="test_transient"
        )
        print(f"✅ PASS - Retry succeeded after {attempt_count} attempts: {result}")
    except Exception as e:
        print(f"❌ FAIL - Should have succeeded on retry: {e}")
    
    # Test 2: Non-transient error fails immediately
    print("\n--- Test 2: Non-transient error fails immediately ---")
    attempt_count = 0
    
    async def non_transient_error():
        nonlocal attempt_count
        attempt_count += 1
        raise ValueError("Invalid input")
    
    try:
        result = await llm_call_with_retry(
            non_transient_error,
            max_retries=4,
            backoff=[0.1, 0.2, 0.3, 0.4],
            label="test_non_transient"
        )
        print(f"❌ FAIL - Should have raised ValueError immediately")
    except ValueError as e:
        if attempt_count == 1:
            print(f"✅ PASS - Non-transient error failed immediately (1 attempt): {e}")
        else:
            print(f"❌ FAIL - Non-transient error should not retry (got {attempt_count} attempts)")
    except Exception as e:
        print(f"❌ FAIL - Wrong exception type: {e}")
    
    # Test 3: Transient error exhausts all retries
    print("\n--- Test 3: Transient error exhausts all retries ---")
    attempt_count = 0
    
    async def always_transient():
        nonlocal attempt_count
        attempt_count += 1
        raise Exception("503 Service Unavailable")
    
    try:
        result = await llm_call_with_retry(
            always_transient,
            max_retries=3,
            backoff=[0.1, 0.2, 0.3],
            label="test_exhausted"
        )
        print(f"❌ FAIL - Should have raised exception after retries")
    except Exception as e:
        if attempt_count == 3:
            print(f"✅ PASS - Exhausted retries after {attempt_count} attempts: {e}")
        else:
            print(f"❌ FAIL - Expected 3 attempts, got {attempt_count}")
    
    # Test 4: Verify friendly error messages
    print("\n--- Test 4: Verify friendly error messages ---")
    
    test_errors = [
        Exception("litellm.RateLimitError: 429 concurrent_request_limit"),
        Exception("OpenAIException: Rate limit exceeded"),
        Exception("503 Service Unavailable"),
        Exception("Connection timeout"),
    ]
    
    for exc in test_errors:
        msg = friendly_llm_error(exc)
        is_transient = is_transient_llm_error(exc)
        
        # Check message is friendly
        forbidden = ["litellm", "RateLimitError", "OpenAIException", "Traceback"]
        has_forbidden = any(word in msg for word in forbidden)
        
        if has_forbidden:
            print(f"❌ FAIL - Message contains forbidden words: {msg}")
        else:
            print(f"✅ PASS - Friendly message for {str(exc)[:50]}: '{msg[:60]}...'")
    
    print("\n" + "=" * 80)
    print("RETRY LOGIC TESTS COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_retry_logic())
