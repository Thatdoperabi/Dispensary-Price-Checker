from writers import  dutchie_writer, elevate_writer, green_light_writer, high_profile_writers


# Function to run both scrapers
def run_scrapers():
    print("Running Greenlight scraper...")
    green_light_writer.truncate_table()  # Optional: truncate before running each scraper
    green_light_writer.scrape_data('https://greenlightdispensary.com/cape-girardeau-menu/?dtche%5Bcategory%5D=flower', 'Greenlight')

    print("Running Dutchie scrapers...")
    # List of URLs and their corresponding location names for CodesWriter
    urls_and_locations = [
        ('https://codesdispensary.com/location/cape-girardeau-mo/?dtche%5Bcategory%5D=flower', 'CODES'),
        ('https://gooddayfarmdispensary.com/cape-girardeau-menu/?dtche%5Bcategory%5D=flower', 'Good Day Farm'),
    ]
    dutchie_writer.scrape_data(urls_and_locations)

    print("Running High Profile scraper...")
    urls_and_locations = [
        ('https://highprofilecannabis.com/shop/cape-girardeau/flower', 'High Profile'),
    ]
    high_profile_writers.scrape_data(urls_and_locations)


    print("Running Elevate scrapers...")
    # List of URLs and their corresponding location names for CodesWriter
    urls_and_locations = [
        ('https://keycannabis.com/shop/cape-girardeau-mo/?dtche%5Bcategory%5D=flower', 'Elevate')
    ]
    elevate_writer.scrape_data(urls_and_locations)

if __name__ == '__main__':
    run_scrapers()
