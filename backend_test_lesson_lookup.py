"""
Backend test for lesson lookup optimization (multikey index on modules.lessons.id).

Tests:
1. REGRESSION: GET /api/lessons/{lesson_id} for existing lesson (f1l1)
2. REGRESSION: GET /api/lessons/{lesson_id} with non-existent lesson_id (404)
3. REGRESSION: GET /api/paths (should still work)
4. REGRESSION: Lesson completion flow (POST /api/progress/complete)
5. REGRESSION: Admin CRUD - create lesson and fetch it
6. REGRESSION: Admin auth
7. PERFORMANCE: 5 consecutive calls to GET /api/lessons/f1l1 (< 200ms avg)
"""
import requests
import sys
import time
import uuid
from datetime import datetime

BASE_URL = "https://repo-to-site-2.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@ascendraacademy.com"
ADMIN_PASSWORD = "AscendraAdmin2026!"
SAGE_EMAIL = "sage1@ascendraacademy.com"
SAGE_PASSWORD = "test1"

class LessonLookupTester:
    def __init__(self):
        self.admin_token = None
        self.sage_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        self.performance_results = []

    def log_pass(self, test_name):
        self.tests_passed += 1
        print(f"✅ PASS: {test_name}")

    def log_fail(self, test_name, reason):
        self.tests_failed += 1
        self.errors.append({"test": test_name, "reason": reason})
        print(f"❌ FAIL: {test_name} - {reason}")

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None, check_json=True):
        """Run a single API test"""
        url = f"{BASE_URL}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing: {name}")
        print(f"   Endpoint: {method} {endpoint}")
        
        try:
            start_time = time.time()
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            elapsed_ms = (time.time() - start_time) * 1000

            print(f"   Status: {response.status_code} ({elapsed_ms:.1f}ms)")
            
            if response.status_code != expected_status:
                self.log_fail(name, f"Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"   Response: {response.text[:500]}")
                except:
                    pass
                return False, {}, elapsed_ms

            if check_json:
                try:
                    json_data = response.json()
                    self.log_pass(name)
                    return True, json_data, elapsed_ms
                except Exception as e:
                    self.log_fail(name, f"Invalid JSON response: {str(e)}")
                    return False, {}, elapsed_ms
            else:
                self.log_pass(name)
                return True, {}, elapsed_ms

        except requests.exceptions.Timeout:
            self.log_fail(name, "Request timeout (30s)")
            return False, {}, 30000
        except Exception as e:
            self.log_fail(name, f"Exception: {str(e)}")
            return False, {}, 0

    def test_admin_login(self):
        """Test admin authentication"""
        print("\n" + "="*70)
        print("TEST 1: Admin Authentication")
        print("="*70)
        
        success, response, _ = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   ✓ Admin token obtained: {self.admin_token[:20]}...")
            return True
        else:
            print("   ✗ Failed to obtain admin token")
            return False

    def test_sage_login(self):
        """Test sage user authentication"""
        print("\n" + "="*70)
        print("TEST 2: Sage User Authentication")
        print("="*70)
        
        success, response, _ = self.run_test(
            "Sage Login",
            "POST",
            "auth/login",
            200,
            data={"email": SAGE_EMAIL, "password": SAGE_PASSWORD}
        )
        
        if success and 'access_token' in response:
            self.sage_token = response['access_token']
            print(f"   ✓ Sage token obtained: {self.sage_token[:20]}...")
            return True
        else:
            print("   ✗ Failed to obtain sage token")
            return False

    def test_lesson_f1l1(self):
        """Test GET /api/lessons/f1l1 (existing free-tier lesson)"""
        print("\n" + "="*70)
        print("TEST 3: GET /api/lessons/f1l1 (Existing Lesson)")
        print("="*70)
        print("   Expected: Full lesson dict with path/module context")
        
        success, response, elapsed_ms = self.run_test(
            "Fetch Lesson f1l1",
            "GET",
            "lessons/f1l1",
            200,
            token=self.sage_token
        )
        
        if success:
            # Verify required fields
            required_fields = ['id', 'title', 'path_id', 'path_title', 'path_color', 
                             'path_tier', 'module_id', 'module_title', 'cards', 
                             'quiz', 'xp', 'duration_min']
            missing_fields = [f for f in required_fields if f not in response]
            
            if missing_fields:
                self.log_fail("Lesson f1l1 - Required Fields", f"Missing fields: {missing_fields}")
                print(f"   ✗ Missing fields: {missing_fields}")
                return False
            
            # Verify specific values
            if response.get('path_id') != 'fundamentals':
                self.log_fail("Lesson f1l1 - Path ID", f"Expected 'fundamentals', got '{response.get('path_id')}'")
                return False
            
            if response.get('module_id') != 'fundamentals-101':
                self.log_fail("Lesson f1l1 - Module ID", f"Expected 'fundamentals-101', got '{response.get('module_id')}'")
                return False
            
            print(f"   ✓ All required fields present")
            print(f"   ✓ path_id: {response.get('path_id')}")
            print(f"   ✓ module_id: {response.get('module_id')}")
            print(f"   ✓ title: {response.get('title')}")
            self.log_pass("Lesson f1l1 - Required Fields")
            self.log_pass("Lesson f1l1 - Path/Module Context")
            return True
        
        return False

    def test_lesson_not_found(self):
        """Test GET /api/lessons/{non-existent} (should return 404)"""
        print("\n" + "="*70)
        print("TEST 4: GET /api/lessons/lesson-does-not-exist-xyz (Non-existent)")
        print("="*70)
        print("   Expected: 404 NOT FOUND")
        
        success, response, _ = self.run_test(
            "Fetch Non-existent Lesson",
            "GET",
            "lessons/lesson-does-not-exist-xyz",
            404,
            token=self.sage_token,
            check_json=False
        )
        
        if success:
            print(f"   ✓ Correctly returned 404 for non-existent lesson")
            return True
        
        return False

    def test_paths_list(self):
        """Test GET /api/paths (should still work)"""
        print("\n" + "="*70)
        print("TEST 5: GET /api/paths (Regression)")
        print("="*70)
        print("   Expected: List of all curriculum paths")
        
        success, response, _ = self.run_test(
            "List Paths",
            "GET",
            "paths",
            200,
            token=self.sage_token
        )
        
        if success:
            paths = response.get('paths', [])
            if len(paths) >= 1:
                print(f"   ✓ Found {len(paths)} paths")
                self.log_pass("Paths List - Count")
                return True
            else:
                self.log_fail("Paths List", "No paths returned")
                return False
        
        return False

    def test_lesson_completion(self):
        """Test POST /api/progress/complete with f1l1"""
        print("\n" + "="*70)
        print("TEST 6: POST /api/progress/complete (Lesson Completion)")
        print("="*70)
        print("   Expected: Award XP and return success payload")
        
        success, response, _ = self.run_test(
            "Complete Lesson f1l1",
            "POST",
            "progress/complete",
            200,
            data={"lesson_id": "f1l1"},
            token=self.sage_token
        )
        
        if success:
            # Verify response structure
            if 'progress' not in response:
                self.log_fail("Lesson Completion", "Missing 'progress' in response")
                return False
            
            if 'awarded_xp' not in response:
                self.log_fail("Lesson Completion", "Missing 'awarded_xp' in response")
                return False
            
            awarded_xp = response.get('awarded_xp', 0)
            print(f"   ✓ Awarded XP: {awarded_xp}")
            print(f"   ✓ Total XP: {response.get('progress', {}).get('total_xp', 0)}")
            self.log_pass("Lesson Completion - XP Award")
            return True
        
        return False

    def test_admin_crud(self):
        """Test admin CRUD - create lesson and fetch it"""
        print("\n" + "="*70)
        print("TEST 7: Admin CRUD (Create Lesson + Fetch)")
        print("="*70)
        print("   Expected: Create lesson via admin endpoint, then fetch it")
        
        # Generate unique lesson ID
        lesson_id = f"test-lesson-{uuid.uuid4().hex[:8]}"
        
        # Create lesson
        success, response, _ = self.run_test(
            "Admin Create Lesson",
            "POST",
            "admin/curriculum/paths/fundamentals/modules/fundamentals-101/lessons",
            200,
            data={
                "id": lesson_id,
                "title": "Test Lesson for Index Verification",
                "duration_min": 5,
                "xp": 50,
                "cards": [{"title": "Test Card", "body": "Test content for index verification", "kind": "text"}],
                "quiz": {
                    "question": "Test question?",
                    "options": ["A", "B", "C", "D"],
                    "answer_index": 0,
                    "explanation": "Test explanation"
                }
            },
            token=self.admin_token
        )
        
        if not success:
            print(f"   ✗ Failed to create lesson")
            return False
        
        print(f"   ✓ Created lesson: {lesson_id}")
        
        # Wait a moment for index to update
        time.sleep(0.5)
        
        # Fetch the newly created lesson
        success, response, _ = self.run_test(
            "Fetch Newly Created Lesson",
            "GET",
            f"lessons/{lesson_id}",
            200,
            token=self.admin_token
        )
        
        if success:
            if response.get('id') == lesson_id:
                print(f"   ✓ Successfully fetched newly created lesson")
                print(f"   ✓ Lesson title: {response.get('title')}")
                self.log_pass("Admin CRUD - Create + Fetch")
                return True
            else:
                self.log_fail("Admin CRUD", f"Lesson ID mismatch: expected {lesson_id}, got {response.get('id')}")
                return False
        
        return False

    def test_performance(self):
        """Test performance - 5 consecutive calls to GET /api/lessons/f1l1"""
        print("\n" + "="*70)
        print("TEST 8: Performance Sanity Check")
        print("="*70)
        print("   Expected: Average latency < 200ms for 5 consecutive calls")
        
        latencies = []
        for i in range(5):
            success, response, elapsed_ms = self.run_test(
                f"Performance Test {i+1}/5",
                "GET",
                "lessons/f1l1",
                200,
                token=self.sage_token
            )
            
            if success:
                latencies.append(elapsed_ms)
                print(f"   Call {i+1}: {elapsed_ms:.1f}ms")
            else:
                print(f"   ✗ Call {i+1} failed")
                return False
        
        avg_latency = sum(latencies) / len(latencies)
        print(f"\n   Average latency: {avg_latency:.1f}ms")
        
        if avg_latency < 200:
            print(f"   ✓ Performance check passed (< 200ms)")
            self.log_pass("Performance - Average Latency")
            self.performance_results.append({
                "test": "GET /api/lessons/f1l1",
                "calls": 5,
                "avg_latency_ms": avg_latency,
                "latencies": latencies
            })
            return True
        else:
            self.log_fail("Performance", f"Average latency {avg_latency:.1f}ms exceeds 200ms threshold")
            return False

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total tests run: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        
        if self.performance_results:
            print("\n📊 PERFORMANCE RESULTS:")
            for result in self.performance_results:
                print(f"   {result['test']}: {result['avg_latency_ms']:.1f}ms avg ({result['calls']} calls)")
        
        if self.errors:
            print("\n❌ FAILED TESTS:")
            for error in self.errors:
                print(f"   - {error['test']}: {error['reason']}")
        
        if self.tests_failed == 0:
            print("\n✅ ALL TESTS PASSED - Lesson lookup optimization verified!")
            print("\nVERIFICATION COMPLETE:")
            print("  ✓ Lesson lookup returns correct data (f1l1)")
            print("  ✓ Non-existent lesson returns 404")
            print("  ✓ Paths listing still works")
            print("  ✓ Lesson completion flow works")
            print("  ✓ Admin CRUD operations work")
            print("  ✓ Performance is acceptable (< 200ms avg)")
            return 0
        else:
            print("\n❌ SOME TESTS FAILED - See details above")
            return 1

def main():
    print("="*70)
    print("Lesson Lookup Optimization Verification Test Suite")
    print("="*70)
    print(f"Backend URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    print(f"Sage User: {SAGE_EMAIL}")
    print(f"Started: {datetime.now().isoformat()}")
    
    tester = LessonLookupTester()
    
    # Run tests in order
    if not tester.test_admin_login():
        print("\n❌ CRITICAL: Admin login failed. Cannot continue.")
        return 1
    
    if not tester.test_sage_login():
        print("\n❌ CRITICAL: Sage login failed. Cannot continue.")
        return 1
    
    # Give backend a moment to settle
    time.sleep(0.5)
    
    # Core regression tests
    tester.test_lesson_f1l1()
    tester.test_lesson_not_found()
    tester.test_paths_list()
    tester.test_lesson_completion()
    tester.test_admin_crud()
    
    # Performance test
    tester.test_performance()
    
    # Print summary
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
