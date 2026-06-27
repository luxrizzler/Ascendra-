"""
Backend test for /api/admin/stats endpoint after MongoDB aggregation optimization.
Tests response shape compatibility and revenue calculation correctness.
"""
import requests
import sys
import uuid
from datetime import datetime, timezone
from pymongo import MongoClient

BASE_URL = "https://repo-to-site-2.preview.emergentagent.com"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "ascendra_db"

class AdminStatsTest:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_session_ids = []  # Track test sessions for cleanup
        
        # MongoDB connection for direct data insertion
        self.mongo_client = MongoClient(MONGO_URL)
        self.db = self.mongo_client[DB_NAME]
        self.sessions_col = self.db["payment_sessions"]

    def log(self, msg, level="INFO"):
        """Log test messages"""
        print(f"[{level}] {msg}")

    def test(self, name, func):
        """Run a single test"""
        self.tests_run += 1
        self.log(f"\n{'='*60}")
        self.log(f"TEST {self.tests_run}: {name}")
        self.log('='*60)
        try:
            func()
            self.tests_passed += 1
            self.log(f"✅ PASSED: {name}", "SUCCESS")
            return True
        except AssertionError as e:
            self.log(f"❌ FAILED: {name}", "ERROR")
            self.log(f"   Reason: {str(e)}", "ERROR")
            return False
        except Exception as e:
            self.log(f"❌ ERROR: {name}", "ERROR")
            self.log(f"   Exception: {str(e)}", "ERROR")
            return False

    def admin_login(self):
        """Test admin login and get token"""
        self.log("Attempting admin login...")
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"email": "admin@ascendraacademy.com", "password": "AscendraAdmin2026!"},
            timeout=10
        )
        assert response.status_code == 200, f"Login failed with status {response.status_code}: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in login response"
        self.token = data["access_token"]
        self.log(f"✅ Admin login successful, token obtained")

    def get_admin_stats(self):
        """Fetch /api/admin/stats"""
        assert self.token, "No token available, login first"
        response = requests.get(
            f"{self.base_url}/api/admin/stats",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Stats endpoint failed with status {response.status_code}: {response.text}"
        return response.json()

    def test_response_shape(self):
        """REGRESSION: Verify exact response shape"""
        stats = self.get_admin_stats()
        
        # Top-level keys
        required_keys = ["users", "revenue", "engagement", "traffic"]
        for key in required_keys:
            assert key in stats, f"Missing top-level key: {key}"
        
        # Revenue object shape
        revenue = stats["revenue"]
        revenue_keys = ["total_usd", "mtd_usd", "arr_estimate_usd", "paid_sessions"]
        for key in revenue_keys:
            assert key in revenue, f"Missing revenue key: {key}"
        
        self.log(f"✅ Response shape is correct")
        self.log(f"   Top-level keys: {list(stats.keys())}")
        self.log(f"   Revenue keys: {list(revenue.keys())}")

    def test_revenue_types(self):
        """REGRESSION: Verify all revenue values are numeric"""
        stats = self.get_admin_stats()
        revenue = stats["revenue"]
        
        # Check types
        assert isinstance(revenue["total_usd"], (int, float)), f"total_usd is not numeric: {type(revenue['total_usd'])}"
        assert isinstance(revenue["mtd_usd"], (int, float)), f"mtd_usd is not numeric: {type(revenue['mtd_usd'])}"
        assert isinstance(revenue["arr_estimate_usd"], (int, float)), f"arr_estimate_usd is not numeric: {type(revenue['arr_estimate_usd'])}"
        assert isinstance(revenue["paid_sessions"], int), f"paid_sessions is not int: {type(revenue['paid_sessions'])}"
        
        # Check not null/undefined
        assert revenue["total_usd"] is not None, "total_usd is None"
        assert revenue["mtd_usd"] is not None, "mtd_usd is None"
        assert revenue["arr_estimate_usd"] is not None, "arr_estimate_usd is None"
        assert revenue["paid_sessions"] is not None, "paid_sessions is None"
        
        self.log(f"✅ All revenue values are numeric and not null")
        self.log(f"   total_usd: {revenue['total_usd']} ({type(revenue['total_usd']).__name__})")
        self.log(f"   mtd_usd: {revenue['mtd_usd']} ({type(revenue['mtd_usd']).__name__})")
        self.log(f"   arr_estimate_usd: {revenue['arr_estimate_usd']} ({type(revenue['arr_estimate_usd']).__name__})")
        self.log(f"   paid_sessions: {revenue['paid_sessions']} ({type(revenue['paid_sessions']).__name__})")

    def test_empty_db_zeros(self):
        """REGRESSION: With zero paid sessions, all revenue should be 0.0"""
        # Verify DB state
        paid_count = self.sessions_col.count_documents({"status": "paid"})
        assert paid_count == 0, f"Expected 0 paid sessions, found {paid_count}"
        
        stats = self.get_admin_stats()
        revenue = stats["revenue"]
        
        assert revenue["total_usd"] == 0.0, f"Expected total_usd=0.0, got {revenue['total_usd']}"
        assert revenue["mtd_usd"] == 0.0, f"Expected mtd_usd=0.0, got {revenue['mtd_usd']}"
        assert revenue["arr_estimate_usd"] == 0.0, f"Expected arr_estimate_usd=0.0, got {revenue['arr_estimate_usd']}"
        assert revenue["paid_sessions"] == 0, f"Expected paid_sessions=0, got {revenue['paid_sessions']}"
        
        self.log(f"✅ Empty DB returns correct zeros")
        self.log(f"   Revenue: {revenue}")

    def test_other_top_level_objects(self):
        """REGRESSION: Verify users, engagement, traffic objects are present and numeric"""
        stats = self.get_admin_stats()
        
        # Users
        users = stats["users"]
        assert isinstance(users["total"], int), f"users.total not int: {type(users['total'])}"
        assert isinstance(users["paid"], int), f"users.paid not int: {type(users['paid'])}"
        self.log(f"✅ users object present: total={users['total']}, paid={users['paid']}")
        
        # Engagement
        engagement = stats["engagement"]
        assert isinstance(engagement["lessons_completed"], int), f"engagement.lessons_completed not int: {type(engagement['lessons_completed'])}"
        assert isinstance(engagement["certificates_issued"], int), f"engagement.certificates_issued not int"
        self.log(f"✅ engagement object present: lessons_completed={engagement['lessons_completed']}")
        
        # Traffic
        traffic = stats["traffic"]
        assert isinstance(traffic["pageviews_total"], int), f"traffic.pageviews_total not int"
        self.log(f"✅ traffic object present: pageviews_total={traffic['pageviews_total']}")

    def insert_test_session(self, amount_usd, interval, session_id=None):
        """Insert a test paid session directly into MongoDB"""
        if session_id is None:
            session_id = f"test-session-revenue-{uuid.uuid4()}"
        
        doc = {
            "session_id": session_id,
            "status": "paid",
            "amount_usd": amount_usd,
            "paid_at": datetime.now(timezone.utc),
            "interval": interval,
            "user_id": "test-user-id",
            "tier": "pathfinder",
            "mode": "payment",
            "created_at": datetime.now(timezone.utc),
        }
        self.sessions_col.insert_one(doc)
        self.test_session_ids.append(session_id)
        self.log(f"✅ Inserted test session: {session_id}, amount={amount_usd}, interval={interval}")
        return session_id

    def cleanup_test_sessions(self):
        """Delete all test sessions"""
        if self.test_session_ids:
            result = self.sessions_col.delete_many({"session_id": {"$in": self.test_session_ids}})
            self.log(f"✅ Cleaned up {result.deleted_count} test sessions")
            self.test_session_ids = []

    def test_single_monthly_session(self):
        """POSITIVE PATH: Single monthly session with amount_usd=19.99"""
        # Insert test session
        self.insert_test_session(amount_usd=19.99, interval="monthly")
        
        # Fetch stats
        stats = self.get_admin_stats()
        revenue = stats["revenue"]
        
        # Verify calculations
        assert revenue["total_usd"] == 19.99, f"Expected total_usd=19.99, got {revenue['total_usd']}"
        assert revenue["mtd_usd"] == 19.99, f"Expected mtd_usd=19.99, got {revenue['mtd_usd']}"
        assert revenue["paid_sessions"] == 1, f"Expected paid_sessions=1, got {revenue['paid_sessions']}"
        
        # ARR = monthly * 12
        expected_arr = 19.99 * 12
        assert abs(revenue["arr_estimate_usd"] - expected_arr) < 0.01, \
            f"Expected arr_estimate_usd={expected_arr}, got {revenue['arr_estimate_usd']}"
        
        self.log(f"✅ Single monthly session calculations correct")
        self.log(f"   total_usd: {revenue['total_usd']}")
        self.log(f"   mtd_usd: {revenue['mtd_usd']}")
        self.log(f"   arr_estimate_usd: {revenue['arr_estimate_usd']}")
        self.log(f"   paid_sessions: {revenue['paid_sessions']}")

    def test_two_sessions_mixed(self):
        """POSITIVE PATH: Two sessions (monthly + annual)"""
        # Insert second session (annual)
        self.insert_test_session(amount_usd=199.99, interval="annual")
        
        # Fetch stats
        stats = self.get_admin_stats()
        revenue = stats["revenue"]
        
        # Verify calculations
        # total = 19.99 (from previous test) + 199.99 = 219.98
        expected_total = 19.99 + 199.99
        assert abs(revenue["total_usd"] - expected_total) < 0.01, \
            f"Expected total_usd={expected_total}, got {revenue['total_usd']}"
        
        # mtd should be same as total (both paid this month)
        assert abs(revenue["mtd_usd"] - expected_total) < 0.01, \
            f"Expected mtd_usd={expected_total}, got {revenue['mtd_usd']}"
        
        # paid_sessions = 2
        assert revenue["paid_sessions"] == 2, f"Expected paid_sessions=2, got {revenue['paid_sessions']}"
        
        # ARR = 19.99*12 + 199.99 = 239.88 + 199.99 = 439.87
        expected_arr = 19.99 * 12 + 199.99
        assert abs(revenue["arr_estimate_usd"] - expected_arr) < 0.01, \
            f"Expected arr_estimate_usd={expected_arr}, got {revenue['arr_estimate_usd']}"
        
        self.log(f"✅ Two sessions (monthly + annual) calculations correct")
        self.log(f"   total_usd: {revenue['total_usd']} (expected: {expected_total})")
        self.log(f"   mtd_usd: {revenue['mtd_usd']} (expected: {expected_total})")
        self.log(f"   arr_estimate_usd: {revenue['arr_estimate_usd']} (expected: {expected_arr})")
        self.log(f"   paid_sessions: {revenue['paid_sessions']}")

    def run_all_tests(self):
        """Run all tests in sequence"""
        self.log("\n" + "="*60)
        self.log("STARTING ADMIN STATS ENDPOINT TESTS")
        self.log("="*60)
        
        try:
            # Login first
            self.admin_login()
            
            # REGRESSION TESTS (empty DB state)
            self.test("Response shape is correct", self.test_response_shape)
            self.test("Revenue values are numeric and not null", self.test_revenue_types)
            self.test("Empty DB returns zeros", self.test_empty_db_zeros)
            self.test("Other top-level objects present", self.test_other_top_level_objects)
            
            # POSITIVE PATH TESTS (with test data)
            self.test("Single monthly session calculations", self.test_single_monthly_session)
            self.test("Two sessions (monthly + annual) calculations", self.test_two_sessions_mixed)
            
        finally:
            # Cleanup
            self.log("\n" + "="*60)
            self.log("CLEANUP")
            self.log("="*60)
            self.cleanup_test_sessions()
            
            # Verify cleanup
            paid_count = self.sessions_col.count_documents({"status": "paid"})
            self.log(f"✅ DB cleaned: {paid_count} paid sessions remaining (should be 0)")
            
        # Summary
        self.log("\n" + "="*60)
        self.log("TEST SUMMARY")
        self.log("="*60)
        self.log(f"Tests run: {self.tests_run}")
        self.log(f"Tests passed: {self.tests_passed}")
        self.log(f"Tests failed: {self.tests_run - self.tests_passed}")
        
        if self.tests_passed == self.tests_run:
            self.log("✅ ALL TESTS PASSED", "SUCCESS")
            return 0
        else:
            self.log(f"❌ {self.tests_run - self.tests_passed} TEST(S) FAILED", "ERROR")
            return 1

if __name__ == "__main__":
    tester = AdminStatsTest()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
