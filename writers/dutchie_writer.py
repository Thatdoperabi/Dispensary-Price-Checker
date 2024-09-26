import sqlite3
from selenium import webdriver
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

# Function to clean and convert fields
def clean_potency(potency_str):
    """ Remove the '%' and convert to float for handling decimal percentages. """
    return float(potency_str.replace('%', '').strip()) if potency_str else None

def clean_weight(weight_str):
    """ Extract the numeric part of the weight (assumes input like '1/8 oz -'). """
    weight_match = re.search(r'([\d/\.]+)', weight_str)
    if weight_match:
        return eval(weight_match.group(1))  # Convert fractions like '1/8' to decimal (3.5)
    return None

def clean_price(price_str):
    """ Remove the '$' and convert to float. """
    return float(price_str.replace('$', '').strip()) if price_str else None

# Function to scrape the current page
def scrape_current_page(driver, location):
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    products = []

    product_cards = soup.find_all('div', {'data-testid': 'product-list-item'})

    for product in product_cards:
        name_tag = product.find('span', class_='mobile-product-list-item__ProductName-zxgt1n-6')
        name = name_tag.text.strip() if name_tag else "No name found"

        brand_tag = product.find('span', class_='mobile-product-list-item__Brand-zxgt1n-3')
        brand = brand_tag.text.strip() if brand_tag else "No brand found"

        details_tag = product.find('div', class_='mobile-product-list-item__DetailsContainer-zxgt1n-1')
        details = details_tag.text.strip() if details_tag else "No details found"

        strain_type = "Unknown"
        potency = None

        if "•" in details:
            strain_type = details.split("•")[0].strip()
            potency_match = re.search(r'THC:\s*([0-9.]+%)', details)
            if potency_match:
                potency = clean_potency(potency_match.group(1).strip())

        weight_price_container = product.find('div', class_='mobile-product-list-item__MultipleOptionsContainer-zxgt1n-2')

        if weight_price_container:
            weight_price_options = weight_price_container.find_all('button')

            for option in weight_price_options:
                weight_tag = option.find('span', class_='weight-tile__Label-otzu8j-5')
                price_tag = option.find('span', class_='weight-tile__PriceText-otzu8j-6')

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
                        'location': location
                    })
        else:
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
                    'location': location
                })

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
        yes_button = driver.find_element(By.XPATH, '//button[contains(text(), "Yes")]')
        yes_button.click()
        print("Clicked 'Yes' on the age verification screen.")
        time.sleep(4)
    except Exception as e:
        print("No age verification found, proceeding with scrape.")

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

        iframe = driver.find_element(By.CSS_SELECTOR, 'iframe.dutchie--iframe')
        driver.switch_to.frame(iframe)

        all_products = scrape_all_pages(driver, location)

        insert_into_database(all_products)

    driver.quit()

if __name__ == '__main__':
    # List of URLs and their corresponding location names
    urls_and_locations = [
        ('https://codesdispensary.com/location/cape-girardeau-mo/?dtche%5Bcategory%5D=flower', 'CODES'),
        ('https://gooddayfarmdispensary.com/cape-girardeau-menu/?dtche%5Bcategory%5D=flower', 'Good Day Farm'),
    ]
    scrape_data(urls_and_locations)
