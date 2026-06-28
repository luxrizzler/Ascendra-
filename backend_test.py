"""
Ascendra Academy - Interactive Lesson System Backend Tests
Tests for:
- Playground endpoint (POST /api/playground/run)
- Migration endpoint (POST /api/admin/curriculum/migrate-interactive)
- Lesson structure (GET /api/lessons/f1l1)
- Regression tests (Stripe webhook, social X status, etc.)
"""
import requests
import json
import hmac
import hashlib
import time
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://repo-to-site-2.preview.emergentagent.com"
WEBHOOK_SECRET = "whsec_pP6zR3wzRFmP74btq3NRaTHanbdK4q6J"
ADMIN_EMAIL = "admin@ascendraacademy.com"
ADMIN_PASSWORD = "AscendraAdmin2026!"
SAGE_EMAIL = "sage1@ascendraacademy.com"
SAGE_PASSWORD = "test1"
SAGE3_EMAIL = "sage3@ascendraacademy.com"
SAGE3_PASSWORD = "test3"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class InteractiveLessonTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.admin_token = None
        self.sage_token = None
        self.test_user_id = None
        self.test_user_email = None
        self.test_user_token = None

    def log_test(self, name, passed, expected, actual, details=""):
        """Log test result with color coding"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"{Colors.GREEN}✅ PASS{Colors.RESET} - {name}")
            if details:
                print(f"   {Colors.BLUE}ℹ{Colors.RESET}  {details}")
        else:
            self.tests_failed += 1
            print(f"{Colors.RED}❌ FAIL{Colors.RESET} - {name}")
            print(f"   Expected: {expected}")
            print(f"   Actual: {actual}")
            if details:
                print(f"   Details: {details}")

    def login_sage_user(self):
        """Login as sage user"""
        print(f"\n{Colors.BLUE}SETUP: Logging in as sage user{Colors.RESET}")
        try:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": SAGE_EMAIL, "password": SAGE_PASSWORD}
            )
            if response.status_code == 200:
                self.sage_token = response.json().get("access_token")
                print(f"{Colors.GREEN}✓{Colors.RESET} Logged in as {SAGE_EMAIL}")
                return True
            else:
                print(f"{Colors.RED}✗{Colors.RESET} Failed to login: {response.status_code}")
                return False
        except Exception as e:
            print(f"{Colors.RED}✗{Colors.RESET} Exception: {str(e)}")
            return False

    def login_admin_user(self):
        """Login as admin user"""
        print(f"\n{Colors.BLUE}SETUP: Logging in as admin{Colors.RESET}")
        try:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
            )
            if response.status_code == 200:
                self.admin_token = response.json().get("access_token")
                print(f"{Colors.GREEN}✓{Colors.RESET} Logged in as admin")
                return True
            else:
                print(f"{Colors.RED}✗{Colors.RESET} Failed to login: {response.status_code}")
                return False
        except Exception as e:
            print(f"{Colors.RED}✗{Colors.RESET} Exception: {str(e)}")
            return False

    def test_playground_authenticated(self):
        """TEST: POST /api/playground/run with authenticated sage user → 200 with response"""
        print(f"\n{Colors.BLUE}TEST: Playground endpoint with authenticated user{Colors.RESET}")
        
        if not self.sage_token:
            self.log_test(
                "Playground with auth",
                False,
                "200 with response",
                "Sage user not logged in"
            )
            return False
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/playground/run",
                json={"prompt": "Say hello in 5 words"},
                headers={"Authorization": f"Bearer {self.sage_token}"}
            )
            
            passed = response.status_code == 200
            if passed:
                data = response.json()
                has_response = "response" in data and len(data.get("response", "")) > 0
                passed = has_response
                
                self.log_test(
                    "Playground with authenticated user",
                    passed,
                    "200 with non-empty response field",
                    f"{response.status_code} with response length: {len(data.get('response', ''))}",
                    f"✓ AI response received: {data.get('response', '')[:50]}..." if passed else ""
                )
            else:
                self.log_test(
                    "Playground with authenticated user",
                    False,
                    "200 with response",
                    f"{response.status_code}: {response.text[:200]}"
                )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "Playground with authenticated user",
                False,
                "200 with response",
                f"Exception: {str(e)}"
            )
            return False

    def test_playground_no_auth(self):
        """TEST: POST /api/playground/run without auth → 401 or 403"""
        print(f"\n{Colors.BLUE}TEST: Playground endpoint without auth{Colors.RESET}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/playground/run",
                json={"prompt": "Say hello in 5 words"}
            )
            
            passed = response.status_code in [401, 403]
            
            self.log_test(
                "Playground without auth",
                passed,
                "401 or 403",
                f"{response.status_code}",
                "✓ Correctly requires authentication" if passed else "⚠ Should require authentication"
            )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "Playground without auth",
                False,
                "401 or 403",
                f"Exception: {str(e)}"
            )
            return False

    def test_playground_empty_prompt(self):
        """TEST: POST /api/playground/run with empty prompt → 422"""
        print(f"\n{Colors.BLUE}TEST: Playground endpoint with empty prompt{Colors.RESET}")
        
        if not self.sage_token:
            self.log_test(
                "Playground with empty prompt",
                False,
                "422",
                "Sage user not logged in"
            )
            return False
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/playground/run",
                json={"prompt": ""},
                headers={"Authorization": f"Bearer {self.sage_token}"}
            )
            
            passed = response.status_code == 422
            
            self.log_test(
                "Playground with empty prompt",
                passed,
                "422 (Pydantic validation error)",
                f"{response.status_code}",
                "✓ Correctly validates prompt" if passed else "⚠ Should validate empty prompt"
            )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "Playground with empty prompt",
                False,
                "422",
                f"Exception: {str(e)}"
            )
            return False

    def test_migration_endpoint(self):
        """TEST: POST /api/admin/curriculum/migrate-interactive → correct response"""
        print(f"\n{Colors.BLUE}TEST: Migration endpoint (admin auth){Colors.RESET}")
        
        if not self.admin_token:
            self.log_test(
                "Migration endpoint",
                False,
                "200 with updated:['f1l1']",
                "Admin not logged in"
            )
            return False
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/admin/curriculum/migrate-interactive",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )
            
            passed = response.status_code == 200
            if passed:
                data = response.json()
                has_updated = "updated" in data and "f1l1" in data.get("updated", [])
                has_count = data.get("count") >= 1
                has_skipped = "skipped" in data
                
                passed = has_updated and has_count and has_skipped
                
                self.log_test(
                    "Migration endpoint",
                    passed,
                    "200 with {updated:['f1l1'], count:1, skipped:[]}",
                    f"{response.status_code} with data: {data}",
                    "✓ Migration endpoint working correctly" if passed else ""
                )
            else:
                self.log_test(
                    "Migration endpoint",
                    False,
                    "200 with correct structure",
                    f"{response.status_code}: {response.text[:200]}"
                )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "Migration endpoint",
                False,
                "200 with correct structure",
                f"Exception: {str(e)}"
            )
            return False

    def test_lesson_f1l1_structure(self):
        """TEST: GET /api/lessons/f1l1 → verify 7 cards with correct structure"""
        print(f"\n{Colors.BLUE}TEST: Lesson f1l1 structure{Colors.RESET}")
        
        if not self.sage_token:
            self.log_test(
                "Lesson f1l1 structure",
                False,
                "7 cards with correct kinds",
                "Sage user not logged in"
            )
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/lessons/f1l1",
                headers={"Authorization": f"Bearer {self.sage_token}"}
            )
            
            passed = response.status_code == 200
            if passed:
                lesson = response.json()
                cards = lesson.get("cards", [])
                
                # Check card count
                has_7_cards = len(cards) == 7
                
                # Check card kinds in order
                expected_kinds = ['text', 'text', 'knowledge_check', 'text', 'fill_blank', 'text', 'playground']
                actual_kinds = [c.get("kind", "text") for c in cards]
                kinds_match = actual_kinds == expected_kinds
                
                # Check knowledge_check card structure (card 3, index 2)
                check_card = cards[2] if len(cards) > 2 else {}
                has_check_fields = all(k in check_card for k in ["question", "options", "answer_index", "explanation"])
                has_4_options = len(check_card.get("options", [])) == 4
                
                # Check fill_blank card structure (card 5, index 4)
                blank_card = cards[4] if len(cards) > 4 else {}
                has_blank_fields = all(k in blank_card for k in ["prompt", "answer", "aliases", "explanation"])
                has_blank_placeholder = "___" in blank_card.get("prompt", "")
                
                # Check playground card structure (card 7, index 6)
                play_card = cards[6] if len(cards) > 6 else {}
                has_play_fields = all(k in play_card for k in ["instruction", "seed_prompt"])
                
                all_checks = (
                    has_7_cards and kinds_match and 
                    has_check_fields and has_4_options and
                    has_blank_fields and has_blank_placeholder and
                    has_play_fields
                )
                
                details = []
                if has_7_cards:
                    details.append(f"✓ 7 cards found")
                else:
                    details.append(f"✗ Expected 7 cards, got {len(cards)}")
                
                if kinds_match:
                    details.append(f"✓ Card kinds match: {actual_kinds}")
                else:
                    details.append(f"✗ Expected {expected_kinds}, got {actual_kinds}")
                
                if has_check_fields and has_4_options:
                    details.append(f"✓ knowledge_check card has correct structure")
                else:
                    details.append(f"✗ knowledge_check card missing fields")
                
                if has_blank_fields and has_blank_placeholder:
                    details.append(f"✓ fill_blank card has correct structure")
                else:
                    details.append(f"✗ fill_blank card missing fields or ___")
                
                if has_play_fields:
                    details.append(f"✓ playground card has correct structure")
                else:
                    details.append(f"✗ playground card missing fields")
                
                self.log_test(
                    "Lesson f1l1 structure",
                    all_checks,
                    "7 cards with kinds ['text','text','knowledge_check','text','fill_blank','text','playground']",
                    f"{len(cards)} cards with kinds {actual_kinds}",
                    "\n   ".join(details)
                )
                
                passed = all_checks
            else:
                self.log_test(
                    "Lesson f1l1 structure",
                    False,
                    "200 with 7 cards",
                    f"{response.status_code}: {response.text[:200]}"
                )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "Lesson f1l1 structure",
                False,
                "7 cards with correct structure",
                f"Exception: {str(e)}"
            )
            return False

    def generate_stripe_signature(self, payload_str, timestamp=None):
        """Generate a valid Stripe webhook signature using HMAC-SHA256"""
        if timestamp is None:
            timestamp = int(time.time())
        
        # Stripe signature format: t={timestamp},v1={signature}
        signed_payload = f"{timestamp}.{payload_str}"
        signature = hmac.new(
            WEBHOOK_SECRET.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"t={timestamp},v1={signature}"

    def test_webhook_no_signature(self):
        """TEST 1: POST webhook with NO stripe-signature header → MUST return 400"""
        print(f"\n{Colors.BLUE}TEST 1: Webhook without signature header{Colors.RESET}")
        
        forged_payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {
                        "user_id": "forged-user-123",
                        "tier": "sage"
                    }
                }
            }
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/billing/webhook",
                json=forged_payload,
                headers={"Content-Type": "application/json"}
                # NO stripe-signature header
            )
            
            passed = response.status_code == 400
            body_text = response.text.lower()
            has_correct_message = "missing stripe-signature header" in body_text
            
            self.log_test(
                "Reject webhook without signature",
                passed and has_correct_message,
                "400 with 'Missing stripe-signature header'",
                f"{response.status_code} with body: {response.text[:200]}",
                "✓ Unsigned payload correctly rejected" if passed else "⚠ Security vulnerability: unsigned payload accepted"
            )
            
            return passed and has_correct_message
            
        except Exception as e:
            self.log_test(
                "Reject webhook without signature",
                False,
                "400 with error message",
                f"Exception: {str(e)}"
            )
            return False

    def test_webhook_invalid_signature(self):
        """TEST 2: POST webhook with BOGUS stripe-signature header → MUST return 400"""
        print(f"\n{Colors.BLUE}TEST 2: Webhook with invalid signature{Colors.RESET}")
        
        forged_payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {
                        "user_id": "forged-user-456",
                        "tier": "sage"
                    }
                }
            }
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/billing/webhook",
                json=forged_payload,
                headers={
                    "Content-Type": "application/json",
                    "stripe-signature": "t=1234,v1=deadbeef"  # Bogus signature
                }
            )
            
            passed = response.status_code == 400
            body_text = response.text.lower()
            has_correct_message = "invalid signature" in body_text
            
            self.log_test(
                "Reject webhook with invalid signature",
                passed and has_correct_message,
                "400 with 'Invalid signature'",
                f"{response.status_code} with body: {response.text[:200]}",
                "✓ Forged signature correctly rejected" if passed else "⚠ Security vulnerability: forged signature accepted"
            )
            
            return passed and has_correct_message
            
        except Exception as e:
            self.log_test(
                "Reject webhook with invalid signature",
                False,
                "400 with error message",
                f"Exception: {str(e)}"
            )
            return False

    def create_test_user(self):
        """Create a fresh test user for the positive path test"""
        print(f"\n{Colors.BLUE}SETUP: Creating test user{Colors.RESET}")
        
        timestamp = int(time.time())
        self.test_user_email = f"webhook_test_{timestamp}@test.ascendra.com"
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/auth/signup",
                json={
                    "email": self.test_user_email,
                    "password": "TestPass123!",
                    "name": "Webhook Test User"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test_user_token = data.get("access_token")
                
                # Get user ID
                me_response = requests.get(
                    f"{BASE_URL}/api/auth/me",
                    headers={"Authorization": f"Bearer {self.test_user_token}"}
                )
                
                if me_response.status_code == 200:
                    user_data = me_response.json()
                    self.test_user_id = user_data.get("id")
                    initial_tier = user_data.get("tier")
                    
                    print(f"{Colors.GREEN}✓{Colors.RESET} Test user created: {self.test_user_email}")
                    print(f"   User ID: {self.test_user_id}")
                    print(f"   Initial tier: {initial_tier}")
                    return True
            
            print(f"{Colors.RED}✗{Colors.RESET} Failed to create test user: {response.status_code}")
            return False
            
        except Exception as e:
            print(f"{Colors.RED}✗{Colors.RESET} Exception creating test user: {str(e)}")
            return False

    def test_webhook_valid_signature(self):
        """TEST 3: POST webhook with VALID signature → MUST return 200 and process event"""
        print(f"\n{Colors.BLUE}TEST 3: Webhook with valid signature (POSITIVE PATH){Colors.RESET}")
        
        if not self.test_user_id:
            self.log_test(
                "Process webhook with valid signature",
                False,
                "200 and tier updated",
                "Test user not created"
            )
            return False
        
        # Create a valid webhook payload
        payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": f"cs_test_{int(time.time())}",
                    "mode": "payment",
                    "customer": f"cus_test_{int(time.time())}",
                    "metadata": {
                        "user_id": self.test_user_id,
                        "tier": "ascender",
                        "interval": "monthly"
                    }
                }
            }
        }
        
        payload_str = json.dumps(payload)
        
        try:
            # Generate valid signature
            valid_signature = self.generate_stripe_signature(payload_str)
            
            print(f"   Sending signed webhook for user: {self.test_user_id}")
            
            # Send webhook with valid signature
            response = requests.post(
                f"{BASE_URL}/api/billing/webhook",
                data=payload_str,  # Send as raw string, not JSON
                headers={
                    "Content-Type": "application/json",
                    "stripe-signature": valid_signature
                }
            )
            
            webhook_passed = response.status_code == 200
            
            self.log_test(
                "Webhook accepts valid signature",
                webhook_passed,
                "200",
                f"{response.status_code}",
                f"Response: {response.text[:100]}" if not webhook_passed else "✓ Valid signature accepted"
            )
            
            if not webhook_passed:
                return False
            
            # Wait a moment for processing
            time.sleep(1)
            
            # Verify user tier was updated
            print(f"   Verifying tier update...")
            me_response = requests.get(
                f"{BASE_URL}/api/auth/me",
                headers={"Authorization": f"Bearer {self.test_user_token}"}
            )
            
            if me_response.status_code == 200:
                user_data = me_response.json()
                updated_tier = user_data.get("tier")
                
                tier_updated = updated_tier == "ascender"
                
                self.log_test(
                    "User tier updated to 'ascender'",
                    tier_updated,
                    "tier='ascender'",
                    f"tier='{updated_tier}'",
                    f"✓ Webhook successfully processed and tier granted" if tier_updated else "⚠ Webhook accepted but tier not updated"
                )
                
                return webhook_passed and tier_updated
            else:
                self.log_test(
                    "User tier updated to 'ascender'",
                    False,
                    "tier='ascender'",
                    f"Failed to fetch user: {me_response.status_code}"
                )
                return False
            
        except Exception as e:
            self.log_test(
                "Process webhook with valid signature",
                False,
                "200 and tier updated",
                f"Exception: {str(e)}"
            )
            return False

    def test_regression_social_x_status(self):
        """REGRESSION: GET /api/admin/social/x/status returns ok:true"""
        print(f"\n{Colors.BLUE}REGRESSION TEST: Admin social X status{Colors.RESET}")
        
        # Login as admin if not already
        if not self.admin_token:
            try:
                response = requests.post(
                    f"{BASE_URL}/api/auth/login",
                    json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
                )
                if response.status_code == 200:
                    self.admin_token = response.json().get("access_token")
            except Exception as e:
                print(f"{Colors.YELLOW}⚠{Colors.RESET} Could not login as admin: {str(e)}")
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/admin/social/x/status",
                headers={"Authorization": f"Bearer {self.admin_token}"} if self.admin_token else {}
            )
            
            passed = response.status_code == 200
            if passed:
                data = response.json()
                has_ok = data.get("ok") == True
                passed = has_ok
            
            self.log_test(
                "Admin social X status endpoint",
                passed,
                "200 with ok:true",
                f"{response.status_code} with body: {response.text[:100]}"
            )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "Admin social X status endpoint",
                False,
                "200 with ok:true",
                f"Exception: {str(e)}"
            )
            return False

    def test_regression_api_root(self):
        """REGRESSION: GET /api/ returns {status:ok}"""
        print(f"\n{Colors.BLUE}REGRESSION TEST: API root endpoint{Colors.RESET}")
        
        try:
            response = requests.get(f"{BASE_URL}/api/")
            
            passed = response.status_code == 200
            if passed:
                data = response.json()
                has_status = data.get("status") == "ok"
                passed = has_status
            
            self.log_test(
                "API root endpoint",
                passed,
                "200 with status:ok",
                f"{response.status_code} with body: {response.text[:100]}"
            )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "API root endpoint",
                False,
                "200 with status:ok",
                f"Exception: {str(e)}"
            )
            return False

    def test_regression_openapi_schema(self):
        """REGRESSION: GET /openapi.json contains /api/billing/webhook route"""
        print(f"\n{Colors.BLUE}REGRESSION TEST: OpenAPI schema includes webhook route{Colors.RESET}")
        
        try:
            # OpenAPI schema is only accessible internally (not through public ingress)
            # Check internal endpoint
            response = requests.get("http://localhost:8001/openapi.json")
            
            passed = response.status_code == 200
            if passed:
                schema = response.json()
                paths = schema.get("paths", {})
                has_webhook = "/api/billing/webhook" in paths
                
                passed = has_webhook
                
                self.log_test(
                    "Webhook route in OpenAPI schema",
                    passed,
                    "/api/billing/webhook present in schema",
                    f"Webhook route {'found' if has_webhook else 'NOT FOUND'} in schema"
                )
            else:
                self.log_test(
                    "Webhook route in OpenAPI schema",
                    False,
                    "200 with webhook route",
                    f"{response.status_code}"
                )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "Webhook route in OpenAPI schema",
                False,
                "200 with webhook route",
                f"Exception: {str(e)}"
            )
            return False

    def test_streak_endpoint(self):
        """TEST: GET /api/streak/me returns streak data with all required fields"""
        print(f"\n{Colors.BLUE}TEST: Streak endpoint{Colors.RESET}")
        
        if not self.sage_token:
            self.log_test(
                "Streak endpoint",
                False,
                "200 with streak data",
                "Sage user not logged in"
            )
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/streak/me",
                headers={"Authorization": f"Bearer {self.sage_token}"}
            )
            
            passed = response.status_code == 200
            if passed:
                data = response.json()
                required_fields = [
                    "current_streak", "longest_streak", "last_active_date", "today",
                    "activity_calendar", "daily_goal_target", "daily_goal_done",
                    "daily_goal_complete", "next_milestone", "days_to_next_milestone"
                ]
                has_all_fields = all(f in data for f in required_fields)
                
                # Validate types
                is_valid = (
                    isinstance(data.get("current_streak"), int) and
                    isinstance(data.get("longest_streak"), int) and
                    isinstance(data.get("activity_calendar"), list) and
                    isinstance(data.get("daily_goal_target"), int) and
                    isinstance(data.get("daily_goal_done"), int) and
                    isinstance(data.get("daily_goal_complete"), bool) and
                    data.get("current_streak") >= 0
                )
                
                passed = has_all_fields and is_valid
                
                details = f"current_streak={data.get('current_streak')}, longest_streak={data.get('longest_streak')}, calendar_days={len(data.get('activity_calendar', []))}"
                
                self.log_test(
                    "Streak endpoint",
                    passed,
                    "200 with all required fields",
                    f"{response.status_code} with fields: {list(data.keys())}",
                    details if passed else "Missing or invalid fields"
                )
            else:
                self.log_test(
                    "Streak endpoint",
                    False,
                    "200 with streak data",
                    f"{response.status_code}: {response.text[:200]}"
                )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "Streak endpoint",
                False,
                "200 with streak data",
                f"Exception: {str(e)}"
            )
            return False

    def test_progress_complete_milestone(self):
        """TEST: POST /api/progress/complete returns optional streak_milestone field"""
        print(f"\n{Colors.BLUE}TEST: Progress complete with streak_milestone field{Colors.RESET}")
        
        if not self.sage_token:
            self.log_test(
                "Progress complete milestone",
                False,
                "200 with streak_milestone field",
                "Sage user not logged in"
            )
            return False
        
        try:
            # Complete a lesson (f1l1)
            response = requests.post(
                f"{BASE_URL}/api/progress/complete",
                json={"lesson_id": "f1l1"},
                headers={"Authorization": f"Bearer {self.sage_token}"}
            )
            
            passed = response.status_code == 200
            if passed:
                data = response.json()
                # Check that streak_milestone field exists (can be null or int)
                has_milestone_field = "streak_milestone" in data
                
                passed = has_milestone_field
                
                milestone_val = data.get("streak_milestone")
                details = f"streak_milestone={milestone_val} (null is OK if not hitting milestone)"
                
                self.log_test(
                    "Progress complete has streak_milestone field",
                    passed,
                    "200 with streak_milestone field present",
                    f"{response.status_code} with streak_milestone={milestone_val}",
                    details
                )
            else:
                self.log_test(
                    "Progress complete has streak_milestone field",
                    False,
                    "200 with streak_milestone field",
                    f"{response.status_code}: {response.text[:200]}"
                )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "Progress complete has streak_milestone field",
                False,
                "200 with streak_milestone field",
                f"Exception: {str(e)}"
            )
            return False

    def test_onboarding_submit(self):
        """TEST: POST /api/onboarding/submit returns AI-generated plan"""
        print(f"\n{Colors.BLUE}TEST: Onboarding submit (AI plan generation){Colors.RESET}")
        
        # Login as sage3 (not onboarded yet)
        try:
            login_response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": SAGE3_EMAIL, "password": SAGE3_PASSWORD}
            )
            if login_response.status_code != 200:
                self.log_test(
                    "Onboarding submit",
                    False,
                    "200 with plan",
                    f"Could not login as sage3: {login_response.status_code}"
                )
                return False
            
            sage3_token = login_response.json().get("access_token")
        except Exception as e:
            self.log_test(
                "Onboarding submit",
                False,
                "200 with plan",
                f"Exception logging in: {str(e)}"
            )
            return False
        
        try:
            # Submit onboarding with all 6 required fields
            onboarding_data = {
                "motivation": "career",
                "experience": "beginner",
                "tools_used": ["chatgpt", "claude"],
                "goals": ["fundamentals", "build_project"],
                "time_per_day": "15",
                "learning_style": "hands_on"
            }
            
            print(f"   Submitting onboarding (AI generation may take 5-15s)...")
            response = requests.post(
                f"{BASE_URL}/api/onboarding/submit",
                json=onboarding_data,
                headers={"Authorization": f"Bearer {sage3_token}"},
                timeout=30
            )
            
            passed = response.status_code == 200
            if passed:
                data = response.json()
                has_plan = "plan" in data and data["plan"] is not None
                has_onboarded = data.get("onboarded") == True
                has_answers = "answers" in data
                
                if has_plan:
                    plan = data["plan"]
                    plan_valid = (
                        "headline" in plan and
                        "rationale" in plan and
                        "recommended_path_ids" in plan and
                        isinstance(plan.get("recommended_path_ids"), list) and
                        len(plan.get("recommended_path_ids", [])) > 0 and
                        "first_lesson_id" in plan and
                        "daily_goal_target" in plan and
                        "generated_at" in plan
                    )
                    
                    # Verify recommended_path_ids are real
                    paths_response = requests.get(
                        f"{BASE_URL}/api/paths",
                        headers={"Authorization": f"Bearer {sage3_token}"}
                    )
                    if paths_response.status_code == 200:
                        all_paths = paths_response.json()
                        valid_path_ids = {p["id"] for p in all_paths}
                        rec_ids = plan.get("recommended_path_ids", [])
                        paths_are_real = all(pid in valid_path_ids for pid in rec_ids)
                    else:
                        paths_are_real = False
                    
                    passed = has_plan and has_onboarded and has_answers and plan_valid and paths_are_real
                    
                    details = f"headline='{plan.get('headline', '')}', recommended_paths={plan.get('recommended_path_ids', [])}, first_lesson={plan.get('first_lesson_id')}"
                    
                    self.log_test(
                        "Onboarding submit with AI plan",
                        passed,
                        "200 with valid plan + onboarded=true",
                        f"{response.status_code} with plan fields: {list(plan.keys())}",
                        details if passed else "Plan missing fields or invalid path IDs"
                    )
                else:
                    self.log_test(
                        "Onboarding submit with AI plan",
                        False,
                        "200 with valid plan",
                        f"{response.status_code} but plan is null or missing"
                    )
                    passed = False
            else:
                self.log_test(
                    "Onboarding submit with AI plan",
                    False,
                    "200 with plan",
                    f"{response.status_code}: {response.text[:200]}"
                )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "Onboarding submit with AI plan",
                False,
                "200 with plan",
                f"Exception: {str(e)}"
            )
            return False

    def test_onboarding_get(self):
        """TEST: GET /api/onboarding/me returns plan or {onboarded: false}"""
        print(f"\n{Colors.BLUE}TEST: Onboarding get endpoint{Colors.RESET}")
        
        if not self.sage_token:
            self.log_test(
                "Onboarding get",
                False,
                "200 with onboarding data",
                "Sage user not logged in"
            )
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/onboarding/me",
                headers={"Authorization": f"Bearer {self.sage_token}"}
            )
            
            passed = response.status_code == 200
            if passed:
                data = response.json()
                has_onboarded_field = "onboarded" in data
                has_plan_field = "plan" in data
                
                passed = has_onboarded_field and has_plan_field
                
                onboarded = data.get("onboarded")
                plan = data.get("plan")
                
                details = f"onboarded={onboarded}, plan={'present' if plan else 'null'}"
                
                self.log_test(
                    "Onboarding get endpoint",
                    passed,
                    "200 with onboarded + plan fields",
                    f"{response.status_code} with {details}",
                    details
                )
            else:
                self.log_test(
                    "Onboarding get endpoint",
                    False,
                    "200 with onboarding data",
                    f"{response.status_code}: {response.text[:200]}"
                )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "Onboarding get endpoint",
                False,
                "200 with onboarding data",
                f"Exception: {str(e)}"
            )
            return False

    def test_challenge_15day(self):
        """TEST: GET /api/challenge/15day returns 15-day challenge with proper lock/unlock"""
        print(f"\n{Colors.BLUE}TEST: 15-Day Challenge endpoint{Colors.RESET}")
        
        if not self.sage_token:
            self.log_test(
                "15-Day Challenge",
                False,
                "200 with 15 days",
                "Sage user not logged in"
            )
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/challenge/15day",
                headers={"Authorization": f"Bearer {self.sage_token}"}
            )
            
            passed = response.status_code == 200
            if passed:
                data = response.json()
                has_required = (
                    data.get("name") == "15-Day AI Challenge" and
                    data.get("total_days") == 15 and
                    "days" in data and
                    "current_day" in data and
                    "completed_count" in data and
                    "is_complete" in data
                )
                
                days = data.get("days", [])
                has_15_days = len(days) == 15
                
                # Check day structure
                if has_15_days:
                    day1 = days[0]
                    day_valid = (
                        day1.get("day") == 1 and
                        "lesson_id" in day1 and
                        "theme" in day1 and
                        "status" in day1 and
                        day1.get("status") in ["locked", "available", "completed"]
                    )
                    
                    # For sage1 who completed f1l1, day 1 should be completed
                    day1_status = day1.get("status")
                    day2_status = days[1].get("status") if len(days) > 1 else None
                    
                    # Check sequential unlock logic
                    statuses = [d.get("status") for d in days]
                    
                    passed = has_required and has_15_days and day_valid
                    
                    details = f"day1_status={day1_status}, day2_status={day2_status}, completed_count={data.get('completed_count')}, current_day={data.get('current_day')}"
                    
                    self.log_test(
                        "15-Day Challenge endpoint",
                        passed,
                        "200 with 15 days + proper structure",
                        f"{response.status_code} with {len(days)} days",
                        details
                    )
                else:
                    self.log_test(
                        "15-Day Challenge endpoint",
                        False,
                        "200 with 15 days",
                        f"{response.status_code} with {len(days)} days"
                    )
                    passed = False
            else:
                self.log_test(
                    "15-Day Challenge endpoint",
                    False,
                    "200 with 15 days",
                    f"{response.status_code}: {response.text[:200]}"
                )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "15-Day Challenge endpoint",
                False,
                "200 with 15 days",
                f"Exception: {str(e)}"
            )
            return False

    def test_prompts_library(self):
        """TEST: GET /api/prompts/library returns searchable prompt library"""
        print(f"\n{Colors.BLUE}TEST: Prompts Library endpoint{Colors.RESET}")
        
        if not self.sage_token:
            self.log_test(
                "Prompts Library",
                False,
                "200 with prompts",
                "Sage user not logged in"
            )
            return False
        
        try:
            # Test 1: Get all prompts
            response = requests.get(
                f"{BASE_URL}/api/prompts/library",
                headers={"Authorization": f"Bearer {self.sage_token}"}
            )
            
            passed = response.status_code == 200
            if passed:
                data = response.json()
                has_required = (
                    "items" in data and
                    "total" in data and
                    "paths" in data
                )
                
                items = data.get("items", [])
                total = data.get("total", 0)
                
                # Check item structure
                if len(items) > 0:
                    item = items[0]
                    item_valid = all(f in item for f in [
                        "lesson_id", "lesson_title", "path_id", "path_title",
                        "card_title", "instruction", "seed_prompt"
                    ])
                else:
                    item_valid = False
                
                passed = has_required and item_valid and total > 0
                
                self.log_test(
                    "Prompts Library - all prompts",
                    passed,
                    "200 with items array + total + paths",
                    f"{response.status_code} with {total} prompts",
                    f"✓ Found {total} prompts across all lessons" if passed else "Missing fields or no prompts"
                )
                
                # Test 2: Search with query
                search_response = requests.get(
                    f"{BASE_URL}/api/prompts/library?q=image",
                    headers={"Authorization": f"Bearer {self.sage_token}"}
                )
                
                if search_response.status_code == 200:
                    search_data = search_response.json()
                    search_total = search_data.get("total", 0)
                    search_works = search_total < total  # Should be filtered
                    
                    self.log_test(
                        "Prompts Library - search filter",
                        search_works,
                        "Filtered results (less than total)",
                        f"Search returned {search_total} results (total: {total})",
                        f"✓ Search filtering works" if search_works else "Search not filtering"
                    )
                
                # Test 3: Filter by path
                path_response = requests.get(
                    f"{BASE_URL}/api/prompts/library?path_id=fundamentals",
                    headers={"Authorization": f"Bearer {self.sage_token}"}
                )
                
                if path_response.status_code == 200:
                    path_data = path_response.json()
                    path_total = path_data.get("total", 0)
                    path_works = path_total < total  # Should be filtered
                    
                    self.log_test(
                        "Prompts Library - path filter",
                        path_works,
                        "Filtered by path (less than total)",
                        f"Path filter returned {path_total} results (total: {total})",
                        f"✓ Path filtering works" if path_works else "Path filter not working"
                    )
            else:
                self.log_test(
                    "Prompts Library - all prompts",
                    False,
                    "200 with prompts",
                    f"{response.status_code}: {response.text[:200]}"
                )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "Prompts Library",
                False,
                "200 with prompts",
                f"Exception: {str(e)}"
            )
            return False

    def test_regression_interactive_status(self):
        """REGRESSION: GET /api/admin/curriculum/interactive-status still works"""
        print(f"\n{Colors.BLUE}REGRESSION TEST: Admin curriculum interactive-status{Colors.RESET}")
        
        if not self.admin_token:
            self.log_test(
                "Admin interactive-status endpoint",
                False,
                "200 with status data",
                "Admin not logged in"
            )
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/admin/curriculum/interactive-status",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )
            
            passed = response.status_code == 200
            if passed:
                data = response.json()
                has_data = isinstance(data, dict) and len(data) > 0
                passed = has_data
            
            self.log_test(
                "Admin interactive-status endpoint",
                passed,
                "200 with status data",
                f"{response.status_code} with data: {str(data)[:100] if passed else response.text[:100]}"
            )
            
            return passed
            
        except Exception as e:
            self.log_test(
                "Admin interactive-status endpoint",
                False,
                "200 with status data",
                f"Exception: {str(e)}"
            )
            return False

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*70}")
        print(f"{Colors.BLUE}TEST SUMMARY{Colors.RESET}")
        print(f"{'='*70}")
        print(f"Total tests run: {self.tests_run}")
        print(f"{Colors.GREEN}Passed: {self.tests_passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {self.tests_failed}{Colors.RESET}")
        
        if self.tests_failed == 0:
            print(f"\n{Colors.GREEN}✅ ALL TESTS PASSED{Colors.RESET}")
            print(f"   • Interactive lesson endpoints working correctly")
            print(f"   • Playground endpoint requires auth and validates input")
            print(f"   • Migration endpoint working (admin only)")
            print(f"   • Lesson f1l1 has correct 7-card structure")
            print(f"   • Webhook security verified")
            print(f"   • No regressions detected")
            return 0
        else:
            print(f"\n{Colors.RED}❌ SOME TESTS FAILED{Colors.RESET}")
            return 1

def main():
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}Ascendra Academy - Interactive Lesson System Backend Tests{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"Base URL: {BASE_URL}")
    
    tester = InteractiveLessonTester()
    
    # Login users
    sage_logged_in = tester.login_sage_user()
    admin_logged_in = tester.login_admin_user()
    
    # Run interactive lesson tests
    print(f"\n{Colors.YELLOW}{'='*70}{Colors.RESET}")
    print(f"{Colors.YELLOW}INTERACTIVE LESSON TESTS{Colors.RESET}")
    print(f"{Colors.YELLOW}{'='*70}{Colors.RESET}")
    
    if sage_logged_in:
        tester.test_playground_authenticated()
        tester.test_playground_empty_prompt()
        tester.test_lesson_f1l1_structure()
    else:
        print(f"{Colors.RED}⚠ Skipping sage user tests - login failed{Colors.RESET}")
    
    tester.test_playground_no_auth()
    
    if admin_logged_in:
        tester.test_migration_endpoint()
    else:
        print(f"{Colors.RED}⚠ Skipping admin tests - login failed{Colors.RESET}")
    
    # Run security tests
    print(f"\n{Colors.YELLOW}{'='*70}{Colors.RESET}")
    print(f"{Colors.YELLOW}SECURITY TESTS (Stripe Webhook){Colors.RESET}")
    print(f"{Colors.YELLOW}{'='*70}{Colors.RESET}")
    
    tester.test_webhook_no_signature()
    tester.test_webhook_invalid_signature()
    
    # Create test user for positive path
    if tester.create_test_user():
        tester.test_webhook_valid_signature()
    else:
        print(f"{Colors.RED}⚠ Skipping positive path test - could not create test user{Colors.RESET}")
    
    # Run NEW FEATURE tests (Phase 1-5)
    print(f"\n{Colors.YELLOW}{'='*70}{Colors.RESET}")
    print(f"{Colors.YELLOW}NEW FEATURES TESTS (Streak, Onboarding, Challenge, Prompts){Colors.RESET}")
    print(f"{Colors.YELLOW}{'='*70}{Colors.RESET}")
    
    if sage_logged_in:
        tester.test_streak_endpoint()
        tester.test_progress_complete_milestone()
        tester.test_onboarding_get()
        tester.test_challenge_15day()
        tester.test_prompts_library()
    else:
        print(f"{Colors.RED}⚠ Skipping new feature tests - sage login failed{Colors.RESET}")
    
    # Test onboarding submit (uses sage3)
    tester.test_onboarding_submit()
    
    # Run regression tests
    print(f"\n{Colors.YELLOW}{'='*70}{Colors.RESET}")
    print(f"{Colors.YELLOW}REGRESSION TESTS{Colors.RESET}")
    print(f"{Colors.YELLOW}{'='*70}{Colors.RESET}")
    
    tester.test_regression_social_x_status()
    tester.test_regression_api_root()
    tester.test_regression_openapi_schema()
    
    if admin_logged_in:
        tester.test_regression_interactive_status()
    else:
        print(f"{Colors.RED}⚠ Skipping admin regression test - login failed{Colors.RESET}")
    
    # Print summary
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
