"""
Test LLM Retry Module and Regenerate Endpoint Error Handling
Tests the fix for raw 'litellm.RateLimitError' bubbling up to UI
"""
import requests
import sys
import json
from datetime import datetime
from typing import Optional

BASE_URL = "https://repo-to-site-2.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@ascendraacademy.com"
ADMIN_PASSWORD = "AscendraAdmin2026!"

class LLMRetryTester:
    def __init__(self):
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
    def log(self, msg: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {msg}")
    
    def test(self, name: str, method: str, endpoint: str, expected_status: int,
             token: Optional[str] = None, data: Optional[dict] = None,
             params: Optional[dict] = None, acceptable_statuses: Optional[list] = None) -> tuple[bool, dict, int]:
        """Run a single API test. Returns (success, response_dict, status_code)"""
        url = f"{BASE_URL}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        self.tests_run += 1
        self.log(f"Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=90)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=90)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=90)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=90)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Check if status is acceptable
            if acceptable_statuses:
                success = response.status_code in acceptable_statuses
            else:
                success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASS - Status: {response.status_code}", "PASS")
            else:
                self.tests_failed += 1
                self.failed_tests.append({
                    "name": name,
                    "expected": expected_status if not acceptable_statuses else f"one of {acceptable_statuses}",
                    "actual": response.status_code,
                    "response": response.text[:300]
                })
                self.log(f"❌ FAIL - Expected {expected_status if not acceptable_statuses else acceptable_statuses}, got {response.status_code}", "FAIL")
                self.log(f"   Response: {response.text[:300]}", "FAIL")
            
            try:
                return success, response.json(), response.status_code
            except:
                return success, {"raw": response.text}, response.status_code
        
        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append({
                "name": name,
                "expected": expected_status,
                "error": str(e)
            })
            self.log(f"❌ FAIL - Error: {str(e)}", "FAIL")
            return False, {"error": str(e)}, 0
    
    def login(self, email: str, password: str) -> Optional[str]:
        """Login and return token"""
        self.log(f"Logging in as {email}")
        success, response, _ = self.test(
            f"Login as {email}",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'access_token' in response:
            token = response['access_token']
            self.log(f"✅ Login successful for {email}")
            return token
        self.log(f"❌ Login failed for {email}")
        return None
    
    def setup_auth(self):
        """Setup authentication for admin"""
        self.log("=" * 80)
        self.log("AUTHENTICATION SETUP")
        self.log("=" * 80)
        
        self.admin_token = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not self.admin_token:
            self.log("❌ CRITICAL: Admin login failed. Cannot proceed.", "ERROR")
            return False
        
        return True
    
    def test_llm_retry_module(self):
        """Test the llm_retry module functions directly"""
        self.log("\n" + "=" * 80)
        self.log("TEST 1: LLM RETRY MODULE FUNCTIONS")
        self.log("=" * 80)
        
        try:
            # Import the module
            import sys
            sys.path.insert(0, '/app/backend')
            from llm_retry import is_transient_llm_error, friendly_llm_error
            
            self.log("\n--- Testing is_transient_llm_error() ---")
            
            # Test 1: 429 concurrent_request_limit (should be True)
            test_cases = [
                (Exception("Error 429 concurrent_request_limit"), True, "429 concurrent_request_limit"),
                (Exception("litellm.RateLimitError: 429 rate limit exceeded"), True, "429 rate limit"),
                (Exception("overloaded_error from provider"), True, "overloaded_error"),
                (Exception("Connection timeout after 30s"), True, "timeout"),
                (Exception("Request timed out"), True, "timed out"),
                (Exception("503 Service Unavailable"), True, "503"),
                (Exception("502 Bad Gateway"), True, "502"),
                (Exception("504 Gateway Timeout"), True, "504"),
                (Exception("NameError: name 'x' is not defined"), False, "NameError"),
                (Exception("ValueError: invalid input"), False, "ValueError"),
                (Exception("Some random error"), False, "random error"),
            ]
            
            for exc, expected, description in test_cases:
                result = is_transient_llm_error(exc)
                self.tests_run += 1
                if result == expected:
                    self.tests_passed += 1
                    self.log(f"✅ PASS - is_transient_llm_error({description}) = {result}", "PASS")
                else:
                    self.tests_failed += 1
                    self.failed_tests.append({
                        "name": f"is_transient_llm_error({description})",
                        "expected": expected,
                        "actual": result
                    })
                    self.log(f"❌ FAIL - is_transient_llm_error({description}) expected {expected}, got {result}", "FAIL")
            
            self.log("\n--- Testing friendly_llm_error() ---")
            
            # Test friendly_llm_error returns clean messages
            error_cases = [
                (Exception("Error 429 concurrent_request_limit"), ["busy", "wait"], ["litellm", "RateLimitError", "OpenAIException"]),
                (Exception("litellm.RateLimitError: rate limit exceeded"), ["busy", "wait"], ["litellm", "RateLimitError"]),
                (Exception("overloaded_error"), ["overloaded", "minute"], ["litellm", "OpenAIException"]),
                (Exception("Connection timeout"), ["timeout", "took too long"], ["litellm", "RateLimitError"]),
            ]
            
            for exc, should_contain, should_not_contain in error_cases:
                msg = friendly_llm_error(exc)
                self.tests_run += 1
                
                # Check that message contains expected words
                contains_expected = any(word.lower() in msg.lower() for word in should_contain)
                # Check that message does NOT contain forbidden words
                contains_forbidden = any(word in msg for word in should_not_contain)
                
                if contains_expected and not contains_forbidden:
                    self.tests_passed += 1
                    self.log(f"✅ PASS - friendly_llm_error() returned clean message: '{msg[:80]}'", "PASS")
                else:
                    self.tests_failed += 1
                    self.failed_tests.append({
                        "name": f"friendly_llm_error({str(exc)[:50]})",
                        "expected": f"Contains {should_contain}, NOT contains {should_not_contain}",
                        "actual": msg
                    })
                    if not contains_expected:
                        self.log(f"❌ FAIL - Message missing expected words {should_contain}: '{msg}'", "FAIL")
                    if contains_forbidden:
                        self.log(f"❌ FAIL - Message contains forbidden words {should_not_contain}: '{msg}'", "FAIL")
            
            self.log("\n✅ LLM retry module tests completed")
            
        except Exception as e:
            self.log(f"❌ ERROR testing llm_retry module: {str(e)}", "ERROR")
            self.tests_failed += 1
            self.failed_tests.append({
                "name": "llm_retry module import/test",
                "error": str(e)
            })
    
    def test_regenerate_endpoint(self):
        """Test the regenerate endpoint error handling"""
        self.log("\n" + "=" * 80)
        self.log("TEST 2: REGENERATE ENDPOINT ERROR HANDLING")
        self.log("=" * 80)
        
        # First, get the queue to find items
        self.log("\n--- Getting queue items ---")
        success, response, _ = self.test(
            "GET /api/admin/auto/queue - Get queue items",
            "GET",
            "admin/auto/queue",
            200,
            token=self.admin_token
        )
        
        if not success:
            self.log("❌ Cannot get queue items, skipping regenerate tests", "ERROR")
            return
        
        queue_items = response.get("items", [])
        self.log(f"Found {len(queue_items)} queue items")
        
        # Find items in different states
        failed_item = None
        needs_review_item = None
        published_item = None
        pending_item = None
        
        for item in queue_items:
            status = item.get("status")
            if status == "failed" and not failed_item:
                failed_item = item
            elif status == "needs_review" and not needs_review_item:
                needs_review_item = item
            elif status == "published" and not published_item:
                published_item = item
            elif status == "pending" and not pending_item:
                pending_item = item
        
        self.log(f"Found: failed={failed_item is not None}, needs_review={needs_review_item is not None}, "
                f"published={published_item is not None}, pending={pending_item is not None}")
        
        # PRIMARY TEST: Regenerate on FAILED or NEEDS_REVIEW item
        test_item = failed_item or needs_review_item
        if test_item:
            self.log(f"\n--- PRIMARY TEST: Regenerate {test_item['status']} item ---")
            self.log(f"Item ID: {test_item['id']}")
            self.log(f"Topic: {test_item.get('topic', 'N/A')}")
            
            # This is the critical test - regenerate should either:
            # (a) return 200 with success, OR
            # (b) return 503 with a friendly error message (transient failure)
            # It should NEVER return 500 or a raw 'litellm' error
            
            success, response, status_code = self.test(
                f"POST /api/admin/auto/queue/{{id}}/regenerate - Regenerate {test_item['status']} item",
                "POST",
                f"admin/auto/queue/{test_item['id']}/regenerate",
                200,
                token=self.admin_token,
                acceptable_statuses=[200, 503, 502]  # Accept success OR friendly error
            )
            
            # Check the response detail for forbidden strings
            if status_code in [502, 503]:
                # This is a handled error - check that it's friendly
                detail = response.get("detail", "")
                self.tests_run += 1
                
                forbidden_words = ["litellm", "RateLimitError", "OpenAIException", "Traceback", "Exception:"]
                contains_forbidden = any(word in detail for word in forbidden_words)
                
                if contains_forbidden:
                    self.tests_failed += 1
                    self.failed_tests.append({
                        "name": "Regenerate error message check",
                        "expected": "Friendly error message without raw exception details",
                        "actual": detail
                    })
                    self.log(f"❌ FAIL - Error detail contains raw exception info: '{detail}'", "FAIL")
                else:
                    self.tests_passed += 1
                    self.log(f"✅ PASS - Error message is user-friendly: '{detail}'", "PASS")
                    
                    # Check for expected friendly words
                    friendly_words = ["busy", "wait", "overloaded", "hiccup", "try again"]
                    contains_friendly = any(word.lower() in detail.lower() for word in friendly_words)
                    if contains_friendly:
                        self.log(f"   ✅ Message contains friendly language", "PASS")
            
            elif status_code == 200:
                # Success case - check the run result
                run = response.get("run", {})
                run_status = run.get("status")
                self.log(f"   ✅ Regeneration succeeded with status: {run_status}")
                
                # Check that the item was updated
                item = response.get("item", {})
                if item:
                    new_status = item.get("status")
                    self.log(f"   Item new status: {new_status}")
        else:
            self.log("⚠️  No FAILED or NEEDS_REVIEW items to test regenerate", "WARN")
        
        # Test 404 for non-existent item
        self.log("\n--- Test 404 for non-existent item ---")
        self.test(
            "POST /api/admin/auto/queue/{{id}}/regenerate - Non-existent item returns 404",
            "POST",
            "admin/auto/queue/nonexistent-id-xyz-12345/regenerate",
            404,
            token=self.admin_token
        )
        
        # Test 400 for invalid status (published or pending)
        if published_item:
            self.log("\n--- Test 400 for published item ---")
            self.test(
                "POST /api/admin/auto/queue/{{id}}/regenerate - Published item returns 400",
                "POST",
                f"admin/auto/queue/{published_item['id']}/regenerate",
                400,
                token=self.admin_token
            )
        
        if pending_item:
            self.log("\n--- Test 400 for pending item ---")
            self.test(
                "POST /api/admin/auto/queue/{{id}}/regenerate - Pending item returns 400",
                "POST",
                f"admin/auto/queue/{pending_item['id']}/regenerate",
                400,
                token=self.admin_token
            )
    
    def test_regression_endpoints(self):
        """Test regression - other admin auto queue endpoints still work"""
        self.log("\n" + "=" * 80)
        self.log("TEST 3: REGRESSION - OTHER ADMIN AUTO QUEUE ENDPOINTS")
        self.log("=" * 80)
        
        # Test GET /api/admin/auto/queue
        self.log("\n--- Test GET /api/admin/auto/queue ---")
        success, response, _ = self.test(
            "GET /api/admin/auto/queue - List queue items",
            "GET",
            "admin/auto/queue",
            200,
            token=self.admin_token
        )
        
        if success:
            items = response.get("items", [])
            self.log(f"   ✅ Retrieved {len(items)} queue items")
        
        # Find a needs_review item for draft edit test
        needs_review_item = None
        if success:
            for item in response.get("items", []):
                if item.get("status") == "needs_review":
                    needs_review_item = item
                    break
        
        # Test PATCH /api/admin/auto/queue/{id}/draft
        if needs_review_item:
            self.log(f"\n--- Test PATCH /api/admin/auto/queue/{{id}}/draft ---")
            self.log(f"Testing on item: {needs_review_item['id']}")
            
            self.test(
                "PATCH /api/admin/auto/queue/{{id}}/draft - Edit draft",
                "PATCH",
                f"admin/auto/queue/{needs_review_item['id']}/draft",
                200,
                token=self.admin_token,
                data={
                    "title": "Updated Test Title via Regression Test"
                }
            )
        else:
            self.log("⚠️  No needs_review items to test draft edit", "WARN")
        
        # Test POST /api/admin/auto/queue/{id}/reject
        if needs_review_item:
            self.log(f"\n--- Test POST /api/admin/auto/queue/{{id}}/reject ---")
            
            # Note: This will actually reject the item, so we'll use a different one if available
            # or skip if we don't want to modify the queue
            self.log("   Skipping reject test to preserve queue state")
        else:
            self.log("⚠️  No needs_review items to test reject", "WARN")
    
    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "=" * 80)
        self.log("TEST SUMMARY - LLM RETRY & ERROR HANDLING")
        self.log("=" * 80)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"Passed: {self.tests_passed} ✅")
        self.log(f"Failed: {self.tests_failed} ❌")
        
        if self.tests_run > 0:
            success_rate = (self.tests_passed / self.tests_run * 100)
            self.log(f"Success Rate: {success_rate:.1f}%")
        
        if self.failed_tests:
            self.log("\n" + "=" * 80)
            self.log("FAILED TESTS DETAILS")
            self.log("=" * 80)
            for i, test in enumerate(self.failed_tests, 1):
                self.log(f"\n{i}. {test['name']}")
                if 'expected' in test:
                    self.log(f"   Expected: {test['expected']}")
                if 'actual' in test:
                    self.log(f"   Actual: {test['actual']}")
                if 'response' in test:
                    self.log(f"   Response: {test['response']}")
                if 'error' in test:
                    self.log(f"   Error: {test['error']}")
        
        self.log("\n" + "=" * 80)
        self.log("KEY FINDINGS")
        self.log("=" * 80)
        
        # Check if the primary bug is fixed
        raw_error_found = False
        for test in self.failed_tests:
            if "raw exception" in test.get("name", "").lower() or \
               any(word in str(test.get("actual", "")) for word in ["litellm", "RateLimitError", "OpenAIException"]):
                raw_error_found = True
                break
        
        if raw_error_found:
            self.log("❌ PRIMARY BUG STILL PRESENT: Raw LLM errors are bubbling up to the API response", "ERROR")
        else:
            self.log("✅ PRIMARY BUG FIXED: No raw LLM errors found in API responses", "PASS")
        
        return 0 if self.tests_failed == 0 else 1

def main():
    tester = LLMRetryTester()
    
    # Setup authentication
    if not tester.setup_auth():
        return 1
    
    # Run tests
    tester.test_llm_retry_module()
    tester.test_regenerate_endpoint()
    tester.test_regression_endpoints()
    
    # Print summary
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
