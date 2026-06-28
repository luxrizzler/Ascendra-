"""
Backend API Tests for Phase 15 & Phase 16
Tests admin auto-pilot queue management and user-generated learning paths
"""
import requests
import sys
import json
from datetime import datetime
from typing import Optional

BASE_URL = "https://repo-to-site-2.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@ascendraacademy.com"
ADMIN_PASSWORD = "AscendraAdmin2026!"
SAGE_TEST_USERS = [
    {"email": "sage1@ascendraacademy.com", "password": "test1"},
    {"email": "sage2@ascendraacademy.com", "password": "test2"},
    {"email": "sage3@ascendraacademy.com", "password": "test3"},
]

class APITester:
    def __init__(self):
        self.admin_token = None
        self.user_tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
    def log(self, msg: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {msg}")
    
    def test(self, name: str, method: str, endpoint: str, expected_status: int,
             token: Optional[str] = None, data: Optional[dict] = None,
             params: Optional[dict] = None) -> tuple[bool, dict]:
        """Run a single API test"""
        url = f"{BASE_URL}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        self.tests_run += 1
        self.log(f"Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASS - Status: {response.status_code}", "PASS")
            else:
                self.tests_failed += 1
                self.failed_tests.append({
                    "name": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200]
                })
                self.log(f"❌ FAIL - Expected {expected_status}, got {response.status_code}", "FAIL")
                self.log(f"   Response: {response.text[:200]}", "FAIL")
            
            try:
                return success, response.json()
            except:
                return success, {"raw": response.text}
        
        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append({
                "name": name,
                "expected": expected_status,
                "error": str(e)
            })
            self.log(f"❌ FAIL - Error: {str(e)}", "FAIL")
            return False, {"error": str(e)}
    
    def login(self, email: str, password: str) -> Optional[str]:
        """Login and return token"""
        self.log(f"Logging in as {email}")
        success, response = self.test(
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
        """Setup authentication for admin and test users"""
        self.log("=" * 60)
        self.log("AUTHENTICATION SETUP")
        self.log("=" * 60)
        
        # Admin login
        self.admin_token = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not self.admin_token:
            self.log("❌ CRITICAL: Admin login failed. Cannot proceed.", "ERROR")
            return False
        
        # Test user logins
        for user in SAGE_TEST_USERS[:2]:  # Login first 2 sage users
            token = self.login(user["email"], user["password"])
            if token:
                self.user_tokens[user["email"]] = token
        
        return True
    
    def test_phase_15_admin_queue(self):
        """Test Phase 15: Admin Auto-Pilot Queue Management"""
        self.log("\n" + "=" * 60)
        self.log("PHASE 15: ADMIN AUTO-PILOT QUEUE MANAGEMENT")
        self.log("=" * 60)
        
        # Get queue list first to find items
        success, response = self.test(
            "GET /api/admin/auto/queue - List queue items",
            "GET",
            "admin/auto/queue",
            200,
            token=self.admin_token
        )
        
        queue_items = response.get("items", []) if success else []
        failed_item = None
        needs_review_item = None
        
        for item in queue_items:
            if item.get("status") == "failed" and not failed_item:
                failed_item = item
            elif item.get("status") == "needs_review" and not needs_review_item:
                needs_review_item = item
        
        # Test regenerate on FAILED item
        if failed_item:
            self.log(f"\nTesting regenerate on FAILED item: {failed_item['id']}")
            self.test(
                "POST /api/admin/auto/queue/{id}/regenerate - Regenerate FAILED item",
                "POST",
                f"admin/auto/queue/{failed_item['id']}/regenerate",
                200,
                token=self.admin_token
            )
        else:
            self.log("⚠️  No FAILED items in queue to test regenerate")
        
        # Test regenerate on non-existent item (should 404)
        self.test(
            "POST /api/admin/auto/queue/{id}/regenerate - Non-existent item returns 404",
            "POST",
            "admin/auto/queue/nonexistent-id-12345/regenerate",
            404,
            token=self.admin_token
        )
        
        # Test regenerate from invalid status (should 400)
        published_item = next((item for item in queue_items if item.get("status") == "published"), None)
        if published_item:
            self.test(
                "POST /api/admin/auto/queue/{id}/regenerate - Published item returns 400",
                "POST",
                f"admin/auto/queue/{published_item['id']}/regenerate",
                400,
                token=self.admin_token
            )
        
        # Test reject endpoint
        if needs_review_item:
            self.log(f"\nTesting reject on NEEDS_REVIEW item: {needs_review_item['id']}")
            self.test(
                "POST /api/admin/auto/queue/{id}/reject - Reject with reason",
                "POST",
                f"admin/auto/queue/{needs_review_item['id']}/reject",
                200,
                token=self.admin_token,
                data={"reason": "Test rejection - quality not meeting standards"}
            )
        else:
            self.log("⚠️  No NEEDS_REVIEW items in queue to test reject")
        
        # Test draft edit endpoint
        if needs_review_item and needs_review_item.get("draft"):
            self.log(f"\nTesting draft edit on NEEDS_REVIEW item: {needs_review_item['id']}")
            self.test(
                "PATCH /api/admin/auto/queue/{id}/draft - Edit draft title and body",
                "PATCH",
                f"admin/auto/queue/{needs_review_item['id']}/draft",
                200,
                token=self.admin_token,
                data={
                    "title": "Updated Test Title",
                    "body_text": "This is updated test content for the lesson."
                }
            )
        
        # Test admin auth requirement (403 for non-admin)
        user_token = list(self.user_tokens.values())[0] if self.user_tokens else None
        if user_token:
            self.test(
                "POST /api/admin/auto/queue/{id}/regenerate - Non-admin returns 403",
                "POST",
                "admin/auto/queue/any-id/regenerate",
                403,
                token=user_token
            )
            
            self.test(
                "POST /api/admin/auto/queue/{id}/reject - Non-admin returns 403",
                "POST",
                "admin/auto/queue/any-id/reject",
                403,
                token=user_token,
                data={"reason": "test"}
            )
            
            self.test(
                "PATCH /api/admin/auto/queue/{id}/draft - Non-admin returns 403",
                "PATCH",
                "admin/auto/queue/any-id/draft",
                403,
                token=user_token,
                data={"title": "test"}
            )
    
    def test_phase_16_user_paths(self):
        """Test Phase 16: User-Generated Learning Paths"""
        self.log("\n" + "=" * 60)
        self.log("PHASE 16: USER-GENERATED LEARNING PATHS")
        self.log("=" * 60)
        
        # Test 1: Anonymous user - only public/approved paths
        self.log("\n--- Testing Anonymous Access ---")
        success, response = self.test(
            "GET /api/paths - Anonymous user sees only public/approved paths",
            "GET",
            "paths",
            200
        )
        
        if success:
            paths = response.get("paths", [])
            self.log(f"   Anonymous user sees {len(paths)} paths")
            # Check no pending/rejected paths leaked
            leaked = [p for p in paths if p.get("visibility") in ("pending_review", "rejected", "private")]
            if leaked:
                self.log(f"❌ SECURITY ISSUE: {len(leaked)} non-public paths leaked to anonymous user!", "ERROR")
            else:
                self.log("✅ No non-public paths leaked to anonymous user")
        
        # Test 2: Authenticated user sees their own paths
        user_email = list(self.user_tokens.keys())[0] if self.user_tokens else None
        user_token = self.user_tokens.get(user_email) if user_email else None
        
        if user_token:
            self.log(f"\n--- Testing Authenticated User Access ({user_email}) ---")
            success, response = self.test(
                "GET /api/paths - Authenticated user sees public + own paths",
                "GET",
                "paths",
                200,
                token=user_token
            )
            
            if success:
                paths = response.get("paths", [])
                self.log(f"   Authenticated user sees {len(paths)} paths")
        
        # Test 3: Free user tries to generate path (should 402)
        # First, ensure we have a free-tier user
        free_user_token = None
        for email, token in self.user_tokens.items():
            # Get user info
            success, user_info = self.test(
                f"GET /api/auth/me - Check tier for {email}",
                "GET",
                "auth/me",
                200,
                token=token
            )
            if success and user_info.get("tier") == "free":
                free_user_token = token
                self.log(f"   Found free-tier user: {email}")
                break
        
        if free_user_token:
            self.log("\n--- Testing Free User Path Generation (should fail) ---")
            self.test(
                "POST /api/paths/generate - Free user returns 402",
                "POST",
                "paths/generate",
                402,
                token=free_user_token,
                data={
                    "goal": "Learn advanced AI automation techniques",
                    "fill_lessons": False
                }
            )
        
        # Test 4: Goal validation
        if user_token:
            self.log("\n--- Testing Path Generation Validation ---")
            
            # Goal too short (< 8 chars)
            self.test(
                "POST /api/paths/generate - Goal too short returns 400",
                "POST",
                "paths/generate",
                400,
                token=user_token,
                data={"goal": "AI", "fill_lessons": False}
            )
            
            # Goal too long (> 2000 chars)
            long_goal = "A" * 2001
            self.test(
                "POST /api/paths/generate - Goal too long returns 400",
                "POST",
                "paths/generate",
                400,
                token=user_token,
                data={"goal": long_goal, "fill_lessons": False}
            )
        
        # Test 5: Upgrade a sage user to paid tier and test generation
        sage_user_email = SAGE_TEST_USERS[0]["email"]
        sage_token = self.user_tokens.get(sage_user_email)
        
        if sage_token and self.admin_token:
            self.log(f"\n--- Upgrading {sage_user_email} to sage tier ---")
            
            # Get user ID first
            success, user_info = self.test(
                f"GET /api/auth/me - Get user ID for {sage_user_email}",
                "GET",
                "auth/me",
                200,
                token=sage_token
            )
            
            if success:
                user_id = user_info.get("id")
                current_tier = user_info.get("tier")
                self.log(f"   User ID: {user_id}, Current tier: {current_tier}")
                
                # Upgrade to sage tier if not already
                if current_tier != "sage":
                    self.log(f"   Upgrading user to sage tier...")
                    success, _ = self.test(
                        f"PATCH /api/admin/users/{user_id} - Upgrade to sage tier",
                        "PATCH",
                        f"admin/users/{user_id}",
                        200,
                        token=self.admin_token,
                        data={"tier": "sage"}
                    )
                    
                    if success:
                        self.log("   ✅ User upgraded to sage tier")
                        
                        # Verify upgrade
                        success, user_info = self.test(
                            "GET /api/auth/me - Verify tier upgrade",
                            "GET",
                            "auth/me",
                            200,
                            token=sage_token
                        )
                        
                        if success:
                            new_tier = user_info.get("tier")
                            self.log(f"   Verified new tier: {new_tier}")
                
                # Now test path generation as paid user
                self.log("\n--- Testing Paid User Path Generation ---")
                success, response = self.test(
                    "POST /api/paths/generate - Paid user generates path",
                    "POST",
                    "paths/generate",
                    200,
                    token=sage_token,
                    data={
                        "goal": "Master AI-powered content creation for social media marketing",
                        "fill_lessons": True
                    }
                )
                
                generated_path_id = None
                if success:
                    generated_path_id = response.get("path", {}).get("id")
                    self.log(f"   ✅ Path generated with ID: {generated_path_id}")
                    self.log(f"   Fill status: {response.get('fill_status')}")
                    
                    # Test GET /api/paths/mine
                    self.log("\n--- Testing GET /api/paths/mine ---")
                    success, response = self.test(
                        "GET /api/paths/mine - List user's created paths",
                        "GET",
                        "paths/mine",
                        200,
                        token=sage_token
                    )
                    
                    if success:
                        my_paths = response.get("paths", [])
                        self.log(f"   User has created {len(my_paths)} paths")
                        found = any(p.get("id") == generated_path_id for p in my_paths)
                        if found:
                            self.log(f"   ✅ Generated path found in user's paths")
                        else:
                            self.log(f"   ❌ Generated path NOT found in user's paths", "ERROR")
                    
                    # Test path visibility - creator can view
                    if generated_path_id:
                        self.log("\n--- Testing Path Visibility ---")
                        success, response = self.test(
                            "GET /api/paths/{id} - Creator can view pending path",
                            "GET",
                            f"paths/{generated_path_id}",
                            200,
                            token=sage_token
                        )
                        
                        if success:
                            visibility = response.get("visibility")
                            status = response.get("admin_review_status")
                            self.log(f"   Path visibility: {visibility}, status: {status}")
                        
                        # Test another user cannot view
                        other_user_token = None
                        for email, token in self.user_tokens.items():
                            if email != sage_user_email:
                                other_user_token = token
                                break
                        
                        if other_user_token:
                            self.test(
                                "GET /api/paths/{id} - Other user cannot view pending path (404)",
                                "GET",
                                f"paths/{generated_path_id}",
                                404,
                                token=other_user_token
                            )
                        
                        # Test admin can view
                        self.test(
                            "GET /api/paths/{id} - Admin can view pending path",
                            "GET",
                            f"paths/{generated_path_id}",
                            200,
                            token=self.admin_token
                        )
                        
                        # Test admin endpoints
                        self.log("\n--- Testing Admin Review Endpoints ---")
                        
                        # GET /api/admin/paths/pending-review
                        success, response = self.test(
                            "GET /api/admin/paths/pending-review - List pending paths",
                            "GET",
                            "admin/paths/pending-review",
                            200,
                            token=self.admin_token
                        )
                        
                        if success:
                            pending_paths = response.get("paths", [])
                            self.log(f"   Found {len(pending_paths)} pending paths")
                            found = any(p.get("id") == generated_path_id for p in pending_paths)
                            if found:
                                self.log(f"   ✅ Generated path found in pending review list")
                        
                        # GET /api/admin/notifications
                        success, response = self.test(
                            "GET /api/admin/notifications - Check for path submission notification",
                            "GET",
                            "admin/notifications",
                            200,
                            token=self.admin_token
                        )
                        
                        if success:
                            notifs = response.get("notifications", [])
                            unread = response.get("unread_count", 0)
                            self.log(f"   Total notifications: {len(notifs)}, Unread: {unread}")
                            
                            path_notif = next((n for n in notifs if n.get("path_id") == generated_path_id), None)
                            if path_notif:
                                self.log(f"   ✅ Found notification for generated path")
                                notif_id = path_notif.get("id")
                                
                                # Mark notification as read
                                self.test(
                                    "POST /api/admin/notifications/{id}/mark-read",
                                    "POST",
                                    f"admin/notifications/{notif_id}/mark-read",
                                    200,
                                    token=self.admin_token
                                )
                        
                        # Test approve path
                        self.log("\n--- Testing Path Approval ---")
                        success, response = self.test(
                            "POST /api/admin/paths/{id}/approve - Approve path",
                            "POST",
                            f"admin/paths/{generated_path_id}/approve",
                            200,
                            token=self.admin_token,
                            data={
                                "notes": "Great content! Approved for public access.",
                                "new_tier": "pathfinder"
                            }
                        )
                        
                        if success:
                            self.log("   ✅ Path approved successfully")
                            
                            # Verify path is now public
                            success, response = self.test(
                                "GET /api/paths - Verify approved path appears in public list",
                                "GET",
                                "paths",
                                200
                            )
                            
                            if success:
                                paths = response.get("paths", [])
                                found = any(p.get("id") == generated_path_id for p in paths)
                                if found:
                                    self.log(f"   ✅ Approved path now appears in public paths list")
                                else:
                                    self.log(f"   ❌ Approved path NOT in public list", "ERROR")
        
        # Test regression: existing curated paths still work
        self.log("\n--- Testing Regression: Existing Paths ---")
        success, response = self.test(
            "GET /api/paths - Verify existing curated paths still returned",
            "GET",
            "paths",
            200
        )
        
        if success:
            paths = response.get("paths", [])
            curated_paths = [p for p in paths if not p.get("is_user_generated")]
            self.log(f"   Found {len(curated_paths)} curated paths")
            if len(curated_paths) >= 10:
                self.log(f"   ✅ Existing curated paths still available")
            else:
                self.log(f"   ⚠️  Expected at least 10 curated paths, found {len(curated_paths)}")
    
    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "=" * 60)
        self.log("TEST SUMMARY")
        self.log("=" * 60)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"Passed: {self.tests_passed} ✅")
        self.log(f"Failed: {self.tests_failed} ❌")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            self.log("\n" + "=" * 60)
            self.log("FAILED TESTS DETAILS")
            self.log("=" * 60)
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
        
        return 0 if self.tests_failed == 0 else 1

def main():
    tester = APITester()
    
    # Setup authentication
    if not tester.setup_auth():
        return 1
    
    # Run Phase 15 tests
    tester.test_phase_15_admin_queue()
    
    # Run Phase 16 tests
    tester.test_phase_16_user_paths()
    
    # Print summary
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
