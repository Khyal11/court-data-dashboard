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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
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

class EnhancedDelhiHighCourtScraper:
    """Enhanced scraper for Delhi High Court with improved speed and reliability"""
    
    def __init__(self, headless=True, show_browser=False):
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
        self.max_retries = 3
        
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
    
    def setup_driver(self):
        """Setup Chrome WebDriver with optimized options for speed"""
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
                logger.info("Running browser in visible mode")
            
            # Enhanced performance optimizations for speed
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
            
            # Additional speed optimizations
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-background-media-suspend')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            
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
            
            # Set timeouts for faster operations
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(5)
            
            return True
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {str(e)}")
            return False
    
    def solve_captcha_fast(self, captcha_element):
        """Fast CAPTCHA solving optimized for Delhi High Court"""
        try:
            if not TESSERACT_AVAILABLE:
                logger.warning("Tesseract OCR not available. Cannot solve CAPTCHA automatically.")
                return None
                
            # Take screenshot of CAPTCHA
            captcha_screenshot = captcha_element.screenshot_as_png
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(captcha_screenshot))
            
            # Fast preprocessing for Delhi High Court CAPTCHAs (usually simple digits)
            image = image.convert('L')  # Convert to grayscale
            
            # Quick enhancement
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.5)
            
            # Resize for better OCR
            width, height = image.size
            image = image.resize((width * 2, height * 2), Image.LANCZOS)
            
            # Fast OCR with digit-only configuration
            captcha_text = pytesseract.image_to_string(
                image, 
                config='--psm 7 -c tessedit_char_whitelist=0123456789'
            )
            captcha_text = ''.join(filter(str.isdigit, captcha_text.strip()))
            
            logger.info(f"Fast CAPTCHA OCR result: '{captcha_text}' (length: {len(captcha_text)})")
            
            # Return only if we got a reasonable result
            if len(captcha_text) >= 3 and len(captcha_text) <= 8:
                return captcha_text
            else:
                logger.warning(f"CAPTCHA result seems invalid: '{captcha_text}'")
                return None
            
        except Exception as e:
            logger.error(f"Fast CAPTCHA solving failed: {str(e)}")
            return None
    
    def fast_search_case(self, case_type, case_number, filing_year):
        """
        Fast case search with enhanced error handling and retry logic
        Returns: {
            'success': bool,
            'message': str,
            'error': str,
            'case_data': dict or None
        }
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🚀 Fast search attempt {attempt + 1}/{self.max_retries}: {case_type} {case_number}/{filing_year}")
                
                if not self.setup_driver():
                    logger.error("Failed to setup WebDriver")
                    if attempt == self.max_retries - 1:
                        return {
                            'success': False,
                            'message': 'Failed to initialize browser',
                            'error': 'browser_setup_failed',
                            'case_data': None
                        }
                    continue
                
                # Navigate to case status page
                self.driver.get(self.case_status_url)
                time.sleep(1)  # Reduced wait time
                
                # Wait for page to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "case_type"))
                )
                
                # Fill case details quickly
                case_type_select = Select(self.driver.find_element(By.ID, "case_type"))
                case_type_select.select_by_value(case_type)
                logger.info(f"✅ Selected case type: {case_type}")
                
                case_number_input = self.driver.find_element(By.ID, "case_number")
                case_number_input.clear()
                case_number_input.send_keys(case_number)
                logger.info(f"✅ Entered case number: {case_number}")
                
                filing_year_select = Select(self.driver.find_element(By.ID, "case_year"))
                filing_year_select.select_by_value(filing_year)
                logger.info(f"✅ Selected year: {filing_year}")
                
                # Handle CAPTCHA quickly
                captcha_solved = self.handle_captcha_fast()
                if not captcha_solved:
                    logger.warning(f"❌ CAPTCHA failed on attempt {attempt + 1}")
                    if attempt == self.max_retries - 1:
                        return {
                            'success': False,
                            'message': 'CAPTCHA verification failed after multiple attempts',
                            'error': 'captcha_failed',
                            'case_data': None
                        }
                    continue
                
                # Submit form quickly
                if not self.submit_form_fast():
                    logger.warning(f"❌ Form submission failed on attempt {attempt + 1}")
                    if attempt == self.max_retries - 1:
                        return {
                            'success': False,
                            'message': 'Form submission failed',
                            'error': 'form_submission_failed',
                            'case_data': None
                        }
                    continue
                
                # Wait for results
                logger.info("⏳ Waiting for results...")
                time.sleep(5)  # Increased wait time for page to fully load
                
                # Debug: Log page title and URL to understand what page we're on
                try:
                    current_url = self.driver.current_url
                    page_title = self.driver.title
                    logger.info(f"🌐 Current page: {page_title} | URL: {current_url}")
                except:
                    pass
                
                # Check for "No records found"
                page_source = self.driver.page_source.lower()
                if any(phrase in page_source for phrase in ['no record found', 'no records found', 'case not found', 'invalid case']):
                    logger.info(f"❌ Case not found: {case_type} {case_number}/{filing_year}")
                    return {
                        'success': False,
                        'message': f'No case found for {case_type} {case_number}/{filing_year}',
                        'error': 'no_data_found',
                        'case_data': None
                    }
                
                # Parse case data quickly
                case_data = self.parse_case_data_fast()
                
                if case_data and case_data.get('total_cases', 0) > 0:
                    logger.info(f"✅ Fast search successful: Found {case_data.get('total_cases', 0)} case(s)")
                    return {
                        'success': True,
                        'message': 'Case found successfully',
                        'error': None,
                        'case_data': case_data
                    }
                elif case_data and case_data.get('total_cases', 0) == 0:
                    # Valid response but no cases found
                    logger.info(f"❌ No cases found for the search criteria")
                    return {
                        'success': False,
                        'message': f'No case found for the given search criteria',
                        'error': 'no_data_found',
                        'case_data': None
                    }
                else:
                    logger.warning(f"❌ No case data parsed on attempt {attempt + 1}")
                    if attempt == self.max_retries - 1:
                        return {
                            'success': False,
                            'message': 'Case data could not be parsed',
                            'error': 'parsing_failed',
                            'case_data': None
                        }
                    continue
                    
            except TimeoutException as e:
                logger.warning(f"⏰ Timeout on attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_retries - 1:
                    return {
                        'success': False,
                        'message': 'Search timed out',
                        'error': 'timeout',
                        'case_data': None
                    }
                continue
                
            except Exception as e:
                logger.error(f"❌ Error on attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_retries - 1:
                    return {
                        'success': False,
                        'message': f'Search failed: {str(e)}',
                        'error': 'unknown_error',
                        'case_data': None
                    }
                continue
                
            finally:
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
        
        # If we get here, all retries failed
        return {
            'success': False,
            'message': 'Search failed after maximum retries',
            'error': 'max_retries_exceeded',
            'case_data': None
        }
    
    def handle_captcha_fast(self):
        """Fast CAPTCHA handling"""
        try:
            # Look for text-based CAPTCHA first (fastest)
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
                        logger.info(f"📝 Found text-based CAPTCHA: {captcha_text}")
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
                    logger.info(f"✅ Entered text CAPTCHA: {captcha_text}")
                    return True
            
            # Try image-based CAPTCHA if text-based failed
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
                    captcha_solution = self.solve_captcha_fast(captcha_img)
                    if captcha_solution:
                        captcha_input.clear()
                        captcha_input.send_keys(captcha_solution)
                        logger.info(f"✅ Entered image CAPTCHA: {captcha_solution}")
                        return True
            except:
                pass
            
            # No CAPTCHA found
            logger.info("ℹ️ No CAPTCHA found on page")
            return True
            
        except Exception as e:
            logger.error(f"❌ CAPTCHA handling failed: {str(e)}")
            return False
    
    def submit_form_fast(self):
        """Fast form submission"""
        try:
            # Try different submit button selectors
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']", 
                "button:contains('Submit')",
                "input[value*='Submit']",
                "button[class*='submit']",
                ".btn-primary",
                ".submit-btn"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    if selector.startswith("button:contains"):
                        submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
                    else:
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if submit_button and submit_button.is_enabled():
                        logger.info(f"🎯 Found submit button: {selector}")
                        break
                except:
                    continue
            
            if not submit_button:
                # Fallback: find any enabled button
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                inputs = self.driver.find_elements(By.XPATH, "//input[@type='button' or @type='submit']")
                all_buttons = buttons + inputs
                
                for btn in all_buttons:
                    if btn.is_enabled():
                        btn_text = btn.text.strip() or btn.get_attribute('value') or ''
                        if any(keyword in btn_text.lower() for keyword in ['submit', 'search', 'go', 'find']):
                            submit_button = btn
                            logger.info(f"🎯 Using fallback button: '{btn_text}'")
                            break
            
            if submit_button:
                submit_button.click()
                logger.info("✅ Form submitted successfully")
                return True
            else:
                logger.error("❌ No submit button found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Form submission failed: {str(e)}")
            return False
    
    def parse_case_data_fast(self):
        """Fast case data parsing optimized for single case results with stale element protection"""
        try:
            logger.info("🔍 Fast parsing case data...")
            
            # Wait a bit more for page to stabilize
            time.sleep(2)
            
            case_data = {
                'cases': [],
                'total_cases': 0,
                'raw_html': self.driver.page_source
            }
            
            # Get fresh page source to avoid stale elements
            page_source = self.driver.page_source
            
            # First, try to parse from HTML source directly (more reliable)
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Look for results table in HTML
            tables = soup.find_all('table')
            results_table = None
            
            for table in tables:
                table_text = table.get_text().lower()
                if any(keyword in table_text for keyword in ['s.no', 'case no', 'petitioner', 'respondent', 'diary']):
                    results_table = table
                    logger.info(f"📋 Found results table in HTML")
                    break
            
            if not results_table:
                logger.warning("⚠️ No results table found in HTML, trying text parsing")
                return self.parse_from_page_text_fast()
            
            # Parse table rows from HTML
            rows = results_table.find_all('tr')
            logger.info(f"📊 Found {len(rows)} rows in results table")
            
            for i, row in enumerate(rows):
                try:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 3:  # Skip header rows or incomplete rows
                        continue
                    
                    # Extract basic data from HTML
                    sno = cells[0].get_text(strip=True) if len(cells) > 0 else ""
                    case_info = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    parties = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    listing_info = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                    
                    # Skip header rows
                    if sno.lower() in ['s.no', 's.no.', 'sno', 'serial'] or not case_info:
                        logger.info(f"⏭️ Skipping header row: {sno}")
                        continue
                    
                    # Quick parsing of case number and status
                    case_number = ""
                    status = "Unknown"
                    
                    if '[' in case_info and ']' in case_info:
                        status_start = case_info.find('[')
                        status_end = case_info.find(']')
                        if status_start != -1 and status_end != -1:
                            status = case_info[status_start+1:status_end].strip()
                            case_number = case_info[:status_start].strip()
                    else:
                        case_number = case_info
                    
                    # Quick parsing of dates
                    next_date = "N/A"
                    last_date = "N/A"
                    court_no = "N/A"
                    
                    if listing_info:
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
                    
                    # Look for PDF links in HTML
                    pdf_links = []
                    links = cells[1].find_all('a') if len(cells) > 1 else []
                    for link in links:
                        href = link.get('href', '')
                        link_text = link.get_text(strip=True)
                        if href and ('.pdf' in href.lower() or 'order' in link_text.lower()):
                            full_url = href if href.startswith('http') else f"{self.base_url}/{href.lstrip('/')}"
                            pdf_links.append({
                                'text': link_text,
                                'url': full_url
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
                    logger.info(f"✅ Parsed case: {case_number} - {status}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing row {i}: {str(e)}")
                    continue
            
            case_data['total_cases'] = len(case_data['cases'])
            logger.info(f"🎉 Fast parsing complete: {case_data['total_cases']} cases found")
            
            # If no cases found, try alternative parsing
            if case_data['total_cases'] == 0:
                logger.info("🔄 No cases found with table parsing, trying alternative methods...")
                return self.parse_from_page_text_fast()
            
            return case_data
            
        except Exception as e:
            logger.error(f"❌ Fast parsing failed: {str(e)}")
            return self.parse_from_page_text_fast()
    
    def parse_from_page_text_fast(self):
        """Fast fallback parser using page text with multiple patterns"""
        try:
            logger.info("🔍 Using fast text parsing fallback...")
            page_text = self.driver.page_source
            
            case_data = {
                'cases': [],
                'total_cases': 0,
                'raw_html': page_text,
                'parsing_method': 'fast_text_fallback'
            }
            
            # Multiple regex patterns for different case formats
            import re
            
            # Pattern 1: Standard format with status in brackets
            pattern1 = r'([A-Z\.]+\s*-?\s*\d+\s*/\s*\d{4})\s*\[([^\]]+)\]'
            matches1 = re.findall(pattern1, page_text)
            
            # Pattern 2: Case number without status
            pattern2 = r'([A-Z\.]+\s*-?\s*\d+\s*/\s*\d{4})'
            matches2 = re.findall(pattern2, page_text)
            
            # Pattern 3: Look for table-like structure in text
            pattern3 = r'(\d+)\s+([A-Z\.]+\s*-?\s*\d+\s*/\s*\d{4})'
            matches3 = re.findall(pattern3, page_text)
            
            logger.info(f"🔍 Pattern matches: {len(matches1)} with status, {len(matches2)} without status, {len(matches3)} with S.No")
            
            # Process matches with status first
            for i, (case_num, status) in enumerate(matches1):
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
            
            # If no matches with status, try without status
            if len(case_data['cases']) == 0 and matches2:
                for i, case_num in enumerate(matches2[:5]):  # Limit to first 5 to avoid duplicates
                    if case_num.strip() and len(case_num.strip()) > 5:  # Basic validation
                        case_data['cases'].append({
                            'sno': str(i + 1),
                            'case_number': case_num.strip(),
                            'status': 'Status not available',
                            'parties': 'Parties information not available',
                            'next_date': 'N/A',
                            'last_date': 'N/A',
                            'court_no': 'N/A',
                            'pdf_links': [],
                            'raw_text': case_num.strip()
                        })
            
            # If still no matches, try with S.No pattern
            if len(case_data['cases']) == 0 and matches3:
                for sno, case_num in matches3[:5]:  # Limit to first 5
                    if case_num.strip() and len(case_num.strip()) > 5:
                        case_data['cases'].append({
                            'sno': sno.strip(),
                            'case_number': case_num.strip(),
                            'status': 'Status not available',
                            'parties': 'Parties information not available',
                            'next_date': 'N/A',
                            'last_date': 'N/A',
                            'court_no': 'N/A',
                            'pdf_links': [],
                            'raw_text': f"{sno} {case_num}"
                        })
            
            case_data['total_cases'] = len(case_data['cases'])
            logger.info(f"🎉 Fast text parsing found {case_data['total_cases']} cases")
            
            # If still no cases found, check for common "no results" messages
            if case_data['total_cases'] == 0:
                page_lower = page_text.lower()
                if any(msg in page_lower for msg in ['no record found', 'no records found', 'case not found', 'invalid case', 'no data found']):
                    logger.info("📝 Page indicates no records found")
                else:
                    logger.warning("⚠️ No cases found and no 'no records' message detected")
                    # Log a sample of the page content for debugging
                    sample_text = page_text[:1000] if len(page_text) > 1000 else page_text
                    logger.debug(f"Page sample: {sample_text}")
            
            return case_data
            
        except Exception as e:
            logger.error(f"❌ Fast text parsing failed: {str(e)}")
            return {
                'cases': [],
                'total_cases': 0,
                'raw_html': self.driver.page_source if self.driver else '',
                'error': str(e)
            }
    
    def download_pdf(self, pdf_url):
        """Fast PDF download"""
        try:
            logger.info(f"📥 Fast downloading PDF: {pdf_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/pdf,application/octet-stream,*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            response = requests.get(pdf_url, headers=headers, timeout=20, stream=True)
            response.raise_for_status()
            
            # Generate filename
            filename = pdf_url.split('/')[-1]
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            
            # Read content efficiently
            pdf_content = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    pdf_content += chunk
            
            if len(pdf_content) < 100:
                logger.error(f"❌ PDF too small: {len(pdf_content)} bytes")
                return None
            
            logger.info(f"✅ PDF downloaded: {len(pdf_content)} bytes")
            
            return {
                'content': pdf_content,
                'filename': filename,
                'mimetype': 'application/pdf',
                'size': len(pdf_content)
            }
            
        except Exception as e:
            logger.error(f"❌ Fast PDF download failed: {str(e)}")
            return None
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None