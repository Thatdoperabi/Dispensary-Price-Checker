from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import time

# Function to send PAGE_DOWN key presses to scroll and load more products
def send_page_down(driver, num_times=10):
    body = driver.find_element(By.TAG_NAME, 'body')
    for _ in range(num_times):
        body.send_keys(Keys.PAGE_DOWN)
        print("Sent PAGE_DOWN key...")
        time.sleep(2)  # Allow content to load after each key press

# Function to scrape the current page
def scrape_current_page(driver):
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
                    weight = weight_tag.text.strip()
                    price = price_tag.text.strip()

                    # Append the product with the specific weight and price
                    products.append({
                        'name': name,
                        'brand': brand,
                        'details': details,
                        'weight': weight,
                        'price': price
                    })
        else:
            # In case there are no multiple weights/prices, handle the default product entry
            weight_tag = product.find('span', class_='weight-tile__Label-otzu8j-5')
            price_tag = product.find('span', class_='weight-tile__PriceText-otzu8j-6')

            if weight_tag and price_tag:
                weight = weight_tag.text.strip()
                price = price_tag.text.strip()

                products.append({
                    'name': name,
                    'brand': brand,
                    'details': details,
                    'weight': weight,
                    'price': price
                })

    return products

# Function to handle pagination and scrape all pages
def scrape_all_pages(driver):
    all_products = []

    while True:
        # Scroll down to load all products on the current page
        send_page_down(driver, num_times=10)

        # Scrape the current page
        products = scrape_current_page(driver)
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
            time.sleep(3)

        except Exception as e:
            print(f"Reached the last page or encountered an error: {e}")
            break

    return all_products

# Main function to run the scraper
def scrape_data():
    # Path to your ChromeDriver
    driver_path = './chromedriver.exe'  # Replace with your actual path to chromedriver

    # Set up the Service for ChromeDriver
    service = Service(driver_path)

    # Set up Selenium WebDriver with the service
    driver = webdriver.Chrome(service=service)
    driver.get('https://greenlightdispensary.com/cape-girardeau-menu/?dtche%5Bcategory%5D=flower')  # Replace with the actual URL

    # Wait for the page to load completely
    driver.implicitly_wait(10)

    # Find the iframe element using the updated Selenium method
    iframe = driver.find_element(By.CSS_SELECTOR, 'iframe.dutchie--iframe')  # Use the correct selector for the iframe
    driver.switch_to.frame(iframe)  # Switch to the iframe

    # Scrape all pages
    all_products = scrape_all_pages(driver)

    # Close the browser after scraping
    driver.quit()

    return all_products

# Example usage
if __name__ == '__main__':
    product_list = scrape_data()
    for product in product_list:
        print(f"Product: {product['name']}, Brand: {product['brand']}, Details: {product['details']}, Weight: {product['weight']}, Price: {product['price']}")
