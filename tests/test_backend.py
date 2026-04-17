import requests
import pytest

BASE_URL = "http://localhost:5000/api"

def test_api_products_status():
    """
    Verify that the Products API is reachable and returns 200 OK.
    """
    response = requests.get(f"{BASE_URL}/products")
    assert response.status_code == 200

def test_api_products_structure():
    """
    Check if the response contains the expected 'products' and 'pagination' keys.
    """
    response = requests.get(f"{BASE_URL}/products")
    data = response.json()
    assert "products" in data
    assert "pagination" in data
    assert isinstance(data["products"], list)

def test_api_stats():
    """
    Ensure the stats API returns the total count and the new 'lastUpdated' field.
    """
    response = requests.get(f"{BASE_URL}/stats")
    data = response.json()
    assert response.status_code == 200
    assert "totalProducts" in data
    assert "lastUpdated" in data
    assert "priceRange" in data

def test_screen_size_filter():
    """
    Test if the screen size filter works for '32_and_below'.
    """
    response = requests.get(f"{BASE_URL}/products?screen_size=32_and_below")
    data = response.json()
    assert response.status_code == 200
    
    # If products exist, check if their names actually mention 32 or smaller
    if len(data["products"]) > 0:
        for product in data["products"]:
            # Basic check: name should usually have cm/inch info
            name = product["name"].lower()
            # If the extraction worked, the number should be <= 32
            assert product.get("screen_size_num") is not None
            assert product["screen_size_num"] <= 32

def test_discount_filter():
    """
    Test if the Deal Finder works for '25% or more'.
    """
    response = requests.get(f"{BASE_URL}/products?discount=25")
    data = response.json()
    assert response.status_code == 200
    
    if len(data["products"]) > 0:
        for product in data["products"]:
            # Ensure the extracted discount is actually 25 or more
            assert product.get("discount_num") >= 25
