"""
Backend API tests for Phase 7 (SEO Studio) + Phase 8 (Auto-Pilot Content Engine)
Tests all public and admin endpoints.
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


class AutoPilotTester:
    """Phase 8: Auto-Pilot Content Engine tests"""
    def __init__(self, base_url=BACKEND_URL):
        self.base_url = base_url.rstrip("/")
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
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
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                return True, response
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:300]}")
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

    def test_auto_pilot_endpoints(self):
        """Test all auto-pilot endpoints"""
        print("\n" + "="*60)
        print("TESTING AUTO-PILOT ENDPOINTS (Phase 8)")
        print("="*60)

        # Login as admin first
        if not self.login_admin():
            print("❌ CRITICAL: Admin login failed, skipping auto-pilot tests")
            return

        auth_headers = {"Authorization": f"Bearer {self.admin_token}"}

        # Test 1: GET /api/admin/auto/settings
        success, response = self.run_test(
            "GET /api/admin/auto/settings",
            "GET",
            "/api/admin/auto/settings",
            200,
            headers=auth_headers
        )
        if success and response:
            data = response.json()
            required_fields = ["paused", "auto_publish", "quality_threshold", "next_runs"]
            missing = [f for f in required_fields if f not in data]
            if missing:
                print(f"⚠️  WARNING: Missing fields in settings: {missing}")
            else:
                print(f"✅ All required settings fields present")
                print(f"   Paused: {data.get('paused')}, Auto-publish: {data.get('auto_publish')}, Threshold: {data.get('quality_threshold')}")
                next_runs = data.get('next_runs', {})
                if next_runs:
                    print(f"   Next runs: daily_lesson={next_runs.get('daily_lesson')}, monday_path={next_runs.get('monday_path')}, daily_digest={next_runs.get('daily_digest')}")

        # Test 2: POST /api/admin/auto/settings (pause)
        success, response = self.run_test(
            "POST /api/admin/auto/settings (pause)",
            "POST",
            "/api/admin/auto/settings",
            200,
            data={"paused": True},
            headers=auth_headers
        )
        if success and response:
            data = response.json()
            if data.get('paused') == True:
                print(f"✅ Successfully paused auto-pilot")
            else:
                print(f"⚠️  WARNING: Pause flag not set correctly")

        # Test 3: POST /api/admin/auto/settings (resume)
        time.sleep(0.5)
        success, response = self.run_test(
            "POST /api/admin/auto/settings (resume)",
            "POST",
            "/api/admin/auto/settings",
            200,
            data={"paused": False},
            headers=auth_headers
        )
        if success and response:
            data = response.json()
            if data.get('paused') == False:
                print(f"✅ Successfully resumed auto-pilot")
            else:
                print(f"⚠️  WARNING: Resume flag not set correctly")

        # Test 4: POST /api/admin/auto/settings (disable auto-publish)
        time.sleep(0.5)
        success, response = self.run_test(
            "POST /api/admin/auto/settings (disable auto-publish)",
            "POST",
            "/api/admin/auto/settings",
            200,
            data={"auto_publish": False},
            headers=auth_headers
        )
        if success and response:
            data = response.json()
            if data.get('auto_publish') == False:
                print(f"✅ Successfully disabled auto-publish")

        # Test 5: POST /api/admin/auto/settings (re-enable auto-publish)
        time.sleep(0.5)
        success, response = self.run_test(
            "POST /api/admin/auto/settings (re-enable auto-publish)",
            "POST",
            "/api/admin/auto/settings",
            200,
            data={"auto_publish": True},
            headers=auth_headers
        )
        if success and response:
            data = response.json()
            if data.get('auto_publish') == True:
                print(f"✅ Successfully re-enabled auto-publish")

        # Test 6: GET /api/admin/auto/queue
        success, response = self.run_test(
            "GET /api/admin/auto/queue",
            "GET",
            "/api/admin/auto/queue",
            200,
            headers=auth_headers
        )
        queue_items = []
        if success and response:
            data = response.json()
            queue_items = data.get('items', [])
            count = data.get('count', 0)
            print(f"   Found {len(queue_items)} queue items (count={count})")
            if len(queue_items) >= 28:
                print(f"✅ Expected 28+ items (32 default minus some processed), got {len(queue_items)}")
            else:
                print(f"⚠️  WARNING: Expected 28+ items, got {len(queue_items)}")
            
            # Check for different statuses
            statuses = {}
            for item in queue_items:
                status = item.get('status', 'unknown')
                statuses[status] = statuses.get(status, 0) + 1
            print(f"   Status breakdown: {statuses}")

        # Test 7: POST /api/admin/auto/queue (add new item)
        success, response = self.run_test(
            "POST /api/admin/auto/queue (add test item)",
            "POST",
            "/api/admin/auto/queue",
            200,
            data={"topic": "Test topic XYZ", "kind": "lesson", "level": "Beginner"},
            headers=auth_headers
        )
        new_item_id = None
        if success and response:
            data = response.json()
            new_item_id = data.get('id')
            if new_item_id:
                print(f"✅ Successfully added queue item with id: {new_item_id}")

        # Test 8: GET /api/admin/auto/queue (verify new item)
        if new_item_id:
            time.sleep(0.5)
            success, response = self.run_test(
                "GET /api/admin/auto/queue (verify new item)",
                "GET",
                "/api/admin/auto/queue",
                200,
                headers=auth_headers
            )
            if success and response:
                data = response.json()
                items = data.get('items', [])
                found = any(item.get('id') == new_item_id for item in items)
                if found:
                    print(f"✅ New item found in queue")
                else:
                    print(f"⚠️  WARNING: New item not found in queue")

        # Test 9: DELETE /api/admin/auto/queue/{id} (remove test item)
        if new_item_id:
            time.sleep(0.5)
            success, response = self.run_test(
                f"DELETE /api/admin/auto/queue/{new_item_id}",
                "DELETE",
                f"/api/admin/auto/queue/{new_item_id}",
                200,
                headers=auth_headers
            )
            if success:
                print(f"✅ Successfully removed test item")

        # Test 10: GET /api/admin/auto/runs
        success, response = self.run_test(
            "GET /api/admin/auto/runs",
            "GET",
            "/api/admin/auto/runs",
            200,
            headers=auth_headers
        )
        if success and response:
            data = response.json()
            runs = data.get('runs', [])
            count = data.get('count', 0)
            print(f"   Found {len(runs)} runs (count={count})")
            if len(runs) >= 1:
                print(f"✅ Expected at least 1 run from prior manual test, got {len(runs)}")
                # Show the most recent run
                if runs:
                    recent = runs[0]
                    print(f"   Most recent: kind={recent.get('kind')}, status={recent.get('status')}")
                    summary = recent.get('summary', {})
                    if summary.get('grades'):
                        grades = summary['grades']
                        print(f"   Grades: acc={grades.get('accuracy')}, cl={grades.get('clarity')}, br={grades.get('brand_fit')}, dp={grades.get('depth')}")
            else:
                print(f"⚠️  WARNING: Expected at least 1 run, got {len(runs)}")

        # Test 11: POST /api/admin/auto/run {kind:'digest'} (safe to test)
        print("\n📧 Testing digest email send (safe, no Claude calls)...")
        success, response = self.run_test(
            "POST /api/admin/auto/run (digest)",
            "POST",
            "/api/admin/auto/run",
            200,
            data={"kind": "digest"},
            headers=auth_headers
        )
        if success and response:
            data = response.json()
            print(f"   Result: ok={data.get('ok')}, skipped={data.get('skipped')}, reason={data.get('reason')}")
            if data.get('ok'):
                print(f"✅ Digest endpoint working (may have skipped if no runs in last 24h)")

        # Test 12: GET /api/admin/auto/queue/{id} (get single item)
        if queue_items:
            first_item = queue_items[0]
            item_id = first_item.get('id')
            if item_id:
                success, response = self.run_test(
                    f"GET /api/admin/auto/queue/{item_id}",
                    "GET",
                    f"/api/admin/auto/queue/{item_id}",
                    200,
                    headers=auth_headers
                )
                if success and response:
                    data = response.json()
                    if data.get('id') == item_id:
                        print(f"✅ Successfully retrieved single queue item")
                        if data.get('status') == 'needs_review' and data.get('draft'):
                            print(f"   Item has draft preserved (needs_review status)")

        # Test 13: POST /api/admin/auto/queue/{id}/publish on pending item (should 400)
        pending_items = [item for item in queue_items if item.get('status') == 'pending']
        if pending_items:
            pending_id = pending_items[0].get('id')
            if pending_id:
                success, response = self.run_test(
                    f"POST /api/admin/auto/queue/{pending_id}/publish (should 400 - pending)",
                    "POST",
                    f"/api/admin/auto/queue/{pending_id}/publish",
                    400,
                    headers=auth_headers
                )
                if success:
                    print(f"✅ Correctly rejected publish on pending item")

        # Test 14: Check for needs_review items with draft
        needs_review_items = [item for item in queue_items if item.get('status') == 'needs_review']
        if needs_review_items:
            print(f"\n📝 Found {len(needs_review_items)} items needing review")
            for item in needs_review_items[:3]:
                print(f"   - {item.get('topic')} (grades: {item.get('grades')})")

        print("\n⚠️  NOTE: Skipped daily_lesson and monday_path manual runs (60+ second Claude calls)")
        print("   These were already verified by the main agent in prior testing.")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("AUTO-PILOT TEST SUMMARY")
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
    print("PHASE 7 + 8: SEO STUDIO + AUTO-PILOT - BACKEND TESTS")
    print("="*60)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run Phase 7 tests (SEO Studio)
    seo_tester = SeoStudioTester(BACKEND_URL)
    seo_tester.test_public_endpoints()
    seo_tester.test_admin_endpoints()
    seo_result = seo_tester.print_summary()
    
    # Run Phase 8 tests (Auto-Pilot)
    auto_tester = AutoPilotTester(BACKEND_URL)
    auto_tester.test_auto_pilot_endpoints()
    auto_result = auto_tester.print_summary()
    
    # Combined summary
    print("\n" + "="*60)
    print("COMBINED SUMMARY")
    print("="*60)
    total_tests = seo_tester.tests_run + auto_tester.tests_run
    total_passed = seo_tester.tests_passed + auto_tester.tests_passed
    total_failed = len(seo_tester.failed_tests) + len(auto_tester.failed_tests)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"Overall success rate: {success_rate:.1f}%")
    
    return 0 if (seo_result == 0 and auto_result == 0) else 1

if __name__ == "__main__":
    sys.exit(main())
