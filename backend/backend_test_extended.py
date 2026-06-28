"""
Extended Backend API Tests for Phase 15 & Phase 16
Additional edge cases and comprehensive testing
"""
import requests
import sys
import time
from datetime import datetime
from typing import Optional

BASE_URL = "https://repo-to-site-2.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@ascendraacademy.com"
ADMIN_PASSWORD = "AscendraAdmin2026!"
SAGE_USERS = [
    {"email": "sage1@ascendraacademy.com", "password": "test1"},
    {"email": "sage2@ascendraacademy.com", "password": "test2"},
]

class ExtendedTester:
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
        success, response = self.test(
            f"Login as {email}",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'access_token' in response:
            return response['access_token']
        return None
    
    def setup_auth(self):
        """Setup authentication"""
        self.log("=" * 60)
        self.log("AUTHENTICATION SETUP")
        self.log("=" * 60)
        
        self.admin_token = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not self.admin_token:
            self.log("❌ CRITICAL: Admin login failed", "ERROR")
            return False
        
        for user in SAGE_USERS:
            token = self.login(user["email"], user["password"])
            if token:
                self.user_tokens[user["email"]] = token
        
        return True
    
    def test_phase_15_extended(self):
        """Extended Phase 15 tests"""
        self.log("\n" + "=" * 60)
        self.log("PHASE 15 EXTENDED: DRAFT EDITING")
        self.log("=" * 60)
        
        # Get queue to find needs_review item with draft
        success, response = self.test(
            "GET /api/admin/auto/queue - Find needs_review items",
            "GET",
            "admin/auto/queue",
            200,
            token=self.admin_token
        )
        
        if success:
            items = response.get("items", [])
            needs_review_with_draft = None
            needs_review_no_draft = None
            
            for item in items:
                if item.get("status") == "needs_review":
                    if item.get("draft"):
                        needs_review_with_draft = item
                    else:
                        needs_review_no_draft = item
            
            # Test editing draft on needs_review WITH draft
            if needs_review_with_draft:
                self.log(f"\nTesting draft edit on item WITH draft: {needs_review_with_draft['id']}")
                
                success, response = self.test(
                    "PATCH /api/admin/auto/queue/{id}/draft - Edit title",
                    "PATCH",
                    f"admin/auto/queue/{needs_review_with_draft['id']}/draft",
                    200,
                    token=self.admin_token,
                    data={"title": "Updated Lesson Title via API Test"}
                )
                
                if success:
                    draft = response.get("draft", {})
                    if draft.get("title") == "Updated Lesson Title via API Test":
                        self.log("   ✅ Draft title updated successfully")
                    
                    # Verify edited_by_admin_at is set
                    if draft.get("edited_by_admin_at"):
                        self.log("   ✅ edited_by_admin_at timestamp set")
                
                # Test editing body_text (should replace cards)
                success, response = self.test(
                    "PATCH /api/admin/auto/queue/{id}/draft - Edit body_text",
                    "PATCH",
                    f"admin/auto/queue/{needs_review_with_draft['id']}/draft",
                    200,
                    token=self.admin_token,
                    data={"body_text": "This is the updated lesson body content."}
                )
                
                if success:
                    draft = response.get("draft", {})
                    cards = draft.get("cards", [])
                    if len(cards) == 1 and cards[0].get("kind") == "text":
                        self.log("   ✅ body_text correctly replaced cards with single text card")
            else:
                self.log("⚠️  No needs_review items with draft found")
            
            # Test editing draft on item WITHOUT draft (should fail)
            if needs_review_no_draft:
                self.test(
                    "PATCH /api/admin/auto/queue/{id}/draft - No draft returns 400",
                    "PATCH",
                    f"admin/auto/queue/{needs_review_no_draft['id']}/draft",
                    400,
                    token=self.admin_token,
                    data={"title": "Test"}
                )
            
            # Test editing draft on published item (should fail)
            published_item = next((item for item in items if item.get("status") == "published"), None)
            if published_item:
                self.test(
                    "PATCH /api/admin/auto/queue/{id}/draft - Published item returns 400",
                    "PATCH",
                    f"admin/auto/queue/{published_item['id']}/draft",
                    400,
                    token=self.admin_token,
                    data={"title": "Test"}
                )
    
    def test_phase_16_extended(self):
        """Extended Phase 16 tests"""
        self.log("\n" + "=" * 60)
        self.log("PHASE 16 EXTENDED: RATE LIMITING & PATH REJECTION")
        self.log("=" * 60)
        
        sage_email = SAGE_USERS[0]["email"]
        sage_token = self.user_tokens.get(sage_email)
        
        if not sage_token:
            self.log("❌ No sage user token available", "ERROR")
            return
        
        # Ensure user is sage tier
        success, user_info = self.test(
            "GET /api/auth/me - Check user tier",
            "GET",
            "auth/me",
            200,
            token=sage_token
        )
        
        if success:
            user_id = user_info.get("id")
            current_tier = user_info.get("tier")
            
            if current_tier != "sage":
                self.log(f"Upgrading user to sage tier...")
                self.test(
                    "PATCH /api/admin/users/{id} - Upgrade to sage",
                    "PATCH",
                    f"admin/users/{user_id}",
                    200,
                    token=self.admin_token,
                    data={"tier": "sage"}
                )
        
        # Test rate limiting - generate first path
        self.log("\n--- Testing Rate Limiting (5 min window) ---")
        success, response = self.test(
            "POST /api/paths/generate - First generation",
            "POST",
            "paths/generate",
            200,
            token=sage_token,
            data={
                "goal": "Learn to build AI-powered mobile applications",
                "fill_lessons": False
            }
        )
        
        first_path_id = None
        if success:
            first_path_id = response.get("path", {}).get("id")
            self.log(f"   First path generated: {first_path_id}")
        
        # Immediately try to generate another (should fail with 429)
        self.test(
            "POST /api/paths/generate - Immediate second generation returns 429",
            "POST",
            "paths/generate",
            429,
            token=sage_token,
            data={
                "goal": "Master AI video editing techniques",
                "fill_lessons": False
            }
        )
        
        # Test path rejection flow
        if first_path_id:
            self.log("\n--- Testing Path Rejection ---")
            
            # Reject the path
            success, response = self.test(
                "POST /api/admin/paths/{id}/reject - Reject path with notes",
                "POST",
                f"admin/paths/{first_path_id}/reject",
                200,
                token=self.admin_token,
                data={
                    "notes": "Content quality needs improvement. Please revise and resubmit."
                }
            )
            
            if success:
                path = response.get("path", {})
                if path.get("visibility") == "rejected" and path.get("admin_review_status") == "rejected":
                    self.log("   ✅ Path rejected successfully")
                
                # Verify creator can still see rejected path
                self.test(
                    "GET /api/paths/{id} - Creator can view rejected path",
                    "GET",
                    f"paths/{first_path_id}",
                    200,
                    token=sage_token
                )
                
                # Verify rejected path NOT in public list
                success, response = self.test(
                    "GET /api/paths - Rejected path not in public list",
                    "GET",
                    "paths",
                    200
                )
                
                if success:
                    paths = response.get("paths", [])
                    found = any(p.get("id") == first_path_id for p in paths)
                    if not found:
                        self.log("   ✅ Rejected path correctly excluded from public list")
                    else:
                        self.log("   ❌ Rejected path incorrectly appears in public list", "ERROR")
                
                # Verify rejected path appears in creator's /api/paths/mine
                success, response = self.test(
                    "GET /api/paths/mine - Rejected path in creator's list",
                    "GET",
                    "paths/mine",
                    200,
                    token=sage_token
                )
                
                if success:
                    my_paths = response.get("paths", [])
                    found = any(p.get("id") == first_path_id for p in my_paths)
                    if found:
                        self.log("   ✅ Rejected path appears in creator's paths list")
    
    def test_tier_gating(self):
        """Test tier-based access control"""
        self.log("\n" + "=" * 60)
        self.log("PHASE 16: TIER GATING")
        self.log("=" * 60)
        
        # Get all paths
        success, response = self.test(
            "GET /api/paths - Get all paths",
            "GET",
            "paths",
            200
        )
        
        if success:
            paths = response.get("paths", [])
            
            # Count by tier
            tier_counts = {}
            for path in paths:
                tier = path.get("tier", "free")
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
            
            self.log(f"\nPath distribution by tier:")
            for tier, count in sorted(tier_counts.items()):
                self.log(f"   {tier}: {count} paths")
            
            # Find a paid-tier path
            paid_path = next((p for p in paths if p.get("tier") in ("pathfinder", "sage")), None)
            
            if paid_path:
                self.log(f"\nTesting access to {paid_path['tier']} path: {paid_path['id']}")
                
                # Test anonymous user can see it in list but with tier info
                success, response = self.test(
                    "GET /api/paths - Anonymous sees paid path in list",
                    "GET",
                    "paths",
                    200
                )
                
                if success:
                    paths = response.get("paths", [])
                    found = next((p for p in paths if p.get("id") == paid_path["id"]), None)
                    if found and found.get("tier") == paid_path["tier"]:
                        self.log(f"   ✅ Paid path visible with tier={paid_path['tier']}")
    
    def test_regression_existing_paths(self):
        """Test that existing public paths still work"""
        self.log("\n" + "=" * 60)
        self.log("REGRESSION: EXISTING PUBLIC PATHS")
        self.log("=" * 60)
        
        # Get paths list
        success, response = self.test(
            "GET /api/paths - Get paths list",
            "GET",
            "paths",
            200
        )
        
        if success:
            paths = response.get("paths", [])
            
            # Find a curated (non-user-generated) path
            curated_path = next((p for p in paths if not p.get("is_user_generated")), None)
            
            if curated_path:
                path_id = curated_path["id"]
                self.log(f"\nTesting existing curated path: {path_id}")
                
                # Test GET /api/paths/{id} works
                success, response = self.test(
                    f"GET /api/paths/{path_id} - Existing path detail works",
                    "GET",
                    f"paths/{path_id}",
                    200
                )
                
                if success:
                    self.log("   ✅ Existing path detail endpoint works")
                    
                    # Verify it has modules and lessons
                    modules = response.get("modules", [])
                    if modules:
                        self.log(f"   ✅ Path has {len(modules)} modules")
                        
                        total_lessons = sum(len(m.get("lessons", [])) for m in modules)
                        self.log(f"   ✅ Path has {total_lessons} total lessons")
    
    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "=" * 60)
        self.log("EXTENDED TEST SUMMARY")
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
    tester = ExtendedTester()
    
    if not tester.setup_auth():
        return 1
    
    # Run extended tests
    tester.test_phase_15_extended()
    tester.test_phase_16_extended()
    tester.test_tier_gating()
    tester.test_regression_existing_paths()
    
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
