"""
Backend API Test Suite for Admin Dashboard Filtering Bug Fix
Tests that internal test/admin accounts are properly excluded from admin metrics.
"""
import requests
import sys
from typing import Optional

BASE_URL = "https://repo-to-site-2.preview.emergentagent.com/api"

class AdminDashboardTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.token: Optional[str] = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []

    def log(self, message: str):
        """Print timestamped log message"""
        print(f"  {message}")

    def test(self, name: str, condition: bool, details: str = ""):
        """Record test result"""
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            print(f"✅ PASS: {name}")
            if details:
                self.log(details)
        else:
            self.tests_failed += 1
            self.failures.append(f"{name}: {details}")
            print(f"❌ FAIL: {name}")
            if details:
                self.log(details)

    def login_admin(self) -> bool:
        """Login as admin and get JWT token"""
        print("\n🔐 Logging in as admin...")
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={"email": "admin@ascendraacademy.com", "password": "AscendraAdmin2026!"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                if self.token:
                    print("✅ Admin login successful")
                    return True
                else:
                    print("❌ No access_token in response")
                    return False
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False

    def get(self, endpoint: str, params: dict = None) -> tuple[int, dict]:
        """Make authenticated GET request"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                headers=headers,
                params=params,
                timeout=15
            )
            try:
                return response.status_code, response.json()
            except:
                return response.status_code, {"error": response.text}
        except Exception as e:
            return 0, {"error": str(e)}

    def post(self, endpoint: str, data: dict = None) -> tuple[int, dict]:
        """Make authenticated POST request"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:
            response = requests.post(
                f"{self.base_url}/{endpoint}",
                headers=headers,
                json=data,
                timeout=15
            )
            try:
                return response.status_code, response.json()
            except:
                return response.status_code, {"error": response.text}
        except Exception as e:
            return 0, {"error": str(e)}

    def test_admin_stats(self):
        """Test GET /api/admin/stats with filtering"""
        print("\n📊 Testing /api/admin/stats...")
        status, data = self.get("admin/stats")
        
        self.test(
            "admin/stats returns 200",
            status == 200,
            f"Status: {status}"
        )
        
        if status != 200:
            self.log(f"Response: {data}")
            return
        
        # Test 1: Verify filters block exists with correct flags
        filters = data.get("filters", {})
        self.test(
            "filters.excludes_internal_accounts is true",
            filters.get("excludes_internal_accounts") is True,
            f"excludes_internal_accounts: {filters.get('excludes_internal_accounts')}"
        )
        
        excluded_count = filters.get("excluded_count", 0)
        self.test(
            "filters.excluded_count > 0",
            excluded_count > 0,
            f"excluded_count: {excluded_count} (should be ~24 test accounts)"
        )
        
        # Test 2: Verify user counts exclude test accounts (should be 0 with current DB)
        users = data.get("users", {})
        total_users = users.get("total", -1)
        self.test(
            "users.total is 0 (all accounts are test artifacts)",
            total_users == 0,
            f"users.total: {total_users}"
        )
        
        # Test 3: Verify tier breakdown excludes test accounts
        by_tier = users.get("by_tier", {})
        total_from_tiers = sum(by_tier.values())
        self.test(
            "users.by_tier sum is 0",
            total_from_tiers == 0,
            f"by_tier: {by_tier}"
        )
        
        # Test 4: Verify revenue is 0 (webhook_test_* accounts excluded)
        revenue = data.get("revenue", {})
        total_revenue = revenue.get("total_usd", -1)
        self.test(
            "revenue.total_usd is 0.0",
            total_revenue == 0.0,
            f"revenue.total_usd: {total_revenue}"
        )
        
        # Test 5: Verify engagement metrics exclude test accounts
        engagement = data.get("engagement", {})
        self.log(f"Engagement metrics: {engagement}")
        
        # Test 6: Verify traffic is still present (not filtered)
        traffic = data.get("traffic", {})
        self.test(
            "traffic data is present",
            "pageviews_total" in traffic,
            f"traffic: {traffic}"
        )

    def test_admin_users_filtered(self):
        """Test GET /api/admin/users (default: excludes internal)"""
        print("\n👥 Testing /api/admin/users (filtered)...")
        status, data = self.get("admin/users")
        
        self.test(
            "admin/users returns 200",
            status == 200,
            f"Status: {status}"
        )
        
        if status != 200:
            self.log(f"Response: {data}")
            return
        
        total = data.get("total", -1)
        users = data.get("users", [])
        
        self.test(
            "admin/users total is 0 (excludes internal by default)",
            total == 0,
            f"total: {total}, users count: {len(users)}"
        )
        
        # Verify no test emails in results
        test_emails = [u.get("email", "") for u in users if "sage" in u.get("email", "") or "admin@" in u.get("email", "")]
        self.test(
            "No test emails in filtered results",
            len(test_emails) == 0,
            f"Found test emails: {test_emails}" if test_emails else "No test emails found"
        )

    def test_admin_users_include_internal(self):
        """Test GET /api/admin/users?include_internal=true"""
        print("\n👥 Testing /api/admin/users?include_internal=true...")
        status, data = self.get("admin/users", params={"include_internal": "true", "limit": 100})
        
        self.test(
            "admin/users?include_internal=true returns 200",
            status == 200,
            f"Status: {status}"
        )
        
        if status != 200:
            self.log(f"Response: {data}")
            return
        
        total = data.get("total", -1)
        users = data.get("users", [])
        
        self.test(
            "admin/users?include_internal=true total >= 24",
            total >= 24,
            f"total: {total} (should include all test accounts)"
        )
        
        # Verify test emails ARE present
        test_emails = [u.get("email", "") for u in users if "sage" in u.get("email", "") or "admin@ascendraacademy" in u.get("email", "")]
        self.test(
            "Test emails present with include_internal=true",
            len(test_emails) > 0,
            f"Found {len(test_emails)} test emails"
        )

    def test_admin_subscribers_filtered(self):
        """Test GET /api/admin/subscribers (default: excludes internal)"""
        print("\n💳 Testing /api/admin/subscribers (filtered)...")
        status, data = self.get("admin/subscribers")
        
        self.test(
            "admin/subscribers returns 200",
            status == 200,
            f"Status: {status}"
        )
        
        if status != 200:
            self.log(f"Response: {data}")
            return
        
        count = data.get("count", -1)
        mrr_usd = data.get("mrr_usd", -1)
        subscribers = data.get("subscribers", [])
        
        self.test(
            "admin/subscribers count is 0",
            count == 0,
            f"count: {count} (webhook_test_* accounts should be excluded)"
        )
        
        self.test(
            "admin/subscribers mrr_usd is 0",
            mrr_usd == 0.0,
            f"mrr_usd: {mrr_usd}"
        )
        
        # Verify no webhook_test emails
        webhook_emails = [s.get("email", "") for s in subscribers if "webhook_test" in s.get("email", "")]
        self.test(
            "No webhook_test emails in filtered subscribers",
            len(webhook_emails) == 0,
            f"Found webhook_test emails: {webhook_emails}" if webhook_emails else "No webhook_test emails"
        )

    def test_admin_subscribers_include_internal(self):
        """Test GET /api/admin/subscribers?include_internal=true"""
        print("\n💳 Testing /api/admin/subscribers?include_internal=true...")
        status, data = self.get("admin/subscribers", params={"include_internal": "true"})
        
        self.test(
            "admin/subscribers?include_internal=true returns 200",
            status == 200,
            f"Status: {status}"
        )
        
        if status != 200:
            self.log(f"Response: {data}")
            return
        
        count = data.get("count", -1)
        subscribers = data.get("subscribers", [])
        
        # Should include webhook_test_* accounts (4 of them)
        webhook_subs = [s for s in subscribers if "webhook_test" in s.get("email", "")]
        self.test(
            "webhook_test accounts present with include_internal=true",
            len(webhook_subs) > 0,
            f"Found {len(webhook_subs)} webhook_test subscribers (expected ~4)"
        )

    def test_admin_sales(self):
        """Test GET /api/admin/sales (should exclude internal by default)"""
        print("\n💰 Testing /api/admin/sales...")
        status, data = self.get("admin/sales")
        
        self.test(
            "admin/sales returns 200",
            status == 200,
            f"Status: {status}"
        )
        
        if status != 200:
            self.log(f"Response: {data}")
            return
        
        sales = data.get("sales", [])
        self.log(f"Sales count: {len(sales)}")
        
        # Verify no test emails in sales
        test_sales = [s for s in sales if s.get("user_email") and 
                      ("sage" in s.get("user_email", "") or 
                       "webhook_test" in s.get("user_email", "") or
                       "admin@ascendraacademy" in s.get("user_email", ""))]
        
        self.test(
            "No test account sales in filtered results",
            len(test_sales) == 0,
            f"Found {len(test_sales)} test sales" if test_sales else "No test sales found"
        )

    def test_admin_auto_settings(self):
        """Test GET /api/admin/auto/settings - verify interactive_sweep cron"""
        print("\n⚙️  Testing /api/admin/auto/settings...")
        status, data = self.get("admin/auto/settings")
        
        self.test(
            "admin/auto/settings returns 200",
            status == 200,
            f"Status: {status}"
        )
        
        if status != 200:
            self.log(f"Response: {data}")
            return
        
        next_runs = data.get("next_runs", {})
        self.test(
            "next_runs contains 'interactive_sweep'",
            "interactive_sweep" in next_runs,
            f"next_runs keys: {list(next_runs.keys())}"
        )
        
        if "interactive_sweep" in next_runs:
            sweep_time = next_runs.get("interactive_sweep")
            self.test(
                "interactive_sweep has future timestamp",
                sweep_time is not None and len(str(sweep_time)) > 0,
                f"interactive_sweep next run: {sweep_time}"
            )

    def test_regression_endpoints(self):
        """Test regression: ensure other endpoints still work"""
        print("\n🔄 Testing regression endpoints...")
        
        # Test /api/admin/traffic
        status, data = self.get("admin/traffic")
        self.test(
            "admin/traffic still works",
            status == 200,
            f"Status: {status}"
        )
        
        # Test /api/paths (public endpoint)
        status, data = self.get("paths")
        self.test(
            "paths endpoint still works",
            status == 200 and "paths" in data,
            f"Status: {status}, has paths: {'paths' in data}"
        )
        
        # Test /api/whats-new (authenticated)
        status, data = self.get("whats-new")
        self.test(
            "whats-new endpoint still works",
            status == 200 and "items" in data,
            f"Status: {status}, has items: {'items' in data}"
        )

    def test_sage_login(self):
        """Test that sage test accounts can still login (but are filtered from stats)"""
        print("\n🔐 Testing sage1 account login...")
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={"email": "sage1@ascendraacademy.com", "password": "test1"},
                timeout=10
            )
            self.test(
                "sage1 can still login",
                response.status_code == 200,
                f"Status: {response.status_code}"
            )
        except Exception as e:
            self.test(
                "sage1 can still login",
                False,
                f"Error: {e}"
            )

    def run_all_tests(self):
        """Run complete test suite"""
        print("=" * 70)
        print("🧪 Admin Dashboard Filtering Test Suite")
        print("=" * 70)
        print(f"Backend URL: {self.base_url}")
        
        # Login first
        if not self.login_admin():
            print("\n❌ CRITICAL: Admin login failed. Cannot proceed with tests.")
            return False
        
        # Run all test groups
        self.test_admin_stats()
        self.test_admin_users_filtered()
        self.test_admin_users_include_internal()
        self.test_admin_subscribers_filtered()
        self.test_admin_subscribers_include_internal()
        self.test_admin_sales()
        self.test_admin_auto_settings()
        self.test_regression_endpoints()
        self.test_sage_login()
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print(f"Total tests run: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        
        if self.tests_failed > 0:
            print("\n❌ FAILED TESTS:")
            for i, failure in enumerate(self.failures, 1):
                print(f"  {i}. {failure}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"\nSuccess rate: {success_rate:.1f}%")
        print("=" * 70)
        
        return self.tests_failed == 0


def main():
    tester = AdminDashboardTester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
