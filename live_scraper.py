import requests
from bs4 import BeautifulSoup
import time
import logging
import re
from datetime import datetime
import io
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import json
import base64
from PIL import Image
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

logger = logging.getLogger(__name__)

# Check Tesseract availability after logger is defined
if not TESSERACT_AVAILABLE:
    logger.warning("Tesseract OCR not available. CAPTCHA solving will be limited.")

class DelhiHighCourtLiveScraper:
    """Live scraper for Delhi High Court website with real data and PDF downloads"""
    
    def __init__(self, headless=False, show_browser=True):
        self.base_url = "https://delhihighcourt.nic.in"
        self.case_status_url = "https://delhihighcourt.nic.in/app/get-case-type-status"
        self.headless = headless
        self.show_browser = show_browser
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.driver = None
        self.driver_setup_time = None
        self.max_driver_age = 300  # 5 minutes before recreating driver
        
        # Load form structure from JSON
        self.form_structure = self.load_form_structure()
    
    def load_form_structure(self):
        """Load form structure from JSON file"""
        try:
            import json
            with open(r"c:\Users\khyal\OneDrive\Desktop\Court_Web_App\court_form_structure.json", "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load form structure: {str(e)}")
            return {}
    
    def get_case_types(self):
        """Get list of available case types"""
        if self.form_structure and 'case_type' in self.form_structure:
            return self.form_structure['case_type'].get('options', [])
        return []
    
    def get_years(self):
        """Get list of available years"""
        if self.form_structure and 'year' in self.form_structure:
            return self.form_structure['year'].get('options', [])
        return []
    
    def setup_driver(self):
        """Setup Chrome WebDriver with options"""
        try:
            chrome_options = Options()
            
            # Find Chrome executable
            import os
            possible_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME'))
            ]
            
            chrome_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
            
            if chrome_path:
                chrome_options.binary_location = chrome_path
                logger.info(f"Using Chrome at: {chrome_path}")
            
            # Browser visibility control
            if self.headless or not self.show_browser:
                chrome_options.add_argument('--headless')
                logger.info("Running browser in headless mode (invisible)")
            else:
                logger.info("Running browser in visible mode (you will see the browser window)")
            
            # Performance optimizations
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-features=TranslateUI')
            chrome_options.add_argument('--disable-background-networking')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--disable-client-side-phishing-detection')
            chrome_options.add_argument('--disable-hang-monitor')
            chrome_options.add_argument('--disable-prompt-on-repost')
            chrome_options.add_argument('--disable-domain-reliability')
            chrome_options.add_argument('--disable-component-update')
            chrome_options.add_argument('--disable-desktop-notifications')
            chrome_options.add_argument('--aggressive-cache-discard')
            chrome_options.add_argument('--memory-pressure-off')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Set page load strategy for faster loading
            chrome_options.page_load_strategy = 'eager'
            
            # Try direct Chrome start first (faster)
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                logger.info("Chrome WebDriver setup successful (direct)")
            except Exception as e1:
                logger.warning(f"Direct Chrome start failed: {str(e1)}, trying webdriver-manager...")
                # Fallback to webdriver-manager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("Chrome WebDriver setup successful (webdriver-manager)")
            
            return True
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {str(e)}")
            return False
    
    def solve_captcha(self, captcha_element):
        """Attempt to solve CAPTCHA using OCR - optimized for digit CAPTCHAs"""
        try:
            if not TESSERACT_AVAILABLE:
                logger.warning("Tesseract OCR not available. Cannot solve CAPTCHA automatically.")
                return None
                
            # Take screenshot of CAPTCHA
            captcha_screenshot = captcha_element.screenshot_as_png
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(captcha_screenshot))
            
            # Preprocess image for better OCR (optimized for digits)
            image = image.convert('L')  # Convert to grayscale
            
            # Enhance contrast and remove noise
            from PIL import ImageEnhance, ImageFilter
            
            # Increase contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Apply slight blur to reduce noise
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # Resize image for better OCR (make it larger)
            width, height = image.size
            image = image.resize((width * 3, height * 3), Image.LANCZOS)
            
            # Use OCR to read CAPTCHA - optimized for digits only
            captcha_text = pytesseract.image_to_string(
                image, 
                config='--psm 8 -c tessedit_char_whitelist=0123456789'
            )
            captcha_text = captcha_text.strip()
            
            # Clean up the result - keep only digits
            captcha_text = ''.join(filter(str.isdigit, captcha_text))
            
            logger.info(f"CAPTCHA OCR result: '{captcha_text}' (length: {len(captcha_text)})")
            
            # Return only if we got a reasonable result (typically 4-6 digits)
            if len(captcha_text) >= 3 and len(captcha_text) <= 8:
                return captcha_text
            else:
                logger.warning(f"CAPTCHA result seems invalid: '{captcha_text}'")
                return None
            
        except Exception as e:
            logger.error(f"CAPTCHA solving failed: {str(e)}")
            return None
    
    def scrape_case_data(self, case_type, case_number, filing_year):
        """
        Scrape live case data from Delhi High Court website
        """
        try:
            logger.info(f"Starting live scraping for: {case_type} {case_number}/{filing_year}")
            
            if not self.setup_driver():
                logger.error("Failed to setup WebDriver")
                return None
            
            # Navigate to case status page
            self.driver.get(self.case_status_url)
            time.sleep(2)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "case_type"))
            )
            
            # Fill case details with correct field names
            case_type_select = Select(self.driver.find_element(By.ID, "case_type"))
            case_type_select.select_by_value(case_type)
            logger.info(f"Selected case type: {case_type}")
            
            case_number_input = self.driver.find_element(By.ID, "case_number")
            case_number_input.clear()
            case_number_input.send_keys(case_number)
            logger.info(f"Entered case number: {case_number}")
            
            filing_year_select = Select(self.driver.find_element(By.ID, "case_year"))
            filing_year_select.select_by_value(filing_year)
            logger.info(f"Selected year: {filing_year}")
            
            # Handle CAPTCHA if present
            captcha_attempts = 3
            for attempt in range(captcha_attempts):
                try:
                    # Look for different types of CAPTCHA
                    captcha_solved = False
                    
                    # Method 1: Look for text-based CAPTCHA (digits/text that can be copied)
                    try:
                        # Look for CAPTCHA text elements
                        captcha_text_selectors = [
                            "span[id*='captcha']",
                            "div[id*='captcha']", 
                            "label[for*='captcha']",
                            "span.captcha",
                            "div.captcha-text"
                        ]
                        
                        captcha_text = None
                        for selector in captcha_text_selectors:
                            try:
                                captcha_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                                captcha_text = captcha_element.text.strip()
                                if captcha_text and len(captcha_text) >= 3:
                                    logger.info(f"Found text-based CAPTCHA: {captcha_text}")
                                    break
                            except:
                                continue
                        
                        if captcha_text:
                            # Find CAPTCHA input field
                            captcha_input_selectors = [
                                "input[name*='captcha']",
                                "input[id*='captcha']",
                                "input[placeholder*='captcha']"
                            ]
                            
                            captcha_input = None
                            for selector in captcha_input_selectors:
                                try:
                                    captcha_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                                    break
                                except:
                                    continue
                            
                            if captcha_input:
                                captcha_input.clear()
                                captcha_input.send_keys(captcha_text)
                                logger.info(f"Entered text CAPTCHA: {captcha_text}")
                                captcha_solved = True
                    except Exception as e:
                        logger.debug(f"Text CAPTCHA method failed: {str(e)}")
                    
                    # Method 2: Look for image-based CAPTCHA (fallback)
                    if not captcha_solved:
                        try:
                            captcha_img = self.driver.find_element(By.XPATH, "//img[contains(@src, 'captcha') or contains(@src, 'Captcha')]")
                            captcha_input_selectors = [
                                "input[name*='captcha']",
                                "input[id*='captcha']",
                                "input[placeholder*='captcha']"
                            ]
                            
                            captcha_input = None
                            for selector in captcha_input_selectors:
                                try:
                                    captcha_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                                    break
                                except:
                                    continue
                            
                            if captcha_input:
                                # Solve image CAPTCHA
                                captcha_solution = self.solve_captcha(captcha_img)
                                if captcha_solution:
                                    captcha_input.clear()
                                    captcha_input.send_keys(captcha_solution)
                                    logger.info(f"Entered image CAPTCHA: {captcha_solution}")
                                    captcha_solved = True
                        except Exception as e:
                            logger.debug(f"Image CAPTCHA method failed: {str(e)}")
                    
                    if captcha_solved:
                        break
                    else:
                        logger.warning(f"CAPTCHA solving failed on attempt {attempt + 1}")
                        if attempt < captcha_attempts - 1:
                            # Refresh page and try again
                            self.driver.refresh()
                            time.sleep(3)
                            
                            # Re-fill form after refresh
                            WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.ID, "case_type"))
                            )
                            
                            case_type_select = Select(self.driver.find_element(By.ID, "case_type"))
                            case_type_select.select_by_value(case_type)
                            
                            case_number_input = self.driver.find_element(By.ID, "case_number")
                            case_number_input.clear()
                            case_number_input.send_keys(case_number)
                            
                            filing_year_select = Select(self.driver.find_element(By.ID, "case_year"))
                            filing_year_select.select_by_value(filing_year)
                            
                            continue
                        else:
                            logger.error("All CAPTCHA attempts failed")
                            return None
                    
                except NoSuchElementException:
                    logger.info("No CAPTCHA found on page")
                    break
            
            # Submit form - try different selectors
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']", 
                "button:contains('Submit')",
                "input[value*='Submit']",
                "button[class*='submit']",
                "input[class*='submit']",
                ".btn-primary",
                ".submit-btn",
                "button",
                "input[type='button']"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    if selector.startswith("button:contains"):
                        # Use XPath for text content
                        submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
                    else:
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if submit_button and submit_button.is_enabled():
                        logger.info(f"Found submit button with selector: {selector}")
                        break
                except:
                    continue
            
            if not submit_button:
                # Try to find any clickable button
                try:
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    inputs = self.driver.find_elements(By.XPATH, "//input[@type='button' or @type='submit']")
                    all_buttons = buttons + inputs
                    
                    logger.info(f"Found {len(all_buttons)} total buttons/inputs")
                    for i, btn in enumerate(all_buttons):
                        btn_text = btn.text.strip() or btn.get_attribute('value') or btn.get_attribute('class')
                        logger.info(f"Button {i}: '{btn_text}' - enabled: {btn.is_enabled()}")
                        
                        if btn.is_enabled() and any(keyword in btn_text.lower() for keyword in ['submit', 'search', 'go', 'find']):
                            submit_button = btn
                            logger.info(f"Selected button: '{btn_text}'")
                            break
                    
                    if not submit_button and all_buttons:
                        # Use first enabled button as fallback
                        for btn in all_buttons:
                            if btn.is_enabled():
                                submit_button = btn
                                logger.info(f"Using fallback button: '{btn.text or btn.get_attribute('value')}'")
                                break
                                
                except Exception as e:
                    logger.error(f"Error finding buttons: {str(e)}")
            
            if submit_button:
                submit_button.click()
                logger.info("Form submitted successfully")
            else:
                logger.error("No submit button found")
                return None
            
            # Wait for results to load
            logger.info("Waiting for results to load...")
            time.sleep(8)
            
            # Keep browser open longer if visible for debugging
            if self.show_browser and not self.headless:
                logger.info("Results loaded - keeping browser open for 10 seconds for inspection...")
                time.sleep(10)
            
            # Check for "No records found" or similar messages
            page_source = self.driver.page_source.lower()
            if any(phrase in page_source for phrase in ['no record found', 'no records found', 'case not found', 'invalid case']):
                logger.info(f"Case not found: {case_type} {case_number}/{filing_year}")
                if self.show_browser:
                    input("Press Enter to close browser...")
                return None
            
            # Parse case data from results page
            case_data = self.parse_case_details()
            
            if case_data:
                logger.info(f"Successfully scraped case data for: {case_type} {case_number}/{filing_year}")
                if self.show_browser:
                    logger.info("Case data found - keeping browser open for 15 seconds...")
                    time.sleep(15)
                return case_data
            else:
                logger.warning(f"No case data found for: {case_type} {case_number}/{filing_year}")
                if self.show_browser:
                    input("Press Enter to close browser...")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping case data: {str(e)}", exc_info=True)
            return None
        finally:
            if self.driver:
                self.driver.quit()
    
    def scrape_orders_page(self, orders_url):
        """Scrape orders page to get list of orders with download links"""
        try:
            logger.info(f"Scraping orders page: {orders_url}")
            
            # Initialize driver if not already done or if it's old
            current_time = time.time()
            driver_age = current_time - self.driver_setup_time if self.driver_setup_time else float('inf')
            
            if (not self.driver or 
                not hasattr(self.driver, 'session_id') or 
                driver_age > self.max_driver_age):
                
                if self.driver and driver_age > self.max_driver_age:
                    logger.info("Driver is old, creating fresh one for better performance")
                    
                self.setup_driver()
                self.driver_setup_time = current_time
            else:
                # Check if driver is still alive
                try:
                    self.driver.current_url
                    logger.info("Reusing existing driver session for better speed")
                except:
                    logger.info("Driver session expired, creating new one")
                    self.setup_driver()
                    self.driver_setup_time = current_time
            
            # Navigate to orders page
            self.driver.get(orders_url)
            time.sleep(3)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            orders_data = {
                'orders': [],
                'total_orders': 0,
                'raw_html': self.driver.page_source
            }
            
            # Look for orders table
            # Structure: S.No. | Case No/Order Link | Date of Order | Corrigendum Link/Corr. Date | HINDI ORDER
            table_selectors = [
                "table",
                ".table",
                "#ordersTable",
                "[class*='table']"
            ]
            
            table = None
            for selector in table_selectors:
                try:
                    table = self.driver.find_element(By.CSS_SELECTOR, selector)
                    logger.info(f"Found orders table using selector: {selector}")
                    break
                except:
                    continue
            
            if not table:
                logger.warning("No orders table found")
                return orders_data
            
            # Find all rows (skip header)
            rows = table.find_elements(By.TAG_NAME, "tr")
            logger.info(f"Found {len(rows)} rows in orders table")
            
            for i, row in enumerate(rows[1:], 1):  # Skip header row
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 3:
                        continue
                    
                    # Extract order data
                    sno = cells[0].text.strip() if len(cells) > 0 else str(i)
                    
                    # Case No/Order Link (usually contains a link)
                    order_cell = cells[1] if len(cells) > 1 else None
                    order_text = order_cell.text.strip() if order_cell else ""
                    
                    # Look for PDF download link
                    pdf_link = None
                    try:
                        link_element = order_cell.find_element(By.TAG_NAME, "a")
                        pdf_link = link_element.get_attribute("href")
                        if pdf_link and not pdf_link.startswith("http"):
                            pdf_link = f"https://delhihighcourt.nic.in{pdf_link}"
                    except:
                        pass
                    
                    # Date of Order
                    order_date = cells[2].text.strip() if len(cells) > 2 else ""
                    
                    # Corrigendum Link (if exists)
                    corrigendum_link = None
                    corrigendum_date = ""
                    if len(cells) > 3:
                        corr_cell = cells[3]
                        corrigendum_date = corr_cell.text.strip()
                        try:
                            corr_link_element = corr_cell.find_element(By.TAG_NAME, "a")
                            corrigendum_link = corr_link_element.get_attribute("href")
                            if corrigendum_link and not corrigendum_link.startswith("http"):
                                corrigendum_link = f"https://delhihighcourt.nic.in{corrigendum_link}"
                        except:
                            pass
                    
                    # Hindi Order Link (if exists)
                    hindi_link = None
                    if len(cells) > 4:
                        hindi_cell = cells[4]
                        try:
                            hindi_link_element = hindi_cell.find_element(By.TAG_NAME, "a")
                            hindi_link = hindi_link_element.get_attribute("href")
                            if hindi_link and not hindi_link.startswith("http"):
                                hindi_link = f"https://delhihighcourt.nic.in{hindi_link}"
                        except:
                            pass
                    
                    order_data = {
                        'sno': sno,
                        'order_text': order_text,
                        'order_date': order_date,
                        'pdf_link': pdf_link,
                        'corrigendum_date': corrigendum_date,
                        'corrigendum_link': corrigendum_link,
                        'hindi_link': hindi_link
                    }
                    
                    orders_data['orders'].append(order_data)
                    logger.info(f"Parsed order {i}: {order_text} - {order_date}")
                    
                except Exception as e:
                    logger.warning(f"Error parsing order row {i}: {str(e)}")
                    continue
            
            orders_data['total_orders'] = len(orders_data['orders'])
            logger.info(f"Successfully parsed {orders_data['total_orders']} orders")
            
            return orders_data
            
        except Exception as e:
            logger.error(f"Error scraping orders page: {str(e)}", exc_info=True)
            return {
                'orders': [],
                'total_orders': 0,
                'raw_html': '',
                'error': str(e)
            }

    def download_pdf(self, pdf_url):
        """Download PDF from Delhi High Court"""
        try:
            logger.info(f"Downloading PDF: {pdf_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/pdf,application/octet-stream,*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(pdf_url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Check if response is actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and 'octet-stream' not in content_type:
                logger.warning(f"Response is not a PDF: {content_type}")
                # Still try to download as it might be a PDF with wrong content-type
            
            # Generate filename from URL
            filename = pdf_url.split('/')[-1]
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            
            # Read content
            pdf_content = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    pdf_content += chunk
            
            if len(pdf_content) < 100:  # Too small to be a valid PDF
                logger.error(f"PDF content too small: {len(pdf_content)} bytes")
                return None
            
            logger.info(f"Successfully downloaded PDF: {len(pdf_content)} bytes")
            
            return {
                'content': pdf_content,
                'filename': filename,
                'mimetype': 'application/pdf',
                'size': len(pdf_content)
            }
            
        except Exception as e:
            logger.error(f"Error downloading PDF: {str(e)}")
            return None

    def parse_case_details(self):
        """Parse case details from Delhi High Court results table"""
        try:
            logger.info("Parsing Delhi High Court results table...")
            
            case_data = {
                'cases': [],
                'total_cases': 0,
                'raw_html': self.driver.page_source
            }
            
            # Look for the results table
            # Delhi High Court uses a table with columns: S.No. | Diary No./Case No.[STATUS] | Petitioner Vs. Respondent | Listing Date/Court No.
            
            # Try different table selectors
            table_selectors = [
                "table",
                "table.table",
                "table[class*='table']",
                "//table[contains(@class, 'table')]",
                "//table[.//th[contains(text(), 'S.No')]]"
            ]
            
            results_table = None
            for selector in table_selectors:
                try:
                    if selector.startswith("//"):
                        tables = self.driver.find_elements(By.XPATH, selector)
                    else:
                        tables = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for table in tables:
                        table_text = table.text.lower()
                        if any(keyword in table_text for keyword in ['s.no', 'case no', 'petitioner', 'respondent']):
                            results_table = table
                            logger.info(f"Found results table using selector: {selector}")
                            break
                    
                    if results_table:
                        break
                except Exception as e:
                    continue
            
            if not results_table:
                logger.warning("Results table not found, trying to parse from page text")
                return self.parse_from_page_text()
            
            # Parse table rows
            rows = results_table.find_elements(By.TAG_NAME, "tr")
            logger.info(f"Found {len(rows)} rows in results table")
            
            for i, row in enumerate(rows):
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 3:  # Skip header rows or incomplete rows
                        continue
                    
                    # Extract data from cells
                    # Column 0: S.No.
                    # Column 1: Diary No. / Case No.[STATUS] 
                    # Column 2: Petitioner Vs. Respondent
                    # Column 3: Listing Date / Court No.
                    
                    sno = cells[0].text.strip() if len(cells) > 0 else ""
                    case_info = cells[1].text.strip() if len(cells) > 1 else ""
                    parties = cells[2].text.strip() if len(cells) > 2 else ""
                    listing_info = cells[3].text.strip() if len(cells) > 3 else ""
                    
                    # Skip if this looks like a header row
                    if sno.lower() in ['s.no', 's.no.', 'sno'] or not case_info:
                        continue
                    
                    # Parse case number and status from case_info
                    # Format: "CEAC - 1 / 2024 [DISPOSED] Orders"
                    case_number = ""
                    status = "Unknown"
                    
                    if '[' in case_info and ']' in case_info:
                        # Extract status from brackets
                        status_start = case_info.find('[')
                        status_end = case_info.find(']')
                        if status_start != -1 and status_end != -1:
                            status = case_info[status_start+1:status_end].strip()
                            case_number = case_info[:status_start].strip()
                    else:
                        case_number = case_info
                    
                    # Parse listing info for dates and court
                    next_date = "N/A"
                    last_date = "N/A"
                    court_no = "N/A"
                    
                    if listing_info:
                        # Extract NEXT DATE, Last Date, COURT NO
                        if "NEXT DATE:" in listing_info:
                            next_start = listing_info.find("NEXT DATE:") + len("NEXT DATE:")
                            next_end = listing_info.find("Last Date:", next_start)
                            if next_end == -1:
                                next_end = listing_info.find("COURT NO:", next_start)
                            if next_end == -1:
                                next_end = len(listing_info)
                            next_date = listing_info[next_start:next_end].strip()
                        
                        if "Last Date:" in listing_info:
                            last_start = listing_info.find("Last Date:") + len("Last Date:")
                            last_end = listing_info.find("COURT NO:", last_start)
                            if last_end == -1:
                                last_end = len(listing_info)
                            last_date = listing_info[last_start:last_end].strip()
                        
                        if "COURT NO:" in listing_info:
                            court_start = listing_info.find("COURT NO:") + len("COURT NO:")
                            court_no = listing_info[court_start:].strip()
                    
                    # Look for PDF/Order links in this row
                    pdf_links = []
                    order_links = row.find_elements(By.TAG_NAME, "a")
                    for link in order_links:
                        href = link.get_attribute('href')
                        link_text = link.text.strip()
                        if href and ('.pdf' in href.lower() or 'order' in link_text.lower()):
                            pdf_links.append({
                                'text': link_text,
                                'url': href if href.startswith('http') else f"{self.base_url}/{href.lstrip('/')}"
                            })
                    
                    case_record = {
                        'sno': sno,
                        'case_number': case_number,
                        'status': status,
                        'parties': parties,
                        'next_date': next_date,
                        'last_date': last_date,
                        'court_no': court_no,
                        'pdf_links': pdf_links,
                        'raw_text': f"{case_info} | {parties} | {listing_info}"
                    }
                    
                    case_data['cases'].append(case_record)
                    logger.info(f"Parsed case {i}: {case_number} - {status}")
                    
                except Exception as e:
                    logger.warning(f"Error parsing row {i}: {str(e)}")
                    continue
            
            case_data['total_cases'] = len(case_data['cases'])
            logger.info(f"Successfully parsed {case_data['total_cases']} cases")
            
            return case_data
            
        except Exception as e:
            logger.error(f"Error parsing case details: {str(e)}")
            return self.parse_from_page_text()
    
    def parse_from_page_text(self):
        """Fallback parser using page text when table parsing fails"""
        try:
            logger.info("Using fallback text parsing...")
            page_text = self.driver.page_source
            
            case_data = {
                'cases': [],
                'total_cases': 0,
                'raw_html': page_text,
                'parsing_method': 'text_fallback'
            }
            
            # Look for case patterns in the page text
            import re
            
            # Pattern for case entries like "CEAC - 1 / 2024 [DISPOSED]"
            case_pattern = r'([A-Z\.]+\s*-\s*\d+\s*/\s*\d{4})\s*\[([^\]]+)\]'
            matches = re.findall(case_pattern, page_text)
            
            for i, (case_num, status) in enumerate(matches):
                case_data['cases'].append({
                    'sno': str(i + 1),
                    'case_number': case_num.strip(),
                    'status': status.strip(),
                    'parties': 'Parties information not available',
                    'next_date': 'N/A',
                    'last_date': 'N/A',
                    'court_no': 'N/A',
                    'pdf_links': [],
                    'raw_text': f"{case_num} [{status}]"
                })
            
            case_data['total_cases'] = len(case_data['cases'])
            logger.info(f"Fallback parsing found {case_data['total_cases']} cases")
            
            return case_data
            
        except Exception as e:
            logger.error(f"Fallback parsing failed: {str(e)}")
            return {
                'cases': [],
                'total_cases': 0,
                'raw_html': self.driver.page_source,
                'error': str(e)
            }
            
            # If no specific orders found, look for general document links
            if not case_data['orders_judgments']:
                doc_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'pdf')]")
                for link in doc_links:
                    href = link.get_attribute('href')
                    if href:
                        case_data['orders_judgments'].append({
                            'date': 'Date not available',
                            'description': link.text.strip() or 'Court Document',
                            'pdf_link': href if href.startswith('http') else f"{self.base_url}/{href.lstrip('/')}"
                        })
            
            return case_data
            
        except Exception as e:
            logger.error(f"Error parsing case details: {str(e)}")
            return None
    
    def extract_date_from_context(self, element):
        """Extract date from the context around a link element"""
        try:
            # Look for date patterns in the same row or nearby elements
            parent_row = element.find_element(By.XPATH, "./ancestor::tr[1]")
            row_text = parent_row.text
            
            # Common date patterns
            date_patterns = [
                r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b',
                r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2})\b',
                r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, row_text)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception:
            return None
    
    def download_pdf(self, pdf_url):
        """Download actual PDF from court website"""
        try:
            logger.info(f"Downloading PDF from: {pdf_url}")
            
            # Make request to download PDF
            response = self.session.get(pdf_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Check if response is actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type:
                logger.warning(f"Response is not a PDF: {content_type}")
                # Still try to process it as it might be a PDF with wrong content-type
            
            # Read PDF content
            pdf_content = response.content
            
            if len(pdf_content) == 0:
                logger.error("Downloaded PDF is empty")
                return None
            
            # Extract filename from URL or Content-Disposition header
            filename = self.extract_filename_from_response(response, pdf_url)
            
            logger.info(f"Successfully downloaded PDF: {filename} ({len(pdf_content)} bytes)")
            
            return {
                'content': pdf_content,
                'filename': filename,
                'mimetype': 'application/pdf'
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error downloading PDF: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error downloading PDF: {str(e)}")
            return None
    
    def extract_filename_from_response(self, response, url):
        """Extract filename from response headers or URL"""
        try:
            # Try to get filename from Content-Disposition header
            content_disposition = response.headers.get('content-disposition', '')
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"\'')
                return filename
            
            # Extract from URL
            filename = url.split('/')[-1]
            if '?' in filename:
                filename = filename.split('?')[0]
            
            # Ensure .pdf extension
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
            
            return filename
            
        except Exception:
            return 'court_document.pdf'

class ProductionCourtScraper:
    """Production scraper that combines live scraping with fallback to mock data"""
    
    def __init__(self, use_live_scraping=True):
        self.use_live_scraping = use_live_scraping
        self.live_scraper = DelhiHighCourtLiveScraper()
        
        # Import mock scraper as fallback
        from simple_scraper import MockCourtScraper
        self.mock_scraper = MockCourtScraper()
    
    def scrape_case_data(self, case_type, case_number, filing_year):
        """Scrape case data with live scraping and fallback"""
        if self.use_live_scraping:
            try:
                logger.info("Attempting live scraping...")
                case_data = self.live_scraper.scrape_case_data(case_type, case_number, filing_year)
                
                if case_data:
                    logger.info("Live scraping successful")
                    return case_data
                else:
                    logger.warning("Live scraping returned no data, falling back to mock data")
                    return self.mock_scraper.scrape_case_data(case_type, case_number, filing_year)
                    
            except Exception as e:
                logger.error(f"Live scraping failed: {str(e)}, falling back to mock data")
                return self.mock_scraper.scrape_case_data(case_type, case_number, filing_year)
        else:
            logger.info("Using mock data (live scraping disabled)")
            return self.mock_scraper.scrape_case_data(case_type, case_number, filing_year)
    
    def download_pdf(self, pdf_url):
        """Download PDF with live downloading and fallback"""
        if self.use_live_scraping and pdf_url.startswith('http'):
            try:
                logger.info("Attempting live PDF download...")
                pdf_data = self.live_scraper.download_pdf(pdf_url)
                
                if pdf_data:
                    logger.info("Live PDF download successful")
                    return pdf_data
                else:
                    logger.warning("Live PDF download failed, falling back to mock PDF")
                    return self.mock_scraper.download_pdf(pdf_url)
                    
            except Exception as e:
                logger.error(f"Live PDF download failed: {str(e)}, falling back to mock PDF")
                return self.mock_scraper.download_pdf(pdf_url)
        else:
            logger.info("Using mock PDF (live downloading disabled or invalid URL)")
            return self.mock_scraper.download_pdf(pdf_url)