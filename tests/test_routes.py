"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"
HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI

        app.logger.setLevel(logging.CRITICAL)

        init_db(app)
        talisman.force_https = False

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()


    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################
    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_get_account_happy_path(self):
        """Test read account - happy path"""

        logging.debug ("init")
        account = self._create_accounts(1)[0]
        get_response = self.client.get(
            f"{BASE_URL}/{account.id}", content_type="application/json"
        )
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

        # Check the data is correct
        account_read = get_response.get_json()
        self.assertEqual(account_read["name"], account.name)
        self.assertEqual(account_read["email"], account.email)
        self.assertEqual(account_read["address"], account.address)
        self.assertEqual(account_read["phone_number"], account.phone_number)
        self.assertEqual(account_read["date_joined"], str(account.date_joined))     

        logging.debug ("end")   

    def test_get_account_no_account(self):
        """Test read account - error no account"""

        logging.debug ("init")

        get_response = self.client.get(
            f"{BASE_URL}/100", content_type="application/json"
        )
        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)

        logging.debug ("end")


    def test_update_account_happy_path(self):
        """Test update account - happy path"""

        logging.debug ("init")
        account = self._create_accounts(1)[0]

        get_response = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

        account_found = get_response.get_json()
        new_name = f"{account.name}mod"
        account_found["name"] = new_name
        update_account_response = self.client.put(f"{BASE_URL}/{account.id}", json=account_found)
        self.assertEqual(update_account_response.status_code, status.HTTP_200_OK)

        logging.debug ("end")

    def test_update_account_no_account(self):
        """Test update account - error - no account"""

        logging.debug ("init")
        update_account_response = self.client.put(f"{BASE_URL}/100", json={})
        self.assertEqual(update_account_response.status_code, status.HTTP_404_NOT_FOUND)

        logging.debug ("end")        

    def test_list_accounts_happy_path(self):
        """Test list accounts - happy path"""

        logging.debug ("init")
        accounts = self._create_accounts(5)

        list_accounts_response = self.client.get(f"{BASE_URL}")

        logging.info(f"list_accounts_response: {list_accounts_response}")

        self.assertEqual(list_accounts_response.status_code, status.HTTP_200_OK)

        data = list_accounts_response.get_json()["data"]
        self.assertEqual(len(data),5)

        logging.debug ("end")        


    def test_delete_account_happy_path(self):
        """Test to delete a account from the database - happy path"""

        logging.debug ("init")
        num_accounts=5
        account = self._create_accounts(num_accounts)[0]

        response_delete = self.client.delete(f"{BASE_URL}/{account.id}")

        # DEBUG
        logging.debug(f"response_delete: {response_delete}")

        self.assertEqual(response_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response_delete.data), 0)
        list_accounts_response = self.client.get(f"{BASE_URL}")
        data = list_accounts_response.get_json()["data"]

        self.assertEqual(len(data), num_accounts-1)


        logging.debug ("end")

    def test_root_https(self):
        """test root with htpps - happy path"""
        
        response = self.client.get("/", environ_overrides=HTTPS_ENVIRON)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("Content-Security-Policy"), "default-src \'self\'; object-src \'none\'")
        self.assertEqual(response.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        
        

        