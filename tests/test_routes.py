######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from service import app
from service.common import status
from service.models import db, init_db, Product
from tests.factories import ProductFactory

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        #
        # Uncomment this code once READ is implemented
        #

        # # Check that the location header was correct
        # response = self.client.get(location)
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # new_product = response.get_json()
        # self.assertEqual(new_product["name"], test_product.name)
        # self.assertEqual(new_product["description"], test_product.description)
        # self.assertEqual(Decimal(new_product["price"]), test_product.price)
        # self.assertEqual(new_product["available"], test_product.available)
        # self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    #
    # ADD YOUR TEST CASES HERE
    #
        # ----------------------------------------------------------
    # TEST READ
    # ----------------------------------------------------------
    def test_get_product(self):
        """It should Read a single Product"""
        test_product = self._create_products(1)[0]

        resp = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.get_json()
        self.assertEqual(data["name"], test_product.name)
        self.assertEqual(data["description"], test_product.description)

    def test_get_product_not_found(self):
        """It should return 404 when Product is missing"""
        resp = self.client.get(f"{BASE_URL}/0")          # id 0 will never exist
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ----------------------------------------------------------
    # TEST UPDATE
    # ----------------------------------------------------------
    def test_update_product(self):
        """It should Update an existing Product"""
        test_product = self._create_products(1)[0]

        changed = test_product.serialize()
        changed["description"] = "updated description"

        resp = self.client.put(
            f"{BASE_URL}/{test_product.id}", json=changed
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["description"], "updated description")

    def test_update_product_not_found(self):
        """It should return 404 on update of missing Product"""
        fake_product = ProductFactory().serialize()
        resp = self.client.put(f"{BASE_URL}/0", json=fake_product)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ----------------------------------------------------------
    # TEST DELETE
    # ----------------------------------------------------------
    def test_delete_product(self):
        """It should Delete a Product"""
        test_product = self._create_products(1)[0]
        resp = self.client.delete(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        # verify it really disappeared
        resp = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_product_not_found(self):
        """It should return 404 on delete of missing Product"""
        resp = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ----------------------------------------------------------
    # TEST LIST & QUERIES
    # ----------------------------------------------------------
    def test_list_all_products(self):
        """It should List all Products (no filters)"""
        self._create_products(3)
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 3)

    def test_query_product_by_name(self):
        """It should Filter by name"""
        products = self._create_products(5)
        name = products[0].name
        expected_count = sum(1 for p in products if p.name == name)

        resp = self.client.get(f"{BASE_URL}?name={name}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), expected_count)
        for item in data:
            self.assertEqual(item["name"], name)

    def test_query_product_by_category(self):
        """It should Filter by category"""
        products = self._create_products(5)
        category = products[0].category.name
        expected_count = sum(1 for p in products if p.category.name == category)

        resp = self.client.get(f"{BASE_URL}?category={category}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), expected_count)
        for item in data:
            self.assertEqual(item["category"], category)

    def test_query_product_by_availability(self):
        """It should Filter by availability"""
        products = self._create_products(6)
        available = products[0].available
        expected_count = sum(1 for p in products if p.available == available)

        resp = self.client.get(f"{BASE_URL}?available={str(available).lower()}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), expected_count)
        for item in data:
            self.assertEqual(item["available"], available)


    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)
