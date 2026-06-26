"""
Phase 9+10+11 Backend API Testing
Tests lead capture, lifecycle emails, and social studio endpoints.
"""
import requests
import sys
from datetime import datetime

class Phase911Tester:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.lead_id = None
        self.social_post_id = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        h = headers or {}
        if self.token and "Authorization" not in h:
            h["Authorization"] = f"Bearer {self.token}"
        if data is not None and "Content-Type" not in h:
            h["Content-Type"] = "application/json"

        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == "GET":
                response = requests.get(url, headers=h, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, headers=h, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=h, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASS - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                self.log(f"❌ FAIL - Expected {expected_status}, got {response.status_code}")
                try:
                    self.log(f"   Response: {response.text[:200]}")
                except:
                    pass
                return False, {}

        except Exception as e:
            self.log(f"❌ FAIL - Error: {str(e)}")
            return False, {}

    def login_admin(self):
        """Login as admin to get token"""
        self.log("\n=== ADMIN LOGIN ===")
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@ascendraacademy.com", "password": "AscendraAdmin2026!"}
        )
        if success and "access_token" in response:
            self.token = response["access_token"]
            self.log(f"✅ Admin token acquired")
            return True
        self.log("❌ Admin login failed")
        return False

    def test_lead_capture(self):
        """Test Phase 9: Lead capture endpoint (PUBLIC)"""
        self.log("\n=== PHASE 9: LEAD CAPTURE ===")
        
        # Test 1: Capture a new lead (no auth required)
        test_email = f"phase11-test@example.com"
        success, response = self.run_test(
            "POST /api/leads (new lead)",
            "POST",
            "leads",
            200,
            data={"email": test_email, "name": "Phase Test"},
            headers={}  # No auth header
        )
        if success and response.get("ok") and response.get("lead_id"):
            self.lead_id = response["lead_id"]
            self.log(f"   Lead ID: {self.lead_id}")
        else:
            self.log("   ⚠️  Lead capture failed or missing lead_id")

        # Test 2: Idempotent - same email twice
        success2, response2 = self.run_test(
            "POST /api/leads (idempotent - same email)",
            "POST",
            "leads",
            200,
            data={"email": test_email, "name": "Phase Test"},
            headers={}
        )
        if success2 and response2.get("ok"):
            self.log("   ✅ Idempotent upsert working")

    def test_admin_leads(self):
        """Test admin leads list"""
        self.log("\n=== ADMIN: LIST LEADS ===")
        success, response = self.run_test(
            "GET /api/admin/leads",
            "GET",
            "admin/leads",
            200
        )
        if success:
            count = response.get("count", 0)
            leads = response.get("leads", [])
            self.log(f"   Found {count} leads")
            # Check if our test lead is in the list
            found = any(l.get("email") == "phase11-test@example.com" for l in leads)
            if found:
                self.log("   ✅ Test lead found in list")
            else:
                self.log("   ⚠️  Test lead not found in list")

    def test_lifecycle_endpoints(self):
        """Test Phase 10: Lifecycle email endpoints"""
        self.log("\n=== PHASE 10: LIFECYCLE EMAILS ===")
        
        # Test 1: Run all lifecycle scans
        success, response = self.run_test(
            "POST /api/admin/lifecycle/run {kind:'all'}",
            "POST",
            "admin/lifecycle/run",
            200,
            data={"kind": "all"}
        )
        if success:
            self.log(f"   Drip: scanned={response.get('drip', {}).get('scanned_leads', 0)}, sent={response.get('drip', {}).get('sent', {})}")
            self.log(f"   Trial ending: scanned={response.get('trial_ending', {}).get('scanned', 0)}, sent={response.get('trial_ending', {}).get('sent', 0)}")
            self.log(f"   Winback: scanned={response.get('winback', {}).get('scanned', 0)}, sent={response.get('winback', {}).get('sent', 0)}")
            self.log(f"   Streak saver: scanned={response.get('streak_saver', {}).get('scanned', 0)}, sent={response.get('streak_saver', {}).get('sent', 0)}")
            self.log(f"   Annual upsell: scanned={response.get('annual_upsell', {}).get('scanned', 0)}, sent={response.get('annual_upsell', {}).get('sent', 0)}")
            self.log("   ✅ All lifecycle scans completed (0 counts are valid if no users in window)")

        # Test 2: Run drip-only
        success2, response2 = self.run_test(
            "POST /api/admin/lifecycle/run {kind:'drip'}",
            "POST",
            "admin/lifecycle/run",
            200,
            data={"kind": "drip"}
        )
        if success2:
            self.log(f"   Drip-only: sent={response2.get('sent', {})}")

    def test_social_studio(self):
        """Test Phase 11: Social Studio endpoints"""
        self.log("\n=== PHASE 11: SOCIAL STUDIO ===")
        
        # Test 1: List social posts
        success, response = self.run_test(
            "GET /api/admin/social/posts",
            "GET",
            "admin/social/posts",
            200
        )
        if success:
            count = response.get("count", 0)
            posts = response.get("posts", [])
            self.log(f"   Found {count} social posts")
            if count > 0:
                self.social_post_id = posts[0].get("id")
                self.log(f"   Using post ID: {self.social_post_id}")
            else:
                self.log("   ⚠️  No social posts found (expected from prior test run)")
                return

        if not self.social_post_id:
            self.log("   ⚠️  Skipping post detail tests (no posts available)")
            return

        # Test 2: Get specific post
        success2, response2 = self.run_test(
            f"GET /api/admin/social/post/{self.social_post_id}",
            "GET",
            f"admin/social/post/{self.social_post_id}",
            200
        )
        if success2:
            tweets = response2.get("tweets", [])
            slides = response2.get("slides", [])
            has_video = response2.get("has_video", False)
            self.log(f"   Post has {len(tweets)} tweets, {len(slides)} slides, video={has_video}")

        # Test 3: Get slide image
        success3, _ = self.run_test(
            f"GET /api/admin/social/post/{self.social_post_id}/slide/0.png",
            "GET",
            f"admin/social/post/{self.social_post_id}/slide/0.png",
            200
        )
        if success3:
            self.log("   ✅ Slide 0 PNG retrieved successfully")

        # Test 4: Get video (if exists)
        if response2.get("has_video"):
            success4, _ = self.run_test(
                f"GET /api/admin/social/post/{self.social_post_id}/video.mp4",
                "GET",
                f"admin/social/post/{self.social_post_id}/video.mp4",
                200
            )
            if success4:
                self.log("   ✅ Video MP4 retrieved successfully")
        else:
            self.log("   ℹ️  No video for this post (skipping video test)")

    def run_all(self):
        """Run all tests"""
        self.log("=" * 60)
        self.log("PHASE 9+10+11 BACKEND API TESTS")
        self.log("=" * 60)
        
        # Login first
        if not self.login_admin():
            self.log("\n❌ Cannot proceed without admin access")
            return 1

        # Run all test suites
        self.test_lead_capture()
        self.test_admin_leads()
        self.test_lifecycle_endpoints()
        self.test_social_studio()

        # Summary
        self.log("\n" + "=" * 60)
        self.log(f"📊 RESULTS: {self.tests_passed}/{self.tests_run} tests passed")
        self.log("=" * 60)
        
        if self.tests_passed == self.tests_run:
            self.log("✅ ALL TESTS PASSED")
            return 0
        else:
            self.log(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return 1

def main():
    # Get backend URL from environment
    import os
    backend_url = os.environ.get("REACT_APP_BACKEND_URL", "https://repo-to-site-2.preview.emergentagent.com")
    
    tester = Phase911Tester(backend_url)
    return tester.run_all()

if __name__ == "__main__":
    sys.exit(main())
