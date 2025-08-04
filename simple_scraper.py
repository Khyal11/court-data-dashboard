import requests
from bs4 import BeautifulSoup
import time
import logging
import re
from datetime import datetime
import io
from flask import Response
import json

logger = logging.getLogger(__name__)

class SimpleCourtScraper:
    """Simplified scraper for Delhi High Court website using requests only"""
    
    def __init__(self):
        self.base_url = "https://delhihighcourt.nic.in"
        self.case_status_url = f"{self.base_url}/case_status.asp"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def scrape_case_data(self, case_type, case_number, filing_year):
        """
        Scrape case data using requests only (no Selenium)
        This is a simplified approach that works with mock data
        """
        try:
            logger.info(f"Attempting to scrape case: {case_type} {case_number}/{filing_year}")
            
            # For demo purposes, we'll use the mock scraper
            # In production, you would implement actual scraping here
            mock_scraper = MockCourtScraper()
            return mock_scraper.scrape_case_data(case_type, case_number, filing_year)
            
        except Exception as e:
            logger.error(f"Error in simple scraper: {str(e)}")
            return None
    
    def download_pdf(self, pdf_url):
        """Download PDF file - delegate to mock scraper for demo"""
        try:
            logger.info(f"SimpleCourtScraper: Downloading PDF: {pdf_url}")
            
            # For demo purposes, use mock scraper to generate PDF
            mock_scraper = MockCourtScraper()
            pdf_data = mock_scraper.download_pdf(pdf_url)
            
            logger.info(f"SimpleCourtScraper: PDF data received: {type(pdf_data)}")
            return pdf_data
            
        except Exception as e:
            logger.error(f"Error downloading PDF: {str(e)}")
            return None

class MockCourtScraper:
    """Enhanced mock scraper with realistic data and PDF links"""
    
    def __init__(self):
        self.base_url = "https://delhihighcourt.nic.in"
        # Define valid demo cases
        self.valid_cases = {
            ('W.P.(C)', '1234', '2023'): True,
            ('CRL.A.', '5678', '2022'): True,
            ('FAO', '9012', '2024'): True,
        }
    
    def scrape_case_data(self, case_type, case_number, filing_year):
        """Return enhanced mock data with PDF links - only for valid demo cases"""
        case_key = (case_type, case_number, filing_year)
        
        # Check if this is a valid demo case
        if case_key not in self.valid_cases:
            logger.info(f"Case not found: {case_type} {case_number}/{filing_year}")
            return None
        
        logger.info(f"Using mock data for case: {case_type} {case_number}/{filing_year}")
        
        # Create different mock data based on case details
        case_data = {
            'parties': [],
            'filing_date': None,
            'next_hearing_date': None,
            'orders_judgments': [],
            'status': 'Unknown',
            'raw_html': '<html><body>Mock case data</body></html>'
        }
        
        # Customize based on case type and number
        if case_type == "W.P.(C)":
            case_data.update({
                'parties': [
                    {'type': 'Petitioner', 'name': 'ABC Corporation Ltd.'},
                    {'type': 'Respondent', 'name': 'Union of India & Ors.'}
                ],
                'filing_date': '15/03/2023',
                'next_hearing_date': '25/01/2025',
                'status': 'Pending',
                'orders_judgments': [
                    {
                        'date': '15/03/2023',
                        'description': 'Writ petition filed and registered',
                        'pdf_link': f'{self.base_url}/orders/wp_c_{case_number}_{filing_year}_filing.pdf'
                    },
                    {
                        'date': '10/11/2024',
                        'description': 'Interim order - Notice issued to respondents',
                        'pdf_link': f'{self.base_url}/orders/wp_c_{case_number}_{filing_year}_interim.pdf'
                    },
                    {
                        'date': '15/12/2024',
                        'description': 'Counter affidavit filed by respondent',
                        'pdf_link': None
                    }
                ]
            })
        elif case_type == "CRL.A.":
            case_data.update({
                'parties': [
                    {'type': 'Appellant', 'name': 'Rajesh Kumar'},
                    {'type': 'Respondent', 'name': 'State of Delhi'}
                ],
                'filing_date': '20/08/2022',
                'next_hearing_date': None,
                'status': 'Disposed',
                'orders_judgments': [
                    {
                        'date': '20/08/2022',
                        'description': 'Criminal appeal filed',
                        'pdf_link': f'{self.base_url}/orders/crl_a_{case_number}_{filing_year}_filing.pdf'
                    },
                    {
                        'date': '15/02/2023',
                        'description': 'Arguments heard',
                        'pdf_link': None
                    },
                    {
                        'date': '10/05/2023',
                        'description': 'Final judgment - Appeal dismissed',
                        'pdf_link': f'{self.base_url}/orders/crl_a_{case_number}_{filing_year}_judgment.pdf'
                    }
                ]
            })
        elif case_type == "FAO":
            case_data.update({
                'parties': [
                    {'type': 'Appellant', 'name': 'XYZ Pvt. Ltd.'},
                    {'type': 'Respondent', 'name': 'Delhi Development Authority'}
                ],
                'filing_date': '05/01/2024',
                'next_hearing_date': '30/01/2025',
                'status': 'Part Heard',
                'orders_judgments': [
                    {
                        'date': '05/01/2024',
                        'description': 'First appeal from order filed',
                        'pdf_link': f'{self.base_url}/orders/fao_{case_number}_{filing_year}_filing.pdf'
                    },
                    {
                        'date': '20/06/2024',
                        'description': 'Preliminary hearing - Issues framed',
                        'pdf_link': f'{self.base_url}/orders/fao_{case_number}_{filing_year}_issues.pdf'
                    },
                    {
                        'date': '15/11/2024',
                        'description': 'Arguments partially heard',
                        'pdf_link': None
                    }
                ]
            })
        else:
            # Default case data
            case_data.update({
                'parties': [
                    {'type': 'Petitioner', 'name': 'John Doe'},
                    {'type': 'Respondent', 'name': 'State of Delhi'}
                ],
                'filing_date': '01/01/2023',
                'next_hearing_date': '15/02/2025',
                'status': 'Pending',
                'orders_judgments': [
                    {
                        'date': '01/01/2023',
                        'description': 'Case filed and registered',
                        'pdf_link': f'{self.base_url}/orders/case_{case_number}_{filing_year}_filing.pdf'
                    }
                ]
            })
        
        return case_data
    
    def download_pdf(self, pdf_url):
        """Generate a mock PDF for demonstration"""
        try:
            logger.info(f"MockCourtScraper: Generating PDF for URL: {pdf_url}")
            
            # Create a simple mock PDF content
            mock_pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Mock Court Order/Judgment) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
300
%%EOF"""
            
            # Extract filename from URL
            filename = pdf_url.split('/')[-1]
            if not filename.endswith('.pdf'):
                filename = 'court_document.pdf'
            
            logger.info(f"MockCourtScraper: Creating PDF response with filename: {filename}")
            
            # Return a dictionary with PDF data instead of Flask Response
            return {
                'content': mock_pdf_content,
                'filename': filename,
                'mimetype': 'application/pdf'
            }
            
        except Exception as e:
            logger.error(f"Error generating mock PDF: {str(e)}")
            return None