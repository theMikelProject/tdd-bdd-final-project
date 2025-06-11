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
Product Steps

Steps file for products.feature

For information on Waiting until elements are present in the HTML see:
    https://selenium-python.readthedocs.io/waits.html
"""
from behave import given
from service import app

HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_204_NO_CONTENT = 204


@given("the following products")
def step_impl(context):
    """Delete all Products and load the ones in context.table."""
    # Use Flask’s in-process test client – no live server needed
    context.client = app.test_client()

    # -----------------------------------------------------------------
    # 1) PURGE existing rows
    # -----------------------------------------------------------------
    resp = context.client.get("/products")
    assert resp.status_code == HTTP_200_OK
    for product in resp.get_json():
        resp = context.client.delete(f"/products/{product['id']}")
        assert resp.status_code == HTTP_204_NO_CONTENT

    # -----------------------------------------------------------------
    # 2) INSERT rows from the Background table
    # -----------------------------------------------------------------
    for row in context.table:
        payload = {
            "name":        row["name"],
            "description": row["description"],
            "price":       row["price"],
            "available":   row["available"].lower() in ["true", "1", "yes"],
            "category":    row["category"],
        }
        resp = context.client.post("/products", json=payload)
        assert resp.status_code == HTTP_201_CREATED, (
            f"Seed load failed: {resp.status_code} – {resp.data}"
        )