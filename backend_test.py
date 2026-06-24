"""
Ascendra Academy Backend API Test Suite
Tests all endpoints: auth, paths, lessons, progress, models, tutor, certificates, billing, admin
"""
import requests
import sys
import time
from datetime import datetime

BASE_URL = "https://repo-to-site-2.preview.emergentagent.com/api"

class AscendraAPITester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.token = None
        self.user_id = None
        self.admin_token = None
        self.sage_token = None
        self.failed_tests = []
        
    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    
    def test(self, name, method, endpoint, expected_status, data=None, headers=None, token=None):
        """Run a single API test"""
        url = f"{BASE_URL}{endpoint}"
        h = headers or {}
        if token:
            h['Authorization'] = f'Bearer {token}'
        elif self.token and not headers:
            h['Authorization'] = f'Bearer {self.token}'
        
        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                r = requests.get(url, headers=h, timeout=30)
            elif method == 'POST':
                r = requests.post(url, json=data, headers=h, timeout=30)
            elif method == 'PUT':
                r = requests.put(url, json=data, headers=h, timeout=30)
            elif method == 'PATCH':
                r = requests.patch(url, json=data, headers=h, timeout=30)
            
            success = r.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASS - Status: {r.status_code}")
                try:
                    return True, r.json()
                except:
                    return True, {}
            else:
                self.tests_failed += 1
                self.failed_tests.append(f"{name} - Expected {expected_status}, got {r.status_code}")
                self.log(f"❌ FAIL - Expected {expected_status}, got {r.status_code}")
                try:
                    self.log(f"   Response: {r.text[:200]}")
                except:
                    pass
                return False, {}
        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(f"{name} - Error: {str(e)[:100]}")
            self.log(f"❌ FAIL - Error: {str(e)[:150]}")
            return False, {}
    
    def run_all_tests(self):
        self.log("=" * 60)
        self.log("ASCENDRA ACADEMY BACKEND API TEST SUITE")
        self.log("=" * 60)
        
        # 1. Health check
        self.log("\n📋 SECTION 1: HEALTH CHECK")
        self.test("Health check", "GET", "/", 200)
        
        # 2. Auth - Signup new user
        self.log("\n📋 SECTION 2: AUTH - SIGNUP & LOGIN")
        timestamp = int(time.time())
        test_email = f"e2e_{timestamp}@ascendraacademy.com"
        test_password = "password123"
        test_name = "E2E Tester"
        
        success, resp = self.test(
            "Signup new user",
            "POST",
            "/auth/signup",
            200,
            data={"email": test_email, "password": test_password, "name": test_name}
        )
        if success and 'access_token' in resp:
            self.token = resp['access_token']
            self.log(f"   ✓ Token obtained: {self.token[:20]}...")
        
        # 3. Auth - Get current user
        if self.token:
            success, resp = self.test("Get current user (/auth/me)", "GET", "/auth/me", 200)
            if success and 'id' in resp:
                self.user_id = resp['id']
                self.log(f"   ✓ User ID: {self.user_id}")
                self.log(f"   ✓ Tier: {resp.get('tier', 'N/A')}")
        
        # 4. Login with same credentials
        success, resp = self.test(
            "Login with credentials",
            "POST",
            "/auth/login",
            200,
            data={"email": test_email, "password": test_password}
        )
        
        # 5. Paths
        self.log("\n📋 SECTION 3: PATHS & CURRICULUM")
        success, resp = self.test("Get all paths", "GET", "/paths", 200)
        if success and 'paths' in resp:
            path_count = len(resp['paths'])
            self.log(f"   ✓ Found {path_count} paths (expected 10)")
            if path_count != 10:
                self.log(f"   ⚠️  WARNING: Expected 10 paths, got {path_count}")
        
        # 6. Get fundamentals path detail
        success, resp = self.test("Get fundamentals path detail", "GET", "/paths/fundamentals", 200)
        if success:
            self.log(f"   ✓ Path: {resp.get('title', 'N/A')}")
            self.log(f"   ✓ Modules: {len(resp.get('modules', []))}")
        
        # 7. Get first lesson (f1l1)
        self.log("\n📋 SECTION 4: LESSONS")
        success, resp = self.test("Get lesson f1l1 (free tier)", "GET", "/lessons/f1l1", 200)
        if success:
            self.log(f"   ✓ Lesson: {resp.get('title', 'N/A')}")
            self.log(f"   ✓ Cards: {len(resp.get('cards', []))}")
            self.log(f"   ✓ XP: {resp.get('xp', 0)}")
        
        # 8. Try to access sage tier lesson (should fail for free user)
        self.log("\n📋 SECTION 5: TIER ACCESS CONTROL")
        success, resp = self.test("Try sage lesson sp1l1 as free user (should 403)", "GET", "/lessons/sp1l1", 403)
        if success:
            self.log("   ✓ Tier access control working correctly")
        
        # 9. Models
        self.log("\n📋 SECTION 6: AI MODELS")
        success, resp = self.test("Get all AI models", "GET", "/models", 200)
        if success and 'models' in resp:
            model_count = len(resp['models'])
            self.log(f"   ✓ Found {model_count} models (expected 22)")
            if model_count != 22:
                self.log(f"   ⚠️  WARNING: Expected 22 models, got {model_count}")
        
        # 10. Progress
        self.log("\n📋 SECTION 7: PROGRESS & XP")
        success, resp = self.test("Get user progress", "GET", "/progress", 200)
        if success:
            self.log(f"   ✓ Total XP: {resp.get('total_xp', 0)}")
            self.log(f"   ✓ Level: {resp.get('level', 1)}")
            self.log(f"   ✓ Streak: {resp.get('streak_days', 0)} days")
        
        # 11. Complete a lesson
        success, resp = self.test(
            "Complete lesson f1l1",
            "POST",
            "/progress/complete",
            200,
            data={"lesson_id": "f1l1"}
        )
        if success:
            self.log(f"   ✓ Awarded XP: {resp.get('awarded_xp', 0)}")
            self.log(f"   ✓ New total XP: {resp.get('progress', {}).get('total_xp', 0)}")
            newly_completed = resp.get('newly_completed_paths', [])
            if newly_completed:
                self.log(f"   ✓ Completed paths: {newly_completed}")
            certs = resp.get('certificates_issued', [])
            if certs:
                self.log(f"   ✓ Certificates issued: {certs}")
        
        # 12. Quiz / Recommendation
        self.log("\n📋 SECTION 8: QUIZ & RECOMMENDATION")
        success, resp = self.test(
            "Save quiz answers",
            "PUT",
            "/auth/me/quiz",
            200,
            data={
                "goal": "career",
                "experience": "beginner",
                "time_per_day": "30min",
                "focus": "text"
            }
        )
        if success:
            self.log(f"   ✓ Recommended path: {resp.get('recommended_path_id', 'N/A')}")
        
        # 13. Certificates
        self.log("\n📋 SECTION 9: CERTIFICATES")
        success, resp = self.test("Get user certificates", "GET", "/certificates", 200)
        if success:
            cert_count = len(resp.get('certificates', []))
            self.log(f"   ✓ Certificates: {cert_count}")
        
        # 14. Pricing
        self.log("\n📋 SECTION 10: PRICING & BILLING")
        success, resp = self.test("Get pricing tiers", "GET", "/pricing", 200)
        if success and 'tiers' in resp:
            tier_count = len(resp['tiers'])
            self.log(f"   ✓ Tiers: {tier_count} (expected 3)")
            for tier in resp['tiers']:
                self.log(f"      - {tier.get('name')}: ${tier.get('price_monthly')}/mo")
        
        # 15. Stripe checkout
        success, resp = self.test(
            "Create Stripe checkout session",
            "POST",
            "/billing/checkout",
            200,
            data={
                "tier": "pathfinder",
                "interval": "monthly",
                "origin_url": "https://repo-to-site-2.preview.emergentagent.com"
            }
        )
        if success and 'url' in resp:
            checkout_url = resp['url']
            self.log(f"   ✓ Checkout URL: {checkout_url[:60]}...")
            if 'checkout.stripe.com' in checkout_url:
                self.log("   ✓ Valid Stripe checkout URL")
            else:
                self.log(f"   ⚠️  WARNING: URL doesn't contain 'checkout.stripe.com'")
        
        # 16. AI Tutor chat (Claude - may take 10-25 seconds)
        self.log("\n📋 SECTION 11: AI TUTOR (Claude Sonnet 4.5)")
        self.log("   ⏳ Sending message to AI Tutor (may take 10-25 seconds)...")
        success, resp = self.test(
            "AI Tutor chat",
            "POST",
            "/tutor/chat",
            200,
            data={"message": "What is prompt engineering in one sentence?"}
        )
        if success:
            reply = resp.get('reply', '')
            self.log(f"   ✓ Reply received ({len(reply)} chars)")
            self.log(f"   ✓ Session ID: {resp.get('session_id', 'N/A')[:20]}...")
            if len(reply) > 20:
                self.log(f"   ✓ Reply preview: {reply[:100]}...")
        
        # 17. Password change
        self.log("\n📋 SECTION 12: PASSWORD MANAGEMENT")
        success, resp = self.test(
            "Change password",
            "POST",
            "/auth/change-password",
            200,
            data={"current_password": test_password, "new_password": "newpass456"}
        )
        if success:
            self.log("   ✓ Password changed successfully")
        
        # 18. Forgot password (dev mode - returns token)
        success, resp = self.test(
            "Forgot password (dev mode)",
            "POST",
            "/auth/forgot-password",
            200,
            data={"email": test_email}
        )
        if success:
            if 'dev_reset_token' in resp:
                reset_token = resp['dev_reset_token']
                self.log(f"   ✓ Dev reset token: {reset_token[:20]}...")
                
                # 19. Reset password with token
                success2, resp2 = self.test(
                    "Reset password with token",
                    "POST",
                    "/auth/reset-password",
                    200,
                    data={"token": reset_token, "new_password": "resetpass789"}
                )
                if success2:
                    self.log("   ✓ Password reset successful")
        
        # 20. Admin endpoints - login as admin first
        self.log("\n📋 SECTION 13: ADMIN ENDPOINTS")
        self.log("   Logging in as admin (must change password on first login)...")
        
        # Try login as admin
        success, resp = self.test(
            "Admin login",
            "POST",
            "/auth/login",
            200,
            data={"email": "admin@ascendraacademy.com", "password": "AscendraAdmin2026!"}
        )
        if success and 'access_token' in resp:
            self.admin_token = resp['access_token']
            self.log(f"   ✓ Admin token obtained")
            
            # Check if must_change_password
            success2, resp2 = self.test("Admin /auth/me", "GET", "/auth/me", 200, token=self.admin_token)
            if success2:
                must_change = resp2.get('must_change_password', False)
                is_admin = resp2.get('is_admin', False)
                self.log(f"   ✓ Is admin: {is_admin}")
                self.log(f"   ✓ Must change password: {must_change}")
                
                if must_change:
                    # Change admin password
                    success3, resp3 = self.test(
                        "Admin change password (forced)",
                        "POST",
                        "/auth/change-password",
                        200,
                        data={"new_password": "NewAdminPw123"},
                        token=self.admin_token
                    )
                    if success3:
                        self.log("   ✓ Admin password changed")
            
            # Test admin endpoints
            self.test("Admin stats", "GET", "/admin/stats", 200, token=self.admin_token)
            self.test("Admin users", "GET", "/admin/users", 200, token=self.admin_token)
            self.test("Admin sales", "GET", "/admin/sales", 200, token=self.admin_token)
            self.test("Admin traffic", "GET", "/admin/traffic", 200, token=self.admin_token)
        
        # 21. Sage tier test - login as sage1
        self.log("\n📋 SECTION 14: SAGE TIER ACCESS")
        success, resp = self.test(
            "Sage user login",
            "POST",
            "/auth/login",
            200,
            data={"email": "sage1@ascendraacademy.com", "password": "test1"}
        )
        if success and 'access_token' in resp:
            self.sage_token = resp['access_token']
            self.log(f"   ✓ Sage token obtained")
            
            # Check if must_change_password
            success2, resp2 = self.test("Sage /auth/me", "GET", "/auth/me", 200, token=self.sage_token)
            if success2:
                must_change = resp2.get('must_change_password', False)
                tier = resp2.get('tier', 'N/A')
                self.log(f"   ✓ Tier: {tier}")
                self.log(f"   ✓ Must change password: {must_change}")
                
                if must_change:
                    # Change sage password
                    success3, resp3 = self.test(
                        "Sage change password (forced)",
                        "POST",
                        "/auth/change-password",
                        200,
                        data={"new_password": "newsagepass123"},
                        token=self.sage_token
                    )
                    if success3:
                        self.log("   ✓ Sage password changed")
            
            # Try to access sage tier lesson
            success3, resp3 = self.test(
                "Access sage lesson sp1l1 as sage user",
                "GET",
                "/lessons/sp1l1",
                200,
                token=self.sage_token
            )
            if success3:
                self.log("   ✓ Sage tier access working correctly")
        
        # Summary
        self.log("\n" + "=" * 60)
        self.log("TEST SUMMARY")
        self.log("=" * 60)
        self.log(f"Total tests: {self.tests_run}")
        self.log(f"✅ Passed: {self.tests_passed}")
        self.log(f"❌ Failed: {self.tests_failed}")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"Success rate: {success_rate:.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for i, test in enumerate(self.failed_tests, 1):
                self.log(f"  {i}. {test}")
        
        self.log("=" * 60)
        
        return self.tests_failed == 0

if __name__ == "__main__":
    tester = AscendraAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
