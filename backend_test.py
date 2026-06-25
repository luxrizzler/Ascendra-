"""
Backend API tests for Phase 7: Programmatic SEO Studio
Tests all public and admin SEO endpoints.
"""
import requests
import sys
import time
from datetime import datetime

# Get backend URL from frontend .env
BACKEND_URL = "https://repo-to-site-2.preview.emergentagent.com"

class SeoStudioTester:
    def __init__(self, base_url=BACKEND_URL):
        self.base_url = base_url.rstrip("/")
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, check_content_type=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        req_headers = headers or {}
        
        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        print(f"   {method} {endpoint}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=req_headers, timeout=30)
            elif method == 'POST':
                req_headers['Content-Type'] = 'application/json'
                response = requests.post(url, json=data, headers=req_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=req_headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            
            # Check content type if specified
            if success and check_content_type:
                actual_ct = response.headers.get('content-type', '').lower()
                if check_content_type.lower() not in actual_ct:
                    print(f"❌ FAILED - Expected content-type {check_content_type}, got {actual_ct}")
                    self.failed_tests.append({"test": name, "reason": f"Wrong content-type: {actual_ct}"})
                    return False, None
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                return True, response
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                self.failed_tests.append({"test": name, "reason": f"Status {response.status_code} != {expected_status}"})
                return False, response

        except Exception as e:
            print(f"❌ FAILED - Error: {str(e)}")
            self.failed_tests.append({"test": name, "reason": str(e)})
            return False, None

    def login_admin(self):
        """Login as admin and get token"""
        print("\n🔐 Logging in as admin...")
        success, response = self.run_test(
            "Admin login",
            "POST",
            "/api/auth/login",
            200,
            data={"email": "admin@ascendraacademy.com", "password": "AscendraAdmin2026!"}
        )
        if success and response:
            data = response.json()
            self.admin_token = data.get('access_token')
            print(f"✅ Admin token obtained: {self.admin_token[:20]}...")
            return True
        return False

    def test_public_endpoints(self):
        """Test all public SEO endpoints (no auth required)"""
        print("\n" + "="*60)
        print("TESTING PUBLIC SEO ENDPOINTS (No Auth)")
        print("="*60)

        # Test 1: GET /api/seo/sitemap.xml
        success, response = self.run_test(
            "GET /api/seo/sitemap.xml",
            "GET",
            "/api/seo/sitemap.xml",
            200,
            check_content_type="application/xml"
        )
        if success and response:
            xml_content = response.text
            # Check for expected hub URLs
            expected_hubs = [
                "/learn/claude-sonnet-45",
                "/learn/gpt-52",
                "/learn/gemini-3",
                "/learn/sora-2",
                "/learn/nano-banana",
                "/learn/elevenlabs"
            ]
            missing = []
            for hub in expected_hubs:
                if hub not in xml_content:
                    missing.append(hub)
            if missing:
                print(f"⚠️  WARNING: Missing hub URLs in sitemap: {missing}")
            else:
                print(f"✅ All 6 expected hub URLs found in sitemap")
            
            # Check for use-case URLs
            if "/learn/claude-sonnet-45/for-marketing" in xml_content or "/learn/gpt-52/for-founders" in xml_content:
                print(f"✅ Use-case URLs found in sitemap")

        # Test 2: GET /api/seo/robots.txt
        success, response = self.run_test(
            "GET /api/seo/robots.txt",
            "GET",
            "/api/seo/robots.txt",
            200,
            check_content_type="text/plain"
        )
        if success and response:
            robots_content = response.text
            required_rules = ["Disallow: /admin", "Disallow: /api/", "Sitemap:"]
            missing_rules = [r for r in required_rules if r not in robots_content]
            if missing_rules:
                print(f"⚠️  WARNING: Missing rules in robots.txt: {missing_rules}")
            else:
                print(f"✅ All required rules found in robots.txt")

        # Test 3: GET /api/seo/published
        success, response = self.run_test(
            "GET /api/seo/published",
            "GET",
            "/api/seo/published",
            200
        )
        if success and response:
            data = response.json()
            count = data.get('count', 0)
            pages = data.get('pages', [])
            print(f"   Found {count} published pages")
            if count >= 8:
                print(f"✅ Expected 8+ pages, got {count}")
            else:
                print(f"⚠️  WARNING: Expected 8+ pages, got {count}")

        # Test 4: GET /api/seo/page/claude-sonnet-45 (hub page)
        success, response = self.run_test(
            "GET /api/seo/page/claude-sonnet-45",
            "GET",
            "/api/seo/page/claude-sonnet-45",
            200
        )
        if success and response:
            page = response.json()
            required_fields = ["model_name", "model_slug", "title", "meta_title", "meta_description", 
                             "hero_eyebrow", "intro_md", "tldr", "what_it_is", "faqs", "cta_headline"]
            missing_fields = [f for f in required_fields if f not in page]
            if missing_fields:
                print(f"⚠️  WARNING: Missing fields in hub page: {missing_fields}")
            else:
                print(f"✅ All required hub page fields present")

        # Test 5: GET /api/seo/page/gpt-52/for-founders (use-case page)
        success, response = self.run_test(
            "GET /api/seo/page/gpt-52/for-founders",
            "GET",
            "/api/seo/page/gpt-52/for-founders",
            200
        )
        if success and response:
            page = response.json()
            required_fields = ["model_name", "use_case_name", "step_by_step", "prompts", 
                             "pro_tips", "common_mistakes", "tools_to_combine", "faqs"]
            missing_fields = [f for f in required_fields if f not in page]
            if missing_fields:
                print(f"⚠️  WARNING: Missing fields in use-case page: {missing_fields}")
            else:
                print(f"✅ All required use-case page fields present")

        # Test 6: GET /api/seo/page/nonexistent-slug (should 404)
        self.run_test(
            "GET /api/seo/page/nonexistent-slug (should 404)",
            "GET",
            "/api/seo/page/nonexistent-slug",
            404
        )

    def test_admin_endpoints(self):
        """Test admin SEO endpoints (auth required)"""
        print("\n" + "="*60)
        print("TESTING ADMIN SEO ENDPOINTS (Auth Required)")
        print("="*60)

        # Test 7: GET /api/admin/seo/pages without auth (should 401 or 403)
        success, response = self.run_test(
            "GET /api/admin/seo/pages (no auth - should fail)",
            "GET",
            "/api/admin/seo/pages",
            401  # Could also be 403
        )
        # If 403 instead of 401, that's also acceptable
        if not success and response and response.status_code == 403:
            print(f"   Note: Got 403 instead of 401 (both acceptable)")
            self.tests_passed += 1
            self.tests_run -= 1  # Don't double count

        # Login as admin
        if not self.login_admin():
            print("❌ CRITICAL: Admin login failed, skipping admin tests")
            return

        auth_headers = {"Authorization": f"Bearer {self.admin_token}"}

        # Test 8: GET /api/admin/seo/pages with auth
        success, response = self.run_test(
            "GET /api/admin/seo/pages (with admin auth)",
            "GET",
            "/api/admin/seo/pages",
            200,
            headers=auth_headers
        )
        if success and response:
            data = response.json()
            pages = data.get('pages', [])
            print(f"   Found {len(pages)} total pages (including drafts/archived)")

        # Test 9: POST /api/admin/seo/page/claude-sonnet-45/status (archive then restore)
        print("\n📝 Testing status change (archive then restore)...")
        
        # Archive the page
        success, response = self.run_test(
            "POST /api/admin/seo/page/claude-sonnet-45/status (archive)",
            "POST",
            "/api/admin/seo/page/claude-sonnet-45/status",
            200,
            data={"status": "archived"},
            headers=auth_headers
        )
        
        if success:
            # Verify it's now 404 on public endpoint
            time.sleep(0.5)  # Brief pause
            success2, response2 = self.run_test(
                "GET /api/seo/page/claude-sonnet-45 (should 404 after archive)",
                "GET",
                "/api/seo/page/claude-sonnet-45",
                404
            )
            
            # Restore to published
            time.sleep(0.5)
            success3, response3 = self.run_test(
                "POST /api/admin/seo/page/claude-sonnet-45/status (restore to published)",
                "POST",
                "/api/admin/seo/page/claude-sonnet-45/status",
                200,
                data={"status": "published"},
                headers=auth_headers
            )
            
            # Verify it's back
            if success3:
                time.sleep(0.5)
                self.run_test(
                    "GET /api/seo/page/claude-sonnet-45 (should 200 after restore)",
                    "GET",
                    "/api/seo/page/claude-sonnet-45",
                    200
                )

        # Test 10: POST /api/admin/seo/generate-hub (create test page, then delete)
        print("\n🤖 Testing hub generation (this may take 10-20 seconds)...")
        print("   NOTE: This calls Claude 4.5 API, so it's slow...")
        
        success, response = self.run_test(
            "POST /api/admin/seo/generate-hub (Test Model XYZ)",
            "POST",
            "/api/admin/seo/generate-hub",
            200,
            data={"model_name": "Test Model XYZ", "publish": False},
            headers=auth_headers
        )
        
        if success and response:
            data = response.json()
            if data.get('generated') and data.get('page'):
                print(f"✅ Generated page: {data['page'].get('title', 'N/A')}")
                print(f"   Published: {data.get('published', False)}")
                
                # Clean up: delete the test page
                time.sleep(0.5)
                self.run_test(
                    "DELETE /api/admin/seo/page/test-model-xyz (cleanup)",
                    "DELETE",
                    "/api/admin/seo/page/test-model-xyz",
                    200,
                    headers=auth_headers
                )

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {len(self.failed_tests)}")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for i, fail in enumerate(self.failed_tests, 1):
                print(f"  {i}. {fail['test']}")
                print(f"     Reason: {fail['reason']}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"\nSuccess rate: {success_rate:.1f}%")
        
        return 0 if len(self.failed_tests) == 0 else 1

def main():
    print("="*60)
    print("PHASE 7: PROGRAMMATIC SEO STUDIO - BACKEND TESTS")
    print("="*60)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = SeoStudioTester(BACKEND_URL)
    
    # Run public endpoint tests
    tester.test_public_endpoints()
    
    # Run admin endpoint tests
    tester.test_admin_endpoints()
    
    # Print summary
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
