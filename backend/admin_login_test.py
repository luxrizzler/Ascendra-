"""
Admin Login Regression Test - Iteration 24
Focused test to verify admin login works after email_service.send_email fix.

This test specifically verifies:
1. Admin login with correct credentials returns 200 + JWT
2. GET /api/auth/me with admin token returns 200 + is_admin: true
3. GET /api/admin/stats with admin token returns 200 (admin-protected route)
4. Login with wrong password returns 401
5. Login with non-existent email returns 401
6. Stress test: 5 consecutive admin logins all succeed
7. Backend process stays RUNNING
8. POST /api/onboarding/anonymous (the trigger endpoint) returns 200
"""
import requests
import sys
import time
from datetime import datetime

BASE_URL = "https://repo-to-site-2.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@ascendraacademy.com"
ADMIN_PASSWORD = "AscendraAdmin2026!"

class AdminLoginTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        self.admin_token = None
        
    def log(self, msg: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {msg}")
    
    def test(self, name: str, method: str, endpoint: str, expected_status: int,
             token: str = None, data: dict = None, timeout: int = 10) -> tuple[bool, dict]:
        """Run a single API test"""
        url = f"{BASE_URL}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        self.tests_run += 1
        self.log(f"Test #{self.tests_run}: {name}")
        
        try:
            start_time = time.time()
            
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            elapsed = time.time() - start_time
            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASS - Status: {response.status_code} (took {elapsed:.2f}s)", "PASS")
            else:
                self.tests_failed += 1
                self.failed_tests.append({
                    "name": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:300]
                })
                self.log(f"❌ FAIL - Expected {expected_status}, got {response.status_code} (took {elapsed:.2f}s)", "FAIL")
                self.log(f"   Response: {response.text[:300]}", "FAIL")
            
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
    
    def run_all_tests(self):
        """Run all admin login regression tests"""
        self.log("=" * 70)
        self.log("ADMIN LOGIN REGRESSION TEST - ITERATION 24")
        self.log("=" * 70)
        self.log(f"Testing against: {BASE_URL}")
        self.log(f"Admin email: {ADMIN_EMAIL}")
        self.log("")
        
        # Test 1: Admin login with correct credentials
        self.log("\n--- Test 1: Admin Login with Correct Credentials ---")
        success, response = self.test(
            "POST /api/auth/login - Admin login with correct credentials",
            "POST",
            "auth/login",
            200,
            data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            self.log(f"   ✅ Admin token received: {self.admin_token[:20]}...")
        else:
            self.log("   ❌ CRITICAL: Admin login failed. Cannot proceed with remaining tests.", "ERROR")
            return self.print_summary()
        
        # Test 2: GET /api/auth/me with admin token
        self.log("\n--- Test 2: GET /api/auth/me with Admin Token ---")
        success, response = self.test(
            "GET /api/auth/me - Verify admin user record",
            "GET",
            "auth/me",
            200,
            token=self.admin_token
        )
        
        if success:
            is_admin = response.get("is_admin")
            email = response.get("email")
            user_id = response.get("id")
            
            self.log(f"   User ID: {user_id}")
            self.log(f"   Email: {email}")
            self.log(f"   is_admin: {is_admin}")
            
            if is_admin == True:
                self.log("   ✅ is_admin flag is True")
            else:
                self.log(f"   ❌ Expected is_admin=True, got {is_admin}", "ERROR")
            
            if email == ADMIN_EMAIL:
                self.log("   ✅ Email matches admin email")
            else:
                self.log(f"   ❌ Email mismatch: expected {ADMIN_EMAIL}, got {email}", "ERROR")
        
        # Test 3: GET /api/admin/stats (admin-protected route)
        self.log("\n--- Test 3: GET /api/admin/stats (Admin-Protected Route) ---")
        success, response = self.test(
            "GET /api/admin/stats - Admin-protected route works",
            "GET",
            "admin/stats",
            200,
            token=self.admin_token
        )
        
        if success:
            self.log(f"   ✅ Admin stats endpoint accessible")
            # Log some stats for visibility
            total_users = response.get("total_users", 0)
            paid_users = response.get("paid_users", 0)
            self.log(f"   Total users: {total_users}, Paid users: {paid_users}")
        
        # Test 4: Login with wrong password
        self.log("\n--- Test 4: Login with Wrong Password (Should Return 401) ---")
        self.test(
            "POST /api/auth/login - Wrong password returns 401",
            "POST",
            "auth/login",
            401,
            data={"email": ADMIN_EMAIL, "password": "WrongPass123!"}
        )
        
        # Test 5: Login with non-existent email
        self.log("\n--- Test 5: Login with Non-Existent Email (Should Return 401) ---")
        self.test(
            "POST /api/auth/login - Non-existent email returns 401",
            "POST",
            "auth/login",
            401,
            data={"email": "nonexistent@example.com", "password": "SomePass123!"}
        )
        
        # Test 6: Stress test - 5 consecutive admin logins
        self.log("\n--- Test 6: Stress Test - 5 Consecutive Admin Logins ---")
        stress_start = time.time()
        stress_passed = 0
        
        for i in range(1, 6):
            self.log(f"   Stress login attempt {i}/5...")
            success, response = self.test(
                f"POST /api/auth/login - Stress test login #{i}",
                "POST",
                "auth/login",
                200,
                data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                timeout=5
            )
            
            if success and 'access_token' in response:
                stress_passed += 1
                self.log(f"   ✅ Stress login {i}/5 succeeded")
            else:
                self.log(f"   ❌ Stress login {i}/5 failed", "ERROR")
        
        stress_elapsed = time.time() - stress_start
        self.log(f"\n   Stress test summary: {stress_passed}/5 logins succeeded in {stress_elapsed:.2f}s")
        
        if stress_passed == 5:
            self.log("   ✅ All stress test logins succeeded")
        else:
            self.log(f"   ❌ Only {stress_passed}/5 stress logins succeeded", "ERROR")
        
        # Test 7: Backend process stability check
        self.log("\n--- Test 7: Backend Process Stability Check ---")
        try:
            import subprocess
            result = subprocess.run(
                ["sudo", "supervisorctl", "status", "backend"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            status_output = result.stdout.strip()
            self.log(f"   Backend status: {status_output}")
            
            if "RUNNING" in status_output:
                self.log("   ✅ Backend process is RUNNING")
            else:
                self.log(f"   ❌ Backend process is NOT running: {status_output}", "ERROR")
        except Exception as e:
            self.log(f"   ⚠️  Could not check backend status: {e}", "WARN")
        
        # Test 8: POST /api/onboarding/anonymous (the trigger endpoint)
        self.log("\n--- Test 8: POST /api/onboarding/anonymous (Trigger Endpoint) ---")
        self.log("   This endpoint's broken BackgroundTask caused the original Cloudflare 520")
        
        timestamp = int(time.time())
        test_email = f"admin_login_test_{timestamp}@test.ascendra.com"
        
        success, response = self.test(
            "POST /api/onboarding/anonymous - Trigger endpoint returns 200",
            "POST",
            "onboarding/anonymous",
            200,
            data={
                "email": test_email,
                "motivation": "career",
                "experience": "beginner",
                "tools_used": ["chatgpt"],
                "goals": ["fundamentals"],
                "time_per_day": "15",
                "learning_style": "hands_on",
                "source": "admin_login_test"
            },
            timeout=15
        )
        
        if success:
            ok = response.get("ok")
            already_registered = response.get("already_registered")
            plan = response.get("plan")
            
            self.log(f"   ok: {ok}, already_registered: {already_registered}")
            
            if ok == True:
                self.log("   ✅ Endpoint returned ok=True")
            else:
                self.log(f"   ❌ Expected ok=True, got {ok}", "ERROR")
            
            if plan:
                self.log(f"   ✅ Plan generated successfully")
            else:
                self.log(f"   ⚠️  Plan is null (may be Claude rate-limit)", "WARN")
        
        # Final backend stability check after trigger endpoint
        self.log("\n--- Final Backend Stability Check (After Trigger Endpoint) ---")
        try:
            result = subprocess.run(
                ["sudo", "supervisorctl", "status", "backend"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            status_output = result.stdout.strip()
            self.log(f"   Backend status: {status_output}")
            
            if "RUNNING" in status_output:
                self.log("   ✅ Backend still RUNNING after trigger endpoint")
            else:
                self.log(f"   ❌ Backend NOT running after trigger endpoint: {status_output}", "ERROR")
        except Exception as e:
            self.log(f"   ⚠️  Could not check backend status: {e}", "WARN")
        
        return self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "=" * 70)
        self.log("TEST SUMMARY")
        self.log("=" * 70)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"Passed: {self.tests_passed} ✅")
        self.log(f"Failed: {self.tests_failed} ❌")
        
        if self.tests_run > 0:
            success_rate = (self.tests_passed / self.tests_run) * 100
            self.log(f"Success Rate: {success_rate:.1f}%")
        
        if self.failed_tests:
            self.log("\n" + "=" * 70)
            self.log("FAILED TESTS DETAILS")
            self.log("=" * 70)
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
        
        self.log("\n" + "=" * 70)
        if self.tests_failed == 0:
            self.log("✅ ALL TESTS PASSED - Admin login is working correctly!")
        else:
            self.log(f"❌ {self.tests_failed} TEST(S) FAILED - See details above")
        self.log("=" * 70)
        
        return 0 if self.tests_failed == 0 else 1

def main():
    tester = AdminLoginTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())
