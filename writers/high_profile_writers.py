import sqlite3
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import time
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Create or connect to a SQLite database
def create_database():
    try:
        conn = sqlite3.connect('../dispensary.db')  # Creates or connects to the database file
        cursor = conn.cursor()

        # Create the "flower" table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flower (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Product TEXT,
                Brand TEXT,
                Potency REAL,
                Weight REAL,
                Price REAL,
                StrainType TEXT,
                Location TEXT
            )
        ''')

        # Commit the changes and close the connection
        conn.commit()
        print("Table created successfully or already exists.")
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        conn.close()

# Function to send PAGE_DOWN key presses to scroll and load more products
def send_page_down(driver, num_times=15):
    """ Simulate PAGE_DOWN key presses to scroll the page. """
    body = driver.find_element(By.TAG_NAME, 'body')
    for _ in range(num_times):
        body.send_keys(Keys.PAGE_DOWN)
        print("Sent PAGE_DOWN key...")
        time.sleep(1)  # Allow content to load after each key press

def clean_potency(potency_str):
    """ Remove the 'THC: ' prefix and '%' symbol, and convert to float for handling decimal percentages. """
    try:
        # Extract the numeric part of the potency, assuming the format is 'THC: 30.69%'
        potency_value = re.search(r"(\d+\.?\d*)", potency_str)
        return float(potency_value.group(1)) if potency_value else None
    except Exception as e:
        print(f"Error cleaning potency: {e}")
        return None

def clean_weight(weight_str):
    """ Extract the numeric part of the weight (assumes input like '1/8 oz -'). """
    weight_match = re.search(r'([\d/\.]+)', weight_str)
    if weight_match:
        return eval(weight_match.group(1))  # Convert fractions like '1/8' to decimal (3.5)
    return None

def clean_price(price_str):
    """ Remove the '$' and convert to float. """
    return float(price_str.replace('$', '').strip()) if price_str else None

def scrape_current_page(driver, location):
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    products = []

    # Find all product items based on the 'shopitem' class
    product_cards = soup.find_all('div', class_='shopitem')

    if not product_cards:
        print("No products found on the page.")
        return products

    print(f"Found {len(product_cards)} products on the page.")

    for product in product_cards:
        # Extract the product name
        name_tag = product.find('p', class_='shopitem__title')
        name = name_tag.text.strip() if name_tag else "No name found"
        print(f"Scraping product: {name}")

        # Extract the strain type (Indica, Sativa, Hybrid) from 'shopitem__strain'
        strain_type_tag = product.find('p', class_='shopitem__strain')
        strain_type = strain_type_tag.text.strip() if strain_type_tag else "Unknown"  # Default to 'Unknown' if missing

        # Extract the potency (THC percentage) from 'shopitem__strain-thc'
        potency_tag = product.find('p', class_='shopitem__strain-thc')
        potency = clean_potency(potency_tag.text.strip()) if potency_tag else None

        # Extract the brand information
        brand_tag = product.find('p', class_='shopitem__brand')
        brand = brand_tag.text.strip() if brand_tag else "Unknown"  # Set default to 'Unknown' if missing

        # Extract the price and weight combinations
        weight_price_container = product.find_all('div', class_='shopitem__listPrices-productVariants-item')

        if not weight_price_container:
            print(f"No weight-price options found for product: {name}")

        # Loop through each weight-price option and create a separate entry
        for option in weight_price_container:
            weight_tag = option.find('p', class_='shopitem__listPrices-productVariants-name')
            price_tag = option.find('p', class_='shopitem__listPrices-productVariants-price')

            if weight_tag and price_tag:
                weight = clean_weight(weight_tag.text.strip())
                price = clean_price(price_tag.text.strip())

                # Print debug info for each weight and price
                print(f"Found weight: {weight}, price: {price} for product: {name}")

                # Append each product weight and price as a separate entry
                products.append({
                    'name': name,
                    'strain_type': strain_type,  # Store the strain type here (Indica, Sativa, Hybrid)
                    'potency': potency,          # Store the THC percentage here
                    'brand': brand,
                    'weight': weight,
                    'price': price,
                    'location': location
                })

    print(f"Scraped {len(products)} products.")
    return products

# Updated function to handle pagination and scrape all pages
def scrape_all_pages(driver, location):
    all_products = []

    while True:
        send_page_down(driver, num_times=15)  # Scroll down enough to load products

        products = scrape_current_page(driver, location)
        all_products.extend(products)

        try:
            # Scroll to the next button to make sure it's in view
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="go to next page"]'))
            )

            # Scroll the next button into view
            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)

            # Add a small wait before clicking to ensure it’s clickable
            time.sleep(2)

            # Click the next button
            next_button.click()

            # Wait for the next page to load
            time.sleep(9)
        except Exception as e:
            print(f"Reached the last page or encountered an error: {e}")
            break

    return all_products

# Function to insert products into the SQLite database
def insert_into_database(products):
    try:
        conn = sqlite3.connect('../dispensary.db')
        cursor = conn.cursor()

        for product in products:
            cursor.execute('''
                INSERT INTO flower (Product, Brand, Potency, Weight, Price, StrainType, Location)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                product['name'],
                product['brand'],
                product['potency'],
                product['weight'],
                product['price'],
                product['strain_type'],
                product['location']
            ))

        conn.commit()
        print(f"Inserted {len(products)} products into the database.")
    except Exception as e:
        print(f"Error inserting into database: {e}")
    finally:
        conn.close()

# Function to handle age verification
def handle_age_verification(driver):
    try:
        # Wait until the 'Yes' button is clickable, using the unique ID 'age-gate-yes'
        yes_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, 'age-gate-yes'))
        )

        # Scroll the button into view just in case it's not visible
        driver.execute_script("arguments[0].scrollIntoView(true);", yes_button)

        # Click the 'Yes' button
        yes_button.click()
        print("Clicked 'Yes' on the age verification screen.")
        time.sleep(4)  # Allow time for the page to proceed after clicking

    except Exception as e:
        print(f"Error handling age verification: {e}. Proceeding with scrape.")

def scrape_data(urls_and_locations):
    driver_path = '../chromedriver.exe'  # Replace with your actual path to chromedriver
    service = Service(driver_path)

    # Initialize the Selenium WebDriver
    driver = webdriver.Chrome(service=service)

    for url, location in urls_and_locations:
        print(f"Scraping data for: {location}")

        driver.get(url)
        driver.implicitly_wait(15)

        handle_age_verification(driver)

        # Ensure scrolling happens to load all products
        send_page_down(driver, num_times=20)  # Scroll the page down to load products

        # Scrape the current page after scrolling
        all_products = scrape_current_page(driver, location)

        # If no products are found, output a message
        if not all_products:
            print("No products found after scrolling.")

        # Insert the products into the database
        insert_into_database(all_products)

    driver.quit()

if __name__ == '__main__':
    # List of URLs and their corresponding location names
    urls_and_locations = [
        ('https://highprofilecannabis.com/shop/cape-girardeau/flower', 'High Profile'),
    ]
    scrape_data(urls_and_locations)
