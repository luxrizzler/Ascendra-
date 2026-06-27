"""
Ascendra Academy - Interactive Lesson Generator Backend Tests
Tests for:
- GET /api/admin/curriculum/interactive-status (admin auth)
- POST /api/admin/curriculum/generate-interactive (admin auth, idempotency)
- GET /api/lessons/{lesson_id} for auto-generated lessons (b1l1, p1l1, c2l1, f2l1, en1l1)
- Card structure validation (knowledge_check, fill_blank, playground)
- MongoDB interactive_v field verification
- Regression tests (playground, billing webhook, f1l1 unchanged, social X status)
"""
import requests
import json
import hmac
import hashlib
import sys
from datetime import datetime
from pymongo import MongoClient

# Configuration
BASE_URL = "https://repo-to-site-2.preview.emergentagent.com"
WEBHOOK_SECRET = "whsec_pP6zR3wzRFmP74btq3NRaTHanbdK4q6J"
ADMIN_EMAIL = "admin@ascendraacademy.com"
ADMIN_PASSWORD = "AscendraAdmin2026!"
SAGE_EMAIL = "sage1@ascendraacademy.com"
SAGE_PASSWORD = "test1"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "ascendra_db"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class InteractiveGeneratorTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.admin_token = None
        self.sage_token = None
        self.mongo_client = None
        self.db = None

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

    def setup_mongo(self):
        """Connect to MongoDB"""
        print(f"\n{Colors.BLUE}SETUP: Connecting to MongoDB{Colors.RESET}")
        try:
            self.mongo_client = MongoClient(MONGO_URL)
            self.db = self.mongo_client[DB_NAME]
            # Test connection
            self.db.command('ping')
            print(f"{Colors.GREEN}✓{Colors.RESET} Connected to MongoDB")
            return True
        except Exception as e:
            print(f"{Colors.RED}✗{Colors.RESET} MongoDB connection failed: {str(e)}")
            return False

    def login_admin(self):
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
                print(f"{Colors.RED}✗{Colors.RESET} Failed to login: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"{Colors.RED}✗{Colors.RESET} Exception: {str(e)}")
            return False

    def login_sage(self):
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

    # ========== NEW FEATURE TESTS ==========

    def test_interactive_status_endpoint(self):
        """TEST: GET /api/admin/curriculum/interactive-status returns correct structure"""
        print(f"\n{Colors.BLUE}TEST: Interactive status endpoint{Colors.RESET}")
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/admin/curriculum/interactive-status",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )
            
            passed = response.status_code == 200
            self.log_test(
                "Interactive status endpoint returns 200",
                passed,
                "200",
                str(response.status_code),
                f"Response: {response.text[:200]}"
            )
            
            if passed:
                data = response.json()
                # Check required fields
                required_fields = ["running", "upgraded", "failed", "total", "last_run_at", "last_result", "coverage"]
                for field in required_fields:
                    field_exists = field in data
                    self.log_test(
                        f"Status response has '{field}' field",
                        field_exists,
                        f"'{field}' present",
                        f"'{field}' {'present' if field_exists else 'missing'}",
                        f"Value: {data.get(field)}"
                    )
                
                # Check coverage structure
                if "coverage" in data:
                    coverage = data["coverage"]
                    has_interactive = "interactive" in coverage
                    has_total = "total" in coverage
                    self.log_test(
                        "Coverage has 'interactive' and 'total' fields",
                        has_interactive and has_total,
                        "Both fields present",
                        f"interactive: {has_interactive}, total: {has_total}",
                        f"Coverage: {coverage}"
                    )
                    
                    # CRITICAL: Check if all lessons are upgraded (39/39)
                    if has_interactive and has_total:
                        all_upgraded = coverage["interactive"] == coverage["total"]
                        self.log_test(
                            "All lessons are interactive (coverage.interactive == coverage.total)",
                            all_upgraded,
                            f"{coverage['total']}/{coverage['total']}",
                            f"{coverage['interactive']}/{coverage['total']}",
                            f"Expected 39/39 based on preview run"
                        )
                
                return data
        except Exception as e:
            self.log_test(
                "Interactive status endpoint",
                False,
                "Success",
                f"Exception: {str(e)}"
            )
            return None

    def test_interactive_status_auth(self):
        """TEST: GET /api/admin/curriculum/interactive-status requires admin auth"""
        print(f"\n{Colors.BLUE}TEST: Interactive status endpoint auth requirement{Colors.RESET}")
        
        # Test without token
        try:
            response = requests.get(f"{BASE_URL}/api/admin/curriculum/interactive-status")
            passed = response.status_code in [401, 403]
            self.log_test(
                "Status endpoint rejects unauthenticated request",
                passed,
                "401 or 403",
                str(response.status_code)
            )
        except Exception as e:
            self.log_test("Status endpoint auth (no token)", False, "401/403", f"Exception: {str(e)}")
        
        # Test with sage token (non-admin)
        try:
            response = requests.get(
                f"{BASE_URL}/api/admin/curriculum/interactive-status",
                headers={"Authorization": f"Bearer {self.sage_token}"}
            )
            passed = response.status_code == 403
            self.log_test(
                "Status endpoint rejects non-admin user",
                passed,
                "403",
                str(response.status_code)
            )
        except Exception as e:
            self.log_test("Status endpoint auth (sage user)", False, "403", f"Exception: {str(e)}")

    def test_generate_interactive_idempotency(self):
        """TEST: POST /api/admin/curriculum/generate-interactive is idempotent"""
        print(f"\n{Colors.BLUE}TEST: Generate interactive endpoint (idempotency){Colors.RESET}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/admin/curriculum/generate-interactive",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )
            
            passed = response.status_code == 200
            self.log_test(
                "Generate interactive endpoint returns 200",
                passed,
                "200",
                str(response.status_code),
                f"Response: {response.text[:200]}"
            )
            
            if passed:
                data = response.json()
                # Should return either "started" or "already_running"
                status = data.get("status")
                valid_status = status in ["started", "already_running"]
                self.log_test(
                    "Generate returns valid status",
                    valid_status,
                    "'started' or 'already_running'",
                    f"'{status}'",
                    f"Full response: {data}"
                )
                
                # Since all lessons are already upgraded, it should complete quickly with 0 work
                # Wait a bit and check status
                import time
                time.sleep(3)
                
                status_response = requests.get(
                    f"{BASE_URL}/api/admin/curriculum/interactive-status",
                    headers={"Authorization": f"Bearer {self.admin_token}"}
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    # Should have completed with 0 upgraded (all skipped)
                    upgraded = status_data.get("upgraded", -1)
                    total_attempted = status_data.get("total", -1)
                    
                    # Idempotent run should have 0 upgraded and 0 total_attempted
                    idempotent = upgraded == 0 and total_attempted == 0
                    self.log_test(
                        "Idempotent run completes with 0 work (all lessons already upgraded)",
                        idempotent,
                        "upgraded: 0, total_attempted: 0",
                        f"upgraded: {upgraded}, total_attempted: {total_attempted}",
                        f"All lessons should be skipped since they're already upgraded"
                    )
                
                return data
        except Exception as e:
            self.log_test(
                "Generate interactive endpoint",
                False,
                "Success",
                f"Exception: {str(e)}"
            )
            return None

    def test_generate_interactive_auth(self):
        """TEST: POST /api/admin/curriculum/generate-interactive requires admin auth"""
        print(f"\n{Colors.BLUE}TEST: Generate interactive endpoint auth requirement{Colors.RESET}")
        
        # Test without token
        try:
            response = requests.post(f"{BASE_URL}/api/admin/curriculum/generate-interactive")
            passed = response.status_code in [401, 403]
            self.log_test(
                "Generate endpoint rejects unauthenticated request",
                passed,
                "401 or 403",
                str(response.status_code)
            )
        except Exception as e:
            self.log_test("Generate endpoint auth (no token)", False, "401/403", f"Exception: {str(e)}")
        
        # Test with sage token (non-admin)
        try:
            response = requests.post(
                f"{BASE_URL}/api/admin/curriculum/generate-interactive",
                headers={"Authorization": f"Bearer {self.sage_token}"}
            )
            passed = response.status_code == 403
            self.log_test(
                "Generate endpoint rejects non-admin user",
                passed,
                "403",
                str(response.status_code)
            )
        except Exception as e:
            self.log_test("Generate endpoint auth (sage user)", False, "403", f"Exception: {str(e)}")

    def test_lesson_structure(self, lesson_id):
        """TEST: GET /api/lessons/{lesson_id} returns interactive cards"""
        print(f"\n{Colors.BLUE}TEST: Lesson {lesson_id} structure{Colors.RESET}")
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/lessons/{lesson_id}",
                headers={"Authorization": f"Bearer {self.sage_token}"}
            )
            
            passed = response.status_code == 200
            self.log_test(
                f"Lesson {lesson_id} endpoint returns 200",
                passed,
                "200",
                str(response.status_code)
            )
            
            if passed:
                lesson = response.json()
                cards = lesson.get("cards", [])
                
                # Check for interactive card types
                card_kinds = [c.get("kind", "text") for c in cards]
                has_knowledge_check = "knowledge_check" in card_kinds
                has_fill_blank = "fill_blank" in card_kinds
                has_playground = "playground" in card_kinds
                
                self.log_test(
                    f"Lesson {lesson_id} has knowledge_check card",
                    has_knowledge_check,
                    "knowledge_check present",
                    f"{'present' if has_knowledge_check else 'missing'}",
                    f"Card kinds: {card_kinds}"
                )
                
                self.log_test(
                    f"Lesson {lesson_id} has fill_blank card",
                    has_fill_blank,
                    "fill_blank present",
                    f"{'present' if has_fill_blank else 'missing'}",
                    f"Card kinds: {card_kinds}"
                )
                
                self.log_test(
                    f"Lesson {lesson_id} has playground card",
                    has_playground,
                    "playground present",
                    f"{'present' if has_playground else 'missing'}",
                    f"Card kinds: {card_kinds}"
                )
                
                # Validate card structures
                for card in cards:
                    kind = card.get("kind", "text")
                    
                    if kind == "knowledge_check":
                        self.validate_knowledge_check_card(card, lesson_id)
                    elif kind == "fill_blank":
                        self.validate_fill_blank_card(card, lesson_id)
                    elif kind == "playground":
                        self.validate_playground_card(card, lesson_id)
                
                return lesson
        except Exception as e:
            self.log_test(
                f"Lesson {lesson_id} structure",
                False,
                "Success",
                f"Exception: {str(e)}"
            )
            return None

    def validate_knowledge_check_card(self, card, lesson_id):
        """Validate knowledge_check card structure"""
        question = card.get("question", "")
        options = card.get("options", [])
        answer_index = card.get("answer_index")
        explanation = card.get("explanation", "")
        
        # Question must be non-empty string
        valid_question = isinstance(question, str) and len(question) > 0
        self.log_test(
            f"Lesson {lesson_id} knowledge_check has valid question",
            valid_question,
            "non-empty string",
            f"'{question[:50]}...'" if valid_question else "invalid"
        )
        
        # Options must be list of exactly 4 non-empty strings
        valid_options = (
            isinstance(options, list) and 
            len(options) == 4 and 
            all(isinstance(o, str) and len(o) > 0 for o in options)
        )
        self.log_test(
            f"Lesson {lesson_id} knowledge_check has 4 valid options",
            valid_options,
            "list of 4 non-empty strings",
            f"{len(options)} options" if isinstance(options, list) else "invalid"
        )
        
        # Answer index must be int between 0 and 3
        valid_answer = isinstance(answer_index, int) and 0 <= answer_index <= 3
        self.log_test(
            f"Lesson {lesson_id} knowledge_check has valid answer_index",
            valid_answer,
            "int between 0 and 3",
            str(answer_index)
        )
        
        # Explanation must be string (can be empty)
        valid_explanation = isinstance(explanation, str)
        self.log_test(
            f"Lesson {lesson_id} knowledge_check has explanation",
            valid_explanation,
            "string",
            f"'{explanation[:50]}...'" if valid_explanation else "invalid"
        )

    def validate_fill_blank_card(self, card, lesson_id):
        """Validate fill_blank card structure"""
        prompt = card.get("prompt", "")
        answer = card.get("answer", "")
        aliases = card.get("aliases", [])
        explanation = card.get("explanation", "")
        
        # Prompt must contain '___'
        valid_prompt = isinstance(prompt, str) and "___" in prompt
        self.log_test(
            f"Lesson {lesson_id} fill_blank has valid prompt with '___'",
            valid_prompt,
            "string containing '___'",
            f"'{prompt[:50]}...'" if isinstance(prompt, str) else "invalid"
        )
        
        # Answer must be non-empty string
        valid_answer = isinstance(answer, str) and len(answer) > 0
        self.log_test(
            f"Lesson {lesson_id} fill_blank has valid answer",
            valid_answer,
            "non-empty string",
            f"'{answer}'" if valid_answer else "invalid"
        )
        
        # Aliases must be list of strings (can be empty)
        valid_aliases = isinstance(aliases, list) and all(isinstance(a, str) for a in aliases)
        self.log_test(
            f"Lesson {lesson_id} fill_blank has valid aliases",
            valid_aliases,
            "list of strings",
            f"{len(aliases)} aliases" if valid_aliases else "invalid"
        )
        
        # Explanation must be string
        valid_explanation = isinstance(explanation, str)
        self.log_test(
            f"Lesson {lesson_id} fill_blank has explanation",
            valid_explanation,
            "string",
            f"'{explanation[:50]}...'" if valid_explanation else "invalid"
        )

    def validate_playground_card(self, card, lesson_id):
        """Validate playground card structure"""
        instruction = card.get("instruction", "")
        seed_prompt = card.get("seed_prompt", "")
        system = card.get("system", "")
        
        # Instruction must be non-empty string
        valid_instruction = isinstance(instruction, str) and len(instruction) > 0
        self.log_test(
            f"Lesson {lesson_id} playground has valid instruction",
            valid_instruction,
            "non-empty string",
            f"'{instruction[:50]}...'" if valid_instruction else "invalid"
        )
        
        # Seed prompt must be string (can be empty)
        valid_seed = isinstance(seed_prompt, str)
        self.log_test(
            f"Lesson {lesson_id} playground has seed_prompt",
            valid_seed,
            "string",
            f"'{seed_prompt[:50]}...'" if valid_seed else "invalid"
        )
        
        # System must be string (can be empty)
        valid_system = isinstance(system, str)
        self.log_test(
            f"Lesson {lesson_id} playground has system",
            valid_system,
            "string",
            f"'{system[:50]}...'" if valid_system else "invalid"
        )

    def test_mongodb_interactive_v(self, lesson_id):
        """TEST: MongoDB lesson document has interactive_v: 1"""
        print(f"\n{Colors.BLUE}TEST: MongoDB interactive_v field for {lesson_id}{Colors.RESET}")
        
        if self.db is None:
            self.log_test(
                f"MongoDB check for {lesson_id}",
                False,
                "interactive_v: 1",
                "MongoDB not connected"
            )
            return
        
        try:
            # Find the lesson in curriculum_paths collection
            path_doc = self.db["curriculum_paths"].find_one(
                {"modules.lessons.id": lesson_id},
                {"modules.$": 1}
            )
            
            if not path_doc:
                self.log_test(
                    f"Lesson {lesson_id} found in MongoDB",
                    False,
                    "Lesson found",
                    "Lesson not found"
                )
                return
            
            # Extract the lesson
            lesson = None
            for module in path_doc.get("modules", []):
                for lsn in module.get("lessons", []):
                    if lsn.get("id") == lesson_id:
                        lesson = lsn
                        break
                if lesson:
                    break
            
            if lesson:
                interactive_v = lesson.get("interactive_v", 0)
                passed = interactive_v >= 1
                self.log_test(
                    f"Lesson {lesson_id} has interactive_v >= 1 in MongoDB",
                    passed,
                    "interactive_v: 1",
                    f"interactive_v: {interactive_v}"
                )
            else:
                self.log_test(
                    f"Lesson {lesson_id} extracted from MongoDB",
                    False,
                    "Lesson extracted",
                    "Could not extract lesson"
                )
        except Exception as e:
            self.log_test(
                f"MongoDB check for {lesson_id}",
                False,
                "interactive_v: 1",
                f"Exception: {str(e)}"
            )

    # ========== REGRESSION TESTS ==========

    def test_playground_endpoint(self):
        """REGRESSION: POST /api/playground/run still works"""
        print(f"\n{Colors.BLUE}REGRESSION: Playground endpoint{Colors.RESET}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/playground/run",
                headers={"Authorization": f"Bearer {self.sage_token}"},
                json={"prompt": "What is AI?"}
            )
            
            passed = response.status_code == 200
            self.log_test(
                "Playground endpoint returns 200",
                passed,
                "200",
                str(response.status_code)
            )
            
            if passed:
                data = response.json()
                has_response = "response" in data and isinstance(data["response"], str) and len(data["response"]) > 0
                self.log_test(
                    "Playground returns valid response",
                    has_response,
                    "non-empty response string",
                    f"response length: {len(data.get('response', ''))}"
                )
        except Exception as e:
            self.log_test(
                "Playground endpoint",
                False,
                "Success",
                f"Exception: {str(e)}"
            )

    def test_billing_webhook_security(self):
        """REGRESSION: /api/billing/webhook rejects unsigned payloads"""
        print(f"\n{Colors.BLUE}REGRESSION: Billing webhook security{Colors.RESET}")
        
        try:
            # Send unsigned payload
            response = requests.post(
                f"{BASE_URL}/api/billing/webhook",
                json={"type": "checkout.session.completed", "data": {"object": {"id": "fake"}}}
            )
            
            passed = response.status_code == 400
            self.log_test(
                "Webhook rejects unsigned payload with 400",
                passed,
                "400",
                str(response.status_code)
            )
        except Exception as e:
            self.log_test(
                "Webhook security",
                False,
                "400",
                f"Exception: {str(e)}"
            )

    def test_lesson_f1l1_unchanged(self):
        """REGRESSION: Lesson f1l1 (hand-tuned) still has original 7 cards"""
        print(f"\n{Colors.BLUE}REGRESSION: Lesson f1l1 unchanged{Colors.RESET}")
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/lessons/f1l1",
                headers={"Authorization": f"Bearer {self.sage_token}"}
            )
            
            passed = response.status_code == 200
            self.log_test(
                "Lesson f1l1 endpoint returns 200",
                passed,
                "200",
                str(response.status_code)
            )
            
            if passed:
                lesson = response.json()
                cards = lesson.get("cards", [])
                card_kinds = [c.get("kind", "text") for c in cards]
                
                # Expected order: ['text','text','knowledge_check','text','fill_blank','text','playground']
                expected_order = ['text', 'text', 'knowledge_check', 'text', 'fill_blank', 'text', 'playground']
                
                correct_count = len(cards) == 7
                self.log_test(
                    "Lesson f1l1 has 7 cards",
                    correct_count,
                    "7 cards",
                    f"{len(cards)} cards"
                )
                
                correct_order = card_kinds == expected_order
                self.log_test(
                    "Lesson f1l1 has correct card order",
                    correct_order,
                    str(expected_order),
                    str(card_kinds),
                    "Hand-tuned lesson should not be modified by auto-generator"
                )
        except Exception as e:
            self.log_test(
                "Lesson f1l1 unchanged",
                False,
                "Success",
                f"Exception: {str(e)}"
            )

    def test_social_x_status(self):
        """REGRESSION: /api/admin/social/x/status still returns ok:true"""
        print(f"\n{Colors.BLUE}REGRESSION: Social X status endpoint{Colors.RESET}")
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/admin/social/x/status",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )
            
            passed = response.status_code == 200
            self.log_test(
                "Social X status endpoint returns 200",
                passed,
                "200",
                str(response.status_code)
            )
            
            if passed:
                data = response.json()
                ok_status = data.get("ok") == True
                self.log_test(
                    "Social X status returns ok:true",
                    ok_status,
                    "ok: true",
                    f"ok: {data.get('ok')}"
                )
        except Exception as e:
            self.log_test(
                "Social X status",
                False,
                "Success",
                f"Exception: {str(e)}"
            )

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print(f"{Colors.BLUE}TEST SUMMARY{Colors.RESET}")
        print(f"{'='*60}")
        print(f"Total tests run: {self.tests_run}")
        print(f"{Colors.GREEN}Passed: {self.tests_passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {self.tests_failed}{Colors.RESET}")
        
        if self.tests_failed == 0:
            print(f"\n{Colors.GREEN}✅ ALL TESTS PASSED!{Colors.RESET}")
            return 0
        else:
            print(f"\n{Colors.RED}❌ SOME TESTS FAILED{Colors.RESET}")
            return 1

