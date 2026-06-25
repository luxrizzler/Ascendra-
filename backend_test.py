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
    
    def test(self, name, method, endpoint, expected_status, data=None, headers=None, token=None, timeout=30):
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
                r = requests.get(url, headers=h, timeout=timeout)
            elif method == 'POST':
                r = requests.post(url, json=data, headers=h, timeout=timeout)
            elif method == 'PUT':
                r = requests.put(url, json=data, headers=h, timeout=timeout)
            elif method == 'PATCH':
                r = requests.patch(url, json=data, headers=h, timeout=timeout)
            elif method == 'DELETE':
                r = requests.delete(url, headers=h, timeout=timeout)
            
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
        self.log("   Logging in as admin (trying both passwords)...")
        
        # Try login as admin with NewAdmin789! first (changed in prior test)
        success, resp = self.test(
            "Admin login (NewAdmin789!)",
            "POST",
            "/auth/login",
            200,
            data={"email": "admin@ascendraacademy.com", "password": "NewAdmin789!"}
        )
        if not success:
            # Try original password
            success, resp = self.test(
                "Admin login (AscendraAdmin2026!)",
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
        
        # 22. PHASE 5: Google OAuth endpoint
        self.log("\n📋 SECTION 15: PHASE 5 - GOOGLE OAUTH")
        success, resp = self.test(
            "Google OAuth with fake token (should 401)",
            "POST",
            "/auth/google",
            401,
            data={"session_token": "fake-invalid-token-12345"}
        )
        if success:
            self.log("   ✓ Google OAuth endpoint exists and validates tokens")
        
        # 23. PHASE 5: Non-admin access control
        self.log("\n📋 SECTION 16: PHASE 5 - ADMIN ACCESS CONTROL")
        success, resp = self.test(
            "Non-admin accessing admin curriculum (should 403)",
            "GET",
            "/admin/curriculum/paths",
            403,
            token=self.token  # regular user token
        )
        if success:
            self.log("   ✓ Admin access control working correctly")
        
        # 24. PHASE 5: Admin Curriculum CRUD
        if self.admin_token:
            self.log("\n📋 SECTION 17: PHASE 5 - ADMIN CURRICULUM CRUD")
            
            # List all paths
            success, resp = self.test(
                "Admin list all paths",
                "GET",
                "/admin/curriculum/paths",
                200,
                token=self.admin_token
            )
            if success and 'paths' in resp:
                path_count = len(resp['paths'])
                self.log(f"   ✓ Found {path_count} paths")
            
            # Create a test path
            test_path_data = {
                "title": "Test Path E2E",
                "subtitle": "Test subtitle",
                "tagline": "Test tagline for automated testing",
                "tier": "free",
                "level": "Beginner",
                "color": "#FFB000"
            }
            success, resp = self.test(
                "Admin create test path",
                "POST",
                "/admin/curriculum/paths",
                200,
                data=test_path_data,
                token=self.admin_token
            )
            test_path_id = None
            if success and 'id' in resp:
                test_path_id = resp['id']
                self.log(f"   ✓ Created test path: {test_path_id}")
                
                # Update the path
                success2, resp2 = self.test(
                    "Admin update test path",
                    "PATCH",
                    f"/admin/curriculum/paths/{test_path_id}",
                    200,
                    data={"title": "Test Path E2E", "tagline": "Updated tagline for testing"},
                    token=self.admin_token
                )
                if success2:
                    self.log("   ✓ Path updated successfully")
                
                # Add a module
                module_data = {"title": "Test Module 1"}
                success3, resp3 = self.test(
                    "Admin add module to path",
                    "POST",
                    f"/admin/curriculum/paths/{test_path_id}/modules",
                    200,
                    data=module_data,
                    token=self.admin_token
                )
                module_id = None
                if success3 and 'id' in resp3:
                    module_id = resp3['id']
                    self.log(f"   ✓ Module added: {module_id}")
                    
                    # Add a lesson to the module
                    lesson_data = {
                        "title": "Test Lesson 1",
                        "duration_min": 5,
                        "xp": 50,
                        "cards": [
                            {"title": "Card 1", "body": "Test card body 1"},
                            {"title": "Card 2", "body": "Test card body 2"},
                            {"title": "Card 3", "body": "Test card body 3"},
                            {"title": "Card 4", "body": "Test card body 4"}
                        ],
                        "quiz": {
                            "question": "Test question?",
                            "options": ["A", "B", "C", "D"],
                            "answer_index": 0,
                            "explanation": "Test explanation"
                        }
                    }
                    success4, resp4 = self.test(
                        "Admin add lesson to module",
                        "POST",
                        f"/admin/curriculum/paths/{test_path_id}/modules/{module_id}/lessons",
                        200,
                        data=lesson_data,
                        token=self.admin_token
                    )
                    if success4:
                        self.log("   ✓ Lesson added successfully")
                
                # Delete the test path (cleanup)
                success5, resp5 = self.test(
                    "Admin delete test path",
                    "DELETE",
                    f"/admin/curriculum/paths/{test_path_id}",
                    200,
                    token=self.admin_token
                )
                if success5:
                    self.log("   ✓ Test path deleted (cleanup)")
        
        # 25. PHASE 5: AI Studio - Generate Lesson
        if self.admin_token:
            self.log("\n📋 SECTION 18: PHASE 5 - AI STUDIO LESSON GENERATION")
            self.log("   ⏳ Generating lesson with Claude (may take 15-30 seconds)...")
            
            lesson_gen_data = {
                "topic": "Prompt engineering for short-form video scripts",
                "level": "Beginner",
                "publish": False
            }
            success, resp = self.test(
                "AI Studio generate lesson",
                "POST",
                "/admin/ai/generate-lesson",
                200,
                data=lesson_gen_data,
                token=self.admin_token,
                timeout=60  # Claude takes 15-30 seconds
            )
            if success and 'draft' in resp:
                draft = resp['draft']
                self.log(f"   ✓ Lesson generated: {draft.get('title', 'N/A')}")
                cards = draft.get('cards', [])
                self.log(f"   ✓ Cards: {len(cards)} (expected 4)")
                if len(cards) != 4:
                    self.log(f"   ⚠️  WARNING: Expected 4 cards, got {len(cards)}")
                else:
                    # Check card body length
                    for i, card in enumerate(cards):
                        body_len = len(card.get('body', ''))
                        self.log(f"      Card {i+1}: {len(card.get('title', ''))} chars title, {body_len} chars body")
                        if body_len < 50:
                            self.log(f"      ⚠️  WARNING: Card {i+1} body too short ({body_len} < 50)")
                
                quiz = draft.get('quiz', {})
                options = quiz.get('options', [])
                self.log(f"   ✓ Quiz options: {len(options)} (expected 4)")
                if len(options) != 4:
                    self.log(f"   ⚠️  WARNING: Expected 4 quiz options, got {len(options)}")
                answer_idx = quiz.get('answer_index')
                if answer_idx is not None and 0 <= answer_idx < len(options):
                    self.log(f"   ✓ Valid answer_index: {answer_idx}")
                else:
                    self.log(f"   ⚠️  WARNING: Invalid answer_index: {answer_idx}")
        
        # 26. PHASE 5: AI Studio - Scan Outdated
        if self.admin_token:
            self.log("\n📋 SECTION 19: PHASE 5 - AI STUDIO SCAN OUTDATED")
            success, resp = self.test(
                "AI Studio scan outdated content",
                "GET",
                "/admin/ai/scan-outdated",
                200,
                token=self.admin_token
            )
            if success and 'findings' in resp:
                findings = resp['findings']
                self.log(f"   ✓ Findings: {len(findings)}")
                if len(findings) > 0:
                    self.log(f"   ✓ Found at least 1 outdated lesson (expected)")
                    first = findings[0]
                    self.log(f"      Path: {first.get('path_title', 'N/A')}")
                    self.log(f"      Lesson: {first.get('lesson_title', 'N/A')}")
                    self.log(f"      Outdated terms: {first.get('outdated_terms', [])}")
                else:
                    self.log("   ⚠️  WARNING: Expected at least 1 finding (f1l1 mentions GPT-4)")
        
        # 27. PHASE 5: AI Studio - Generate Cover
        if self.admin_token:
            self.log("\n📋 SECTION 20: PHASE 5 - AI STUDIO COVER GENERATION")
            self.log("   ⏳ Generating cover image with gpt-image-1 (may take 25-40 seconds)...")
            
            cover_gen_data = {
                "prompt": "Mastering AI Tutoring",
                "path_id": None
            }
            success, resp = self.test(
                "AI Studio generate cover",
                "POST",
                "/admin/ai/generate-cover",
                200,
                data=cover_gen_data,
                token=self.admin_token,
                timeout=60  # gpt-image-1 takes 25-40 seconds
            )
            if success and 'url' in resp:
                cover_url = resp['url']
                self.log(f"   ✓ Cover URL: {cover_url}")
                if '/api/static/covers/' in cover_url or cover_url.startswith('http'):
                    self.log("   ✓ Valid cover URL format")
                    
                    # Try to fetch the cover image
                    try:
                        if cover_url.startswith('/api/static/'):
                            full_url = f"{BASE_URL.replace('/api', '')}{cover_url}"
                        else:
                            full_url = cover_url
                        
                        self.log(f"   ⏳ Fetching cover image from: {full_url[:80]}...")
                        img_resp = requests.get(full_url, timeout=10)
                        if img_resp.status_code == 200:
                            self.log(f"   ✓ Cover image accessible (HTTP 200)")
                            content_type = img_resp.headers.get('content-type', '')
                            if 'image' in content_type:
                                self.log(f"   ✓ Valid image content-type: {content_type}")
                            else:
                                self.log(f"   ⚠️  WARNING: Unexpected content-type: {content_type}")
                        else:
                            self.log(f"   ⚠️  WARNING: Cover image not accessible (HTTP {img_resp.status_code})")
                    except Exception as e:
                        self.log(f"   ⚠️  WARNING: Failed to fetch cover: {str(e)[:100]}")
                else:
                    self.log(f"   ⚠️  WARNING: Unexpected URL format: {cover_url}")
        
        # 28. PHASE 5: Email Templates - Renewal Reminder
        if self.admin_token:
            self.log("\n📋 SECTION 21: PHASE 5 - RENEWAL REMINDER EMAIL")
            
            # Test preview endpoint (admin auth required)
            success, resp = self.test(
                "Admin email preview - renewal_reminder",
                "GET",
                "/admin/email/preview/renewal_reminder",
                200,
                token=self.admin_token
            )
            if success:
                if 'subject' in resp and 'html' in resp:
                    self.log(f"   ✓ Subject: {resp['subject'][:60]}...")
                    html_len = len(resp.get('html', ''))
                    self.log(f"   ✓ HTML body: {html_len} chars")
                    if html_len < 500:
                        self.log(f"   ⚠️  WARNING: HTML body too short ({html_len} < 500)")
                else:
                    self.log("   ⚠️  WARNING: Missing subject or html in response")
            
            # Test preview without admin auth (should 401)
            success, resp = self.test(
                "Email preview without admin auth (should 401)",
                "GET",
                "/admin/email/preview/renewal_reminder",
                401,
                token=self.token  # regular user token
            )
            if success:
                self.log("   ✓ Auth gating working correctly")
            
            # Test send test email
            success, resp = self.test(
                "Admin email test-send - renewal_reminder",
                "POST",
                "/admin/email/test-send",
                200,
                data={"template": "renewal_reminder", "to": "test@example.com"},
                token=self.admin_token
            )
            if success:
                if resp.get('ok'):
                    self.log(f"   ✓ Test email sent to: {resp.get('to', 'N/A')}")
                    if resp.get('dry_run'):
                        self.log("   ℹ️  Dry-run mode (no RESEND_API_KEY)")
                    else:
                        self.log(f"   ✓ Email ID: {resp.get('id', 'N/A')[:20]}...")
                else:
                    self.log("   ⚠️  WARNING: ok=false in response")
            
            # Test send without admin auth (should 401)
            success, resp = self.test(
                "Email test-send without admin auth (should 401)",
                "POST",
                "/admin/email/test-send",
                401,
                data={"template": "renewal_reminder"},
                token=self.token  # regular user token
            )
            if success:
                self.log("   ✓ Auth gating working correctly")
        
        # 29. PHASE 5: Renewal Reminders - Scan & Send
        if self.admin_token:
            self.log("\n📋 SECTION 22: PHASE 5 - RENEWAL REMINDER SCAN & SEND")
            
            # Test scan endpoint (admin auth required)
            success, resp = self.test(
                "Admin renewal-reminders/run",
                "POST",
                "/admin/billing/renewal-reminders/run",
                200,
                data={},
                token=self.admin_token
            )
            if success:
                scanned = resp.get('scanned', 0)
                sent = resp.get('sent', 0)
                skipped = resp.get('skipped', 0)
                failed = resp.get('failed', 0)
                self.log(f"   ✓ Scanned: {scanned}, Sent: {sent}, Skipped: {skipped}, Failed: {failed}")
                if 'window' in resp:
                    self.log(f"   ✓ Window: {resp['window']}")
                if 'details' in resp:
                    self.log("   ✓ Details field present")
                # Note: seeded users don't have active subscriptions, so scanned=0 is expected
                if scanned == 0:
                    self.log("   ℹ️  No candidates found (expected - seeded users don't have active subs)")
            
            # Test scan without admin auth (should 401)
            success, resp = self.test(
                "Renewal-reminders/run without admin auth (should 401)",
                "POST",
                "/admin/billing/renewal-reminders/run",
                401,
                data={},
                token=self.token  # regular user token
            )
            if success:
                self.log("   ✓ Auth gating working correctly")
            
            # Test idempotency - run scan again (should send 0 if there were candidates)
            success, resp = self.test(
                "Admin renewal-reminders/run (2nd time - idempotency)",
                "POST",
                "/admin/billing/renewal-reminders/run",
                200,
                data={},
                token=self.admin_token
            )
            if success:
                scanned2 = resp.get('scanned', 0)
                sent2 = resp.get('sent', 0)
                skipped2 = resp.get('skipped', 0)
                self.log(f"   ✓ 2nd run: Scanned: {scanned2}, Sent: {sent2}, Skipped: {skipped2}")
                if scanned2 == 0:
                    self.log("   ℹ️  Still no candidates (expected)")
                elif sent2 == 0 and skipped2 > 0:
                    self.log("   ✓ Idempotency working - skipped previously sent reminders")
            
            # Test manual send for specific user (should 404 for non-existent user)
            success, resp = self.test(
                "Admin renewal-reminders/send (non-existent user - should 404)",
                "POST",
                "/admin/billing/renewal-reminders/send",
                404,
                data={"user_id": "non-existent-user-id-12345"},
                token=self.admin_token
            )
            if success:
                self.log("   ✓ Returns 404 for non-existent user")
            
            # Test manual send without admin auth (should 401)
            success, resp = self.test(
                "Renewal-reminders/send without admin auth (should 401)",
                "POST",
                "/admin/billing/renewal-reminders/send",
                401,
                data={"user_id": "some-user-id"},
                token=self.token  # regular user token
            )
            if success:
                self.log("   ✓ Auth gating working correctly")
        
        # 30. PHASE 5: Stripe Webhook - invoice.upcoming
        self.log("\n📋 SECTION 23: PHASE 5 - STRIPE WEBHOOK (invoice.upcoming)")
        
        # Test webhook with invoice.upcoming event (no auth required for webhooks)
        webhook_payload = {
            "type": "invoice.upcoming",
            "data": {
                "object": {
                    "customer": "cus_test_non_existent_12345",
                    "subscription": "sub_test_12345",
                    "amount_due": 1999,
                    "period_end": int(time.time()) + (7 * 86400)  # 7 days from now
                }
            }
        }
        success, resp = self.test(
            "Stripe webhook - invoice.upcoming (non-existent customer)",
            "POST",
            "/billing/webhook",
            200,
            data=webhook_payload
        )
        if success:
            if resp.get('received'):
                self.log("   ✓ Webhook received without crash (graceful no-op for non-existent customer)")
            else:
                self.log("   ⚠️  WARNING: Expected {received: true} in response")
        
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
