

import csv
import json
import time
import re
from datetime import datetime
import logging
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OLXCarCoverScraper:
    def __init__(self):
        self.base_url = "https://www.olx.in"
        self.search_url = "https://www.olx.in/items/q-car-cover"
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome WebDriver setup successful")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up WebDriver: {e}")
            return False
    
    def extract_price(self, price_text):
        """Extract numeric price from price text"""
        if not price_text:
            return None
        
        
        price_clean = re.sub(r'[₹,\s]', '', price_text.strip())
        
        
        numbers = re.findall(r'\d+', price_clean)
        if numbers:
            return ''.join(numbers)
        return None
    
    def wait_for_listings(self, timeout=15):
        """Wait for listings to load on the page"""
        try:
            
            selectors = [
                "[data-aut-id='itemBox']",
                ".EIR5N",  
                "[data-aut-id='itemTitle']",
                ".rui-38N2G",
                ".rui-1ykdW",
                "li[data-aut-id='itemBox']"
            ]
            
            for selector in selectors:
                try:
                    WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"Listings found using selector: {selector}")
                    return selector
                except TimeoutException:
                    continue
            
            logger.warning("No listings found with any selector")
            return None
            
        except Exception as e:
            logger.error(f"Error waiting for listings: {e}")
            return None
    
    def extract_listing_data(self, listing_element):
        """Extract data from a single listing element"""
        try:
            data = {}
            
            
            title_selectors = [
                "[data-aut-id='itemTitle']",
                "h2", "h3", 
                ".rui-35953",
                "a[href*='/item/']"
            ]
            
            title = None
            for selector in title_selectors:
                try:
                    title_elem = listing_element.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip()
                    if title:
                        break
                except NoSuchElementException:
                    continue
            
            data['title'] = title or 'N/A'
            
            
            price_selectors = [
                "[data-aut-id='itemPrice']",
                ".rui-ANJaG",
                "span[class*='price']",
                "span[class*='amount']"
            ]
            
            price = None
            for selector in price_selectors:
                try:
                    price_elem = listing_element.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_elem.text.strip()
                    price = self.extract_price(price_text)
                    if price:
                        break
                except NoSuchElementException:
                    continue
            
            data['price'] = price or 'N/A'
            
            
            location_selectors = [
                "[data-aut-id='item-location']",
                ".rui-1Wks1",
                "span[class*='location']",
                "span[class*='place']"
            ]
            
            location = None
            for selector in location_selectors:
                try:
                    location_elem = listing_element.find_element(By.CSS_SELECTOR, selector)
                    location = location_elem.text.strip()
                    if location:
                        break
                except NoSuchElementException:
                    continue
            
            data['location'] = location or 'N/A'
            
            date_selectors = [
                "[data-aut-id='item-date']",
                "span[class*='date']",
                "span[class*='time']"
            ]
            
            date = None
            for selector in date_selectors:
                try:
                    date_elem = listing_element.find_element(By.CSS_SELECTOR, selector)
                    date = date_elem.text.strip()
                    if date:
                        break
                except NoSuchElementException:
                    continue
            
            data['date'] = date or 'N/A'
            
            # Try to get URL
            url = None
            try:
                link_elem = listing_element.find_element(By.CSS_SELECTOR, "a[href*='/item/']")
                url = link_elem.get_attribute('href')
            except NoSuchElementException:
                url = 'N/A'
            
            data['url'] = url
            
            return data
            
        except Exception as e:
            logger.warning(f"Error extracting listing data: {e}")
            return None
    
    def scroll_to_load_more(self):
        """Scroll down to load more listings"""
        try:
            
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            time.sleep(3)
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            return new_height > last_height
            
        except Exception as e:
            logger.error(f"Error scrolling: {e}")
            return False
    
    def scrape_listings(self):
        """Scrape car cover listings from OLX"""
        if not self.setup_driver():
            return []
        
        all_listings = []
        
        try:
            logger.info(f"Navigating to: {self.search_url}")
            self.driver.get(self.search_url)
            
            
            time.sleep(5)
            
            listing_selector = self.wait_for_listings()
            
            if not listing_selector:
                logger.info("Trying alternative content extraction...")
                page_source = self.driver.page_source
                
                with open(f"page_source_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html", 'w', encoding='utf-8') as f:
                    f.write(page_source)
                
                listings = self.extract_from_page_source(page_source)
                return listings
            
            scroll_attempts = 0
            max_scrolls = 3
            
            while scroll_attempts < max_scrolls:
                if not self.scroll_to_load_more():
                    break
                scroll_attempts += 1
                logger.info(f"Scrolled {scroll_attempts}/{max_scrolls} times")
            
            listing_elements = self.driver.find_elements(By.CSS_SELECTOR, listing_selector)
            logger.info(f"Found {len(listing_elements)} listing elements")
            
            for i, element in enumerate(listing_elements):
                try:
                    listing_data = self.extract_listing_data(element)
                    if listing_data and self.is_car_cover_listing(listing_data):
                        all_listings.append(listing_data)
                        logger.info(f"Extracted listing {i+1}: {listing_data['title'][:50]}...")
                        
                except Exception as e:
                    logger.warning(f"Error processing listing {i+1}: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(all_listings)} car cover listings")
            
        except Exception as e:
            logger.error(f"Error scraping listings: {e}")
        
        finally:
            if self.driver:
                self.driver.quit()
        
        return all_listings
    
    def extract_from_page_source(self, page_source):
        """Extract listings from page source using regex patterns"""
        listings = []
        
        try:
            price_pattern = r'₹\s*[\d,]+(?:\s*[^<\n]*(?:car\s*cover|seat\s*cover|body\s*cover)[^<\n]*)?'
            matches = re.finditer(price_pattern, page_source, re.IGNORECASE)
            
            for match in matches:
                context_start = max(0, match.start() - 200)
                context_end = min(len(page_source), match.end() + 200)
                context = page_source[context_start:context_end]
                
                title_match = re.search(r'(?:car\s*cover|seat\s*cover|body\s*cover|wheel\s*cover)[^<>]*', context, re.IGNORECASE)
                if title_match:
                    listing = {
                        'title': title_match.group().strip(),
                        'price': self.extract_price(match.group()),
                        'location': 'N/A',
                        'date': 'N/A',
                        'url': 'N/A'
                    }
                    listings.append(listing)
            
        except Exception as e:
            logger.error(f"Error extracting from page source: {e}")
        
        return listings
    
    def is_car_cover_listing(self, listing_data):
        """Check if listing is actually for car covers"""
        title = listing_data.get('title', '').lower()
        
        car_cover_keywords = ['car cover', 'body cover', 'seat cover', 'wheel cover', 'brake cover', 'car mat']
        
        exclude_keywords = ['bhk', 'flat', 'apartment', 'parking', 'rent', 'sale', 'sqft', 'bathroom', 'bedroom']
        
        has_car_cover = any(keyword in title for keyword in car_cover_keywords)
        has_property = any(keyword in title for keyword in exclude_keywords)
        
        return has_car_cover and not has_property
    
    def save_to_csv(self, listings, filename):
        """Save listings to CSV file"""
        if not listings:
            logger.warning("No listings to save")
            return False
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['title', 'price', 'location', 'date', 'url']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for listing in listings:
                    writer.writerow({
                        'title': listing.get('title', 'N/A'),
                        'price': listing.get('price', 'N/A'),
                        'location': listing.get('location', 'N/A'),
                        'date': listing.get('date', 'N/A'),
                        'url': listing.get('url', 'N/A')
                    })
                    
            logger.info(f"Saved {len(listings)} listings to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            return False
    
    def save_to_json(self, listings, filename):
        """Save listings to JSON file"""
        if not listings:
            logger.warning("No listings to save")
            return False
        
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'search_query': 'car cover',
                'total_listings': len(listings),
                'listings': listings
            }
            
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved {len(listings)} listings to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
            return False

