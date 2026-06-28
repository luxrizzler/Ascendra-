"""
Backend API tests for admin tier-gate bypass fix (Phase 17).

Tests that admin users can access all lessons regardless of tier,
while maintaining tier restrictions for regular users.

BUG FIX: Admin users (with tier='free') were being blocked from accessing
paid-tier lessons. The fix adds `not user.get('is_admin') and` to the
tier-gate condition in GET /api/lessons/{lesson_id}.
"""
import requests
import sys
import uuid
from datetime import datetime

BASE_URL = "https://repo-to-site-2.preview.emergentagent.com/api"

class TierGateTests:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_token = None
        self.sage_token = None
        self.free_token = None
        
    def log(self, msg: str):
        """Print timestamped log message"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        
    def test(self, name: str, condition: bool, details: str = ""):
        """Record test result"""
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            self.log(f"✅ PASS: {name}")
            if details:
                self.log(f"   {details}")
        else:
            self.log(f"❌ FAIL: {name}")
            if details:
                self.log(f"   {details}")
        return condition
    
    def login(self, email: str, password: str) -> tuple[bool, str, dict]:
        """Login and return (success, token, user_data)"""
        try:
            r = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": email, "password": password},
                timeout=10
            )
            if r.status_code == 200:
                token = r.json().get("access_token")
                # Get user info
                me_r = requests.get(
                    f"{BASE_URL}/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                if me_r.status_code == 200:
                    return True, token, me_r.json()
                return True, token, {}
            self.log(f"Login failed for {email}: {r.status_code} - {r.text[:200]}")
            return False, "", {}
        except Exception as e:
            self.log(f"Login error for {email}: {e}")
            return False, "", {}
    
    def signup_free_user(self) -> tuple[bool, str, str]:
        """Create a new free-tier user, return (success, token, email)"""
        email = f"test_free_{uuid.uuid4().hex[:8]}@example.com"
        password = "TestPass123!"
        try:
            r = requests.post(
                f"{BASE_URL}/auth/signup",
                json={"email": email, "password": password, "name": "Test Free User"},
                timeout=10
            )
            if r.status_code == 200:
                token = r.json().get("access_token")
                return True, token, email
            self.log(f"Signup failed: {r.status_code} - {r.text[:200]}")
            return False, "", email
        except Exception as e:
            self.log(f"Signup error: {e}")
            return False, "", email
    
    def get_paths(self, token: str) -> list:
        """Get all paths for a user"""
        try:
            r = requests.get(
                f"{BASE_URL}/paths",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if r.status_code == 200:
                return r.json().get("paths", [])
            return []
        except Exception as e:
            self.log(f"Get paths error: {e}")
            return []
    
    def find_lesson_by_tier(self, paths: list, target_tier: str) -> tuple[str, str, str]:
        """Find a lesson from a path with the target tier. Returns (lesson_id, path_id, path_tier)"""
        for path in paths:
            if path.get("tier") == target_tier:
                path_id = path.get("id")
                # Get path detail to find a lesson
                try:
                    r = requests.get(
                        f"{BASE_URL}/paths/{path_id}",
                        timeout=10
                    )
                    if r.status_code == 200:
                        detail = r.json()
                        modules = detail.get("modules", [])
                        if modules and modules[0].get("lessons"):
                            lesson_id = modules[0]["lessons"][0]["id"]
                            return lesson_id, path_id, target_tier
                except Exception as e:
                    self.log(f"Error getting path detail for {path_id}: {e}")
        return "", "", ""
    
    def fetch_lesson(self, lesson_id: str, token: str) -> tuple[int, dict]:
        """Fetch a lesson, return (status_code, response_json)"""
        try:
            r = requests.get(
                f"{BASE_URL}/lessons/{lesson_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            return r.status_code, r.json() if r.status_code == 200 else {}
        except Exception as e:
            self.log(f"Fetch lesson error: {e}")
            return 500, {}
    
    def run_all_tests(self):
        """Run all test scenarios"""
        self.log("=" * 70)
        self.log("ADMIN TIER-GATE BYPASS TESTS (Phase 17)")
        self.log("=" * 70)
        
        # ===== SETUP: Login all users =====
        self.log("\n📋 SETUP: Logging in test users...")
        
        # Admin login
        success, self.admin_token, admin_user = self.login("admin@ascendraacademy.com", "AscendraAdmin2026!")
        if not self.test("Admin login", success, f"Admin tier: {admin_user.get('tier')}, is_admin: {admin_user.get('is_admin')}"):
            self.log("❌ CRITICAL: Cannot proceed without admin login")
            return False
        
        # Verify admin has tier='free' and is_admin=True
        admin_tier_is_free = admin_user.get("tier") == "free"
        admin_flag_is_true = admin_user.get("is_admin") == True
        
        if not self.test("Admin has tier='free'", admin_tier_is_free, f"Admin tier: {admin_user.get('tier')}"):
            self.log("⚠️  Warning: Admin tier is not 'free', test assumptions may be invalid")
        
        if not self.test("Admin has is_admin=True", admin_flag_is_true, f"is_admin: {admin_user.get('is_admin')}"):
            self.log("❌ CRITICAL: Admin flag is not set, cannot test admin bypass")
            return False
        
        # Sage user login
        success, self.sage_token, sage_user = self.login("sage1@ascendraacademy.com", "test1")
        if not self.test("Sage user login", success, f"Sage tier: {sage_user.get('tier')}"):
            self.log("⚠️  Warning: Sage user login failed, some tests will be skipped")
        
        # Create free user
        success, self.free_token, free_email = self.signup_free_user()
        if not self.test("Free user signup", success, f"Email: {free_email}"):
            self.log("⚠️  Warning: Free user creation failed, some tests will be skipped")
        
        # ===== Get paths as admin to find test lessons =====
        self.log("\n📋 SETUP: Finding test lessons...")
        admin_paths = self.get_paths(self.admin_token)
        self.test("Admin can fetch paths", len(admin_paths) > 0, f"Found {len(admin_paths)} paths")
        
        # Find lessons of different tiers
        free_lesson_id, free_path_id, _ = self.find_lesson_by_tier(admin_paths, "free")
        ascender_lesson_id, ascender_path_id, _ = self.find_lesson_by_tier(admin_paths, "ascender")
        pathfinder_lesson_id, pathfinder_path_id, _ = self.find_lesson_by_tier(admin_paths, "pathfinder")
        sage_lesson_id, sage_path_id, _ = self.find_lesson_by_tier(admin_paths, "sage")
        
        self.log(f"   Free lesson: {free_lesson_id} (path: {free_path_id})")
        self.log(f"   Ascender lesson: {ascender_lesson_id} (path: {ascender_path_id})")
        self.log(f"   Pathfinder lesson: {pathfinder_lesson_id} (path: {pathfinder_path_id})")
        self.log(f"   Sage lesson: {sage_lesson_id} (path: {sage_path_id})")
        
        # ===== PRIMARY TEST: Admin can access paid-tier lessons =====
        self.log("\n" + "=" * 70)
        self.log("🎯 PRIMARY BUG FIX TEST: Admin access to paid-tier lessons")
        self.log("=" * 70)
        
        if sage_lesson_id:
            status, lesson = self.fetch_lesson(sage_lesson_id, self.admin_token)
            self.test(
                "Admin (tier=free) can access SAGE lesson",
                status == 200,
                f"Status: {status}, Lesson: {lesson.get('title', 'N/A')}"
            )
        else:
            self.log("⚠️  SKIP: No sage lesson found")
        
        if pathfinder_lesson_id:
            status, lesson = self.fetch_lesson(pathfinder_lesson_id, self.admin_token)
            self.test(
                "Admin (tier=free) can access PATHFINDER lesson",
                status == 200,
                f"Status: {status}, Lesson: {lesson.get('title', 'N/A')}"
            )
        else:
            self.log("⚠️  SKIP: No pathfinder lesson found")
        
        if ascender_lesson_id:
            status, lesson = self.fetch_lesson(ascender_lesson_id, self.admin_token)
            self.test(
                "Admin (tier=free) can access ASCENDER lesson",
                status == 200,
                f"Status: {status}, Lesson: {lesson.get('title', 'N/A')}"
            )
        else:
            self.log("⚠️  SKIP: No ascender lesson found")
        
        # ===== NEGATIVE REGRESSION: Free user blocked from paid lessons =====
        self.log("\n" + "=" * 70)
        self.log("🔒 NEGATIVE REGRESSION: Free user tier restrictions")
        self.log("=" * 70)
        
        if self.free_token and sage_lesson_id:
            status, _ = self.fetch_lesson(sage_lesson_id, self.free_token)
            self.test(
                "Free user BLOCKED from SAGE lesson",
                status == 403,
                f"Status: {status} (expected 403)"
            )
        else:
            self.log("⚠️  SKIP: Free user or sage lesson not available")
        
        if self.free_token and pathfinder_lesson_id:
            status, _ = self.fetch_lesson(pathfinder_lesson_id, self.free_token)
            self.test(
                "Free user BLOCKED from PATHFINDER lesson",
                status == 403,
                f"Status: {status} (expected 403)"
            )
        else:
            self.log("⚠️  SKIP: Free user or pathfinder lesson not available")
        
        if self.free_token and ascender_lesson_id:
            status, _ = self.fetch_lesson(ascender_lesson_id, self.free_token)
            self.test(
                "Free user BLOCKED from ASCENDER lesson",
                status == 403,
                f"Status: {status} (expected 403)"
            )
        else:
            self.log("⚠️  SKIP: Free user or ascender lesson not available")
        
        # ===== POSITIVE REGRESSION: Sage user can access all tiers =====
        self.log("\n" + "=" * 70)
        self.log("✅ POSITIVE REGRESSION: Sage user can access all tiers")
        self.log("=" * 70)
        
        if self.sage_token and sage_lesson_id:
            status, lesson = self.fetch_lesson(sage_lesson_id, self.sage_token)
            self.test(
                "Sage user can access SAGE lesson",
                status == 200,
                f"Status: {status}, Lesson: {lesson.get('title', 'N/A')}"
            )
        else:
            self.log("⚠️  SKIP: Sage user or sage lesson not available")
        
        if self.sage_token and ascender_lesson_id:
            status, lesson = self.fetch_lesson(ascender_lesson_id, self.sage_token)
            self.test(
                "Sage user can access ASCENDER lesson",
                status == 200,
                f"Status: {status}, Lesson: {lesson.get('title', 'N/A')}"
            )
        else:
            self.log("⚠️  SKIP: Sage user or ascender lesson not available")
        
        if self.sage_token and free_lesson_id:
            status, lesson = self.fetch_lesson(free_lesson_id, self.sage_token)
            self.test(
                "Sage user can access FREE lesson",
                status == 200,
                f"Status: {status}, Lesson: {lesson.get('title', 'N/A')}"
            )
        else:
            self.log("⚠️  SKIP: Sage user or free lesson not available")
        
        # ===== POSITIVE REGRESSION: Admin can access free lessons =====
        self.log("\n" + "=" * 70)
        self.log("✅ POSITIVE REGRESSION: Admin can access free-tier lessons")
        self.log("=" * 70)
        
        if free_lesson_id:
            status, lesson = self.fetch_lesson(free_lesson_id, self.admin_token)
            self.test(
                "Admin can access FREE lesson",
                status == 200,
                f"Status: {status}, Lesson: {lesson.get('title', 'N/A')}"
            )
        else:
            self.log("⚠️  SKIP: No free lesson found")
        
        # ===== VERIFY: Admin sees all paths =====
        self.log("\n" + "=" * 70)
        self.log("📚 VERIFY: Admin can see all paths")
        self.log("=" * 70)
        
        tier_counts = {}
        for path in admin_paths:
            tier = path.get("tier", "free")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        self.log(f"   Admin sees {len(admin_paths)} total paths:")
        for tier, count in sorted(tier_counts.items()):
            self.log(f"   - {tier}: {count} paths")
        
        # Admin should see paths from multiple tiers (not necessarily all 4, as curriculum may not have all tiers)
        has_multiple_tiers = len(tier_counts) >= 2
        has_paid_tiers = any(tier in tier_counts for tier in ["ascender", "pathfinder", "sage"])
        self.test(
            "Admin sees paths from multiple tiers including paid tiers",
            has_multiple_tiers and has_paid_tiers,
            f"Tiers visible: {list(tier_counts.keys())}"
        )
        
        return True
    
    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "=" * 70)
        self.log("TEST SUMMARY")
        self.log("=" * 70)
        self.log(f"Tests run: {self.tests_run}")
        self.log(f"Tests passed: {self.tests_passed}")
        self.log(f"Tests failed: {self.tests_run - self.tests_passed}")
        
        if self.tests_passed == self.tests_run:
            self.log("✅ ALL TESTS PASSED")
            self.log("\nAdmin tier-gate bypass is working correctly:")
            self.log("  • Admin users can access all lessons regardless of tier")
            self.log("  • Free users are still blocked from paid-tier lessons")
            self.log("  • Paid users can access their tier and below")
            self.log("  • No regressions detected")
            return 0
        else:
            self.log(f"❌ {self.tests_run - self.tests_passed} TEST(S) FAILED")
            self.log("\nPlease review the failed tests above.")
            return 1

def main():
    tester = TierGateTests()
    try:
        tester.run_all_tests()
        return tester.print_summary()
    except Exception as e:
        tester.log(f"❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
