import sqlite3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import time
import re

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
                Potency REAL,  -- Changed to REAL to handle decimal percentages
                Weight REAL,   -- Changed to REAL (to handle fractional numbers like 1/8)
                Price REAL,    -- Changed to REAL to handle numeric prices
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

# Function to truncate the flower table (remove all rows)
def truncate_table():
    try:
        conn = sqlite3.connect('../dispensary.db')
        cursor = conn.cursor()

        # Delete all rows from the flower table
        cursor.execute('DELETE FROM flower')
        conn.commit()
        print("Flower table truncated successfully.")
    except Exception as e:
        print(f"Error truncating table: {e}")
    finally:
        conn.close()

# Function to send PAGE_DOWN key presses to scroll and load more products
def send_page_down(driver, num_times=15):
    """ Simulate PAGE_DOWN key presses to scroll the page. """
    body = driver.find_element(By.TAG_NAME, 'body')
    for _ in range(num_times):
        body.send_keys(Keys.PAGE_DOWN)
        print("Sent PAGE_DOWN key...")
        time.sleep(2)  # Allow content to load after each key press

# Function to clean and convert fields
def clean_potency(potency_str):
    """ Remove the '%' and convert to float for handling decimal percentages. """
    return float(potency_str.replace('%', '').strip()) if potency_str else None

def clean_weight(weight_str):
    """ Extract the numeric part of the weight (assumes input like '1/8 oz -'). """
    weight_match = re.search(r'([\d/\.]+)', weight_str)
    if weight_match:
        # Handle fractional weights (e.g., 1/8 becomes 3.5)
        return eval(weight_match.group(1))  # Convert fractions like '1/8' to decimal (3.5)
    return None

def clean_price(price_str):
    """ Remove the '$' and convert to float. """
    return float(price_str.replace('$', '').strip()) if price_str else None

# Function to scrape the current page
def scrape_current_page(driver, location):
    # Get the page source after scrolling
    html = driver.page_source

    # Use BeautifulSoup to parse the HTML
    soup = BeautifulSoup(html, 'html.parser')

    products = []

    # Find all product items using the 'data-testid' attribute
    product_cards = soup.find_all('div', {'data-testid': 'product-list-item'})

    for product in product_cards:
        # Extract the product name
        name_tag = product.find('span', class_='mobile-product-list-item__ProductName-zxgt1n-6')
        name = name_tag.text.strip() if name_tag else "No name found"

        # Extract the brand
        brand_tag = product.find('span', class_='mobile-product-list-item__Brand-zxgt1n-3')
        brand = brand_tag.text.strip() if brand_tag else "No brand found"

        # Extract the details (such as strain type, THC percentage)
        details_tag = product.find('div', class_='mobile-product-list-item__DetailsContainer-zxgt1n-1')
        details = details_tag.text.strip() if details_tag else "No details found"

        # Extract strain type and potency from details
        strain_type = "Unknown"
        potency = None

        # Check if details contain the strain type (e.g., "Indica-Hybrid")
        if "•" in details:
            strain_type = details.split("•")[0].strip()  # Extract strain type
            potency_match = re.search(r'THC:\s*([0-9.]+%)', details)
            if potency_match:
                potency = clean_potency(potency_match.group(1).strip())  # Clean and convert THC potency

        # Check for multiple weight/price options
        weight_price_container = product.find('div', class_='mobile-product-list-item__MultipleOptionsContainer-zxgt1n-2')

        # If multiple weight/price options exist
        if weight_price_container:
            weight_price_options = weight_price_container.find_all('button')

            for option in weight_price_options:
                # Only process buttons with both weight and price spans
                weight_tag = option.find('span', class_='weight-tile__Label-otzu8j-5')
                price_tag = option.find('span', class_='weight-tile__PriceText-otzu8j-6')

                if weight_tag and price_tag:
                    weight = clean_weight(weight_tag.text.strip())
                    price = clean_price(price_tag.text.strip())

                    # Append the product with the specific weight and price
                    products.append({
                        'name': name,
                        'brand': brand,
                        'strain_type': strain_type,
                        'potency': potency,
                        'weight': weight,
                        'price': price,
                        'location': location  # Use the parameterized location
                    })
        else:
            # In case there are no multiple weights/prices, handle the default product entry
            weight_tag = product.find('span', class_='weight-tile__Label-otzu8j-5')
            price_tag = product.find('span', class_='weight-tile__PriceText-otzu8j-6')

            if weight_tag and price_tag:
                weight = clean_weight(weight_tag.text.strip())
                price = clean_price(price_tag.text.strip())

                products.append({
                    'name': name,
                    'brand': brand,
                    'strain_type': strain_type,
                    'potency': potency,
                    'weight': weight,
                    'price': price,
                    'location': location  # Use the parameterized location
                })

    return products

# Function to handle pagination and scrape all pages
def scrape_all_pages(driver, location):
    all_products = []

    while True:
        # Scroll down to load all products on the current page
        send_page_down(driver, num_times=10)

        # Scrape the current page
        products = scrape_current_page(driver, location)
        all_products.extend(products)

        # Find the "Next" button
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="go to next page"]')

            # Check if the "Next" button is disabled (indicating the last page)
            if not next_button.is_enabled():
                break

            # Click the "Next" button to go to the next page
            print("Clicking the 'Next' button...")
            next_button.click()

            # Wait for the next page to load
            time.sleep(5)

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

        # Commit the transaction and close the connection
        conn.commit()
        print(f"Inserted {len(products)} products into the database.")
    except Exception as e:
        print(f"Error inserting into database: {e}")
    finally:
        conn.close()

def handle_age_verification(driver):
    try:
        # Check if the "Yes" button exists (age verification screen present)
        yes_button = driver.find_element(By.XPATH, '//button[contains(text(), "Yes")]')
        yes_button.click()
        print("Clicked 'Yes' on the age verification screen.")
        time.sleep(3)  # Give it some time to process
    except Exception as e:
        # If the "Yes" button is not found, assume no age verification needed and continue
        print("No age verification found, proceeding with scrape.")

# Main function to run the scraper for a given dispensary
def scrape_data(url, location):
    # Path to your ChromeDriver
    driver_path = '../chromedriver.exe'  # Replace with your actual path to chromedriver

    # Set up the Service for ChromeDriver
    service = Service(driver_path)

    # Set up Selenium WebDriver with the service
    driver = webdriver.Chrome(service=service)
    driver.get(url)  # Use the parameterized URL

    # Wait for the page to load completely
    driver.implicitly_wait(15)

    # Handle age verification if present
    handle_age_verification(driver)

    # Find the iframe element using the updated Selenium method
    iframe = driver.find_element(By.CSS_SELECTOR, 'iframe.dutchie--iframe')  # Use the correct selector for the iframe
    driver.switch_to.frame(iframe)  # Switch to the iframe

    # Scrape all pages
    all_products = scrape_all_pages(driver, location)

    # Insert all products into the database
    insert_into_database(all_products)

    # Close the browser after scraping
    driver.quit()

# Example usage for Greenlight and CODES dispensaries
if __name__ == '__main__':
    # Truncate the table before inserting new records
    truncate_table()

    # Scrape Greenlight
    scrape_data('https://greenlightdispensary.com/cape-girardeau-menu/?dtche%5Bcategory%5D=flower', 'Greenlight')

    # Scrape CODES Dispensary