def main():
    """Main function"""
    print("OLX Car Cover Scraper")
    print("=" * 50)
    
    scraper = OLXCarCoverScraper()
    
    print("Starting scraping process...")
    listings = scraper.scrape_listings()
    
    if listings:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        csv_filename = f"olx_car_covers_{timestamp}.csv"
        json_filename = f"olx_car_covers_{timestamp}.json"
        
        csv_saved = scraper.save_to_csv(listings, csv_filename)
        json_saved = scraper.save_to_json(listings, json_filename)
        
        print(f"\nScraping completed successfully!")
        print(f"Found {len(listings)} car cover listings")
        
        if csv_saved or json_saved:
            print(f"\nData saved to:")
            if csv_saved:
                print(f"- {csv_filename}")
            if json_saved:
                print(f"- {json_filename}")
        
        print("\nSample listings:")
        print("-" * 50)
        for i, listing in enumerate(listings[:5], 1):
            print(f"\n{i}. {listing.get('title', 'N/A')}")
            print(f"   Price: ₹{listing.get('price', 'N/A')}")
            print(f"   Location: {listing.get('location', 'N/A')}")
            print(f"   Date: {listing.get('date', 'N/A')}")
            if listing.get('url') != 'N/A':
                print(f"   URL: {listing.get('url')}")
                
        if len(listings) > 5:
            print(f"\n... and {len(listings) - 5} more listings")
            
    else:
        print("\nNo car cover listings found.")
        print("This could be due to:")
        print("1. OLX website structure changes")
        print("2. Network connectivity issues")
        print("3. Anti-bot measures")
        print("\nCheck the generated page_source_*.html file for debugging.")

if __name__ == "__main__":
    main()