def main():
    tester = InteractiveGeneratorTester()
    
    # Setup
    if not tester.setup_mongo():
        print(f"{Colors.RED}Failed to connect to MongoDB. Continuing without MongoDB tests.{Colors.RESET}")
    
    if not tester.login_admin():
        print(f"{Colors.RED}Failed to login as admin. Exiting.{Colors.RESET}")
        return 1
    
    if not tester.login_sage():
        print(f"{Colors.RED}Failed to login as sage user. Exiting.{Colors.RESET}")
        return 1
    
    # NEW FEATURE TESTS
    print(f"\n{'='*60}")
    print(f"{Colors.BLUE}NEW FEATURE TESTS{Colors.RESET}")
    print(f"{'='*60}")
    
    tester.test_interactive_status_endpoint()
    tester.test_interactive_status_auth()
    tester.test_generate_interactive_auth()
    tester.test_generate_interactive_idempotency()
    
    # Test specific lessons
    test_lessons = ["b1l1", "p1l1", "c2l1", "f2l1", "en1l1"]
    for lesson_id in test_lessons:
        tester.test_lesson_structure(lesson_id)
        if tester.db is not None:
            tester.test_mongodb_interactive_v(lesson_id)
    
    # REGRESSION TESTS
    print(f"\n{'='*60}")
    print(f"{Colors.BLUE}REGRESSION TESTS{Colors.RESET}")
    print(f"{'='*60}")
    
    tester.test_playground_endpoint()
    tester.test_billing_webhook_security()
    tester.test_lesson_f1l1_unchanged()
    tester.test_social_x_status()
    
    # Print summary
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
