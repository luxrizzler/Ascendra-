"""
Ascendra Academy - Stripe Webhook Security Fix Verification
P0 Security Bug: Verify webhook handler correctly rejects unsigned/forged payloads
and still accepts genuinely-signed payloads.
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

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class WebhookSecurityTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.admin_token = None
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

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*70}")
        print(f"{Colors.BLUE}TEST SUMMARY{Colors.RESET}")
        print(f"{'='*70}")
        print(f"Total tests run: {self.tests_run}")
        print(f"{Colors.GREEN}Passed: {self.tests_passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {self.tests_failed}{Colors.RESET}")
        
        if self.tests_failed == 0:
            print(f"\n{Colors.GREEN}✅ ALL TESTS PASSED - P0 Security Fix Verified{Colors.RESET}")
            print(f"   • Unsigned webhooks are rejected (400)")
            print(f"   • Invalid signatures are rejected (400)")
            print(f"   • Valid signatures are accepted and processed (200)")
            print(f"   • No regressions detected")
            return 0
        else:
            print(f"\n{Colors.RED}❌ SOME TESTS FAILED{Colors.RESET}")
            return 1

def main():
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}Ascendra Academy - Stripe Webhook Security Fix Verification{Colors.RESET}")
    print(f"{Colors.BLUE}P0 Security Bug: Verify mandatory signature verification{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"Base URL: {BASE_URL}")
    print(f"Webhook Secret: {WEBHOOK_SECRET[:10]}...{WEBHOOK_SECRET[-4:]}")
    
    tester = WebhookSecurityTester()
    
    # Run security tests
    print(f"\n{Colors.YELLOW}{'='*70}{Colors.RESET}")
    print(f"{Colors.YELLOW}SECURITY TESTS (P0 Fix Verification){Colors.RESET}")
    print(f"{Colors.YELLOW}{'='*70}{Colors.RESET}")
    
    tester.test_webhook_no_signature()
    tester.test_webhook_invalid_signature()
    
    # Create test user for positive path
    if tester.create_test_user():
        tester.test_webhook_valid_signature()
    else:
        print(f"{Colors.RED}⚠ Skipping positive path test - could not create test user{Colors.RESET}")
    
    # Run regression tests
    print(f"\n{Colors.YELLOW}{'='*70}{Colors.RESET}")
    print(f"{Colors.YELLOW}REGRESSION TESTS{Colors.RESET}")
    print(f"{Colors.YELLOW}{'='*70}{Colors.RESET}")
    
    tester.test_regression_social_x_status()
    tester.test_regression_api_root()
    tester.test_regression_openapi_schema()
    
    # Print summary
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
