from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import json
import logging
import traceback
from live_scraper import ProductionCourtScraper
from live_scraper import DelhiHighCourtLiveScraper
from enhanced_scraper import EnhancedDelhiHighCourtScraper
from models import db, CaseQuery, CaseData

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///court_data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize court scraper
# Set use_live_scraping=True for production, False for demo
USE_LIVE_SCRAPING = os.getenv('USE_LIVE_SCRAPING', 'false').lower() == 'true'
court_scraper = ProductionCourtScraper(use_live_scraping=USE_LIVE_SCRAPING)

# Initialize live scraper for dropdown data
live_scraper = DelhiHighCourtLiveScraper(headless=True, show_browser=False)
enhanced_scraper = EnhancedDelhiHighCourtScraper(headless=True, show_browser=False)

@app.route('/')
def index():
    """Main page with case search form"""
    # Get dropdown options from live scraper
    case_types = live_scraper.get_case_types()
    years = live_scraper.get_years()
    
    return render_template('index.html', case_types=case_types, years=years)

@app.route('/search', methods=['POST'])
def search_case():
    """Handle case search request"""
    try:
        case_type = request.form.get('case_type')
        case_number = request.form.get('case_number')
        filing_year = request.form.get('filing_year')
        
        if not all([case_type, case_number, filing_year]):
            flash('All fields are required', 'error')
            return redirect(url_for('index'))
        
        # Log the query
        query = CaseQuery(
            case_type=case_type,
            case_number=case_number,
            filing_year=filing_year,
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(query)
        db.session.commit()
        
        # Use enhanced scraper for faster, more reliable results
        logger.info(f"🚀 Enhanced search: {case_type} {case_number}/{filing_year}")
        
        search_result = enhanced_scraper.fast_search_case(case_type, case_number, filing_year)
        
        if not search_result.get('success'):
            error_msg = search_result.get('message', 'Search failed')
            error_type = search_result.get('error', 'unknown')
            
            logger.warning(f"❌ Search failed: {error_type} - {error_msg}")
            
            if error_type == 'no_data_found':
                flash(f'❌ No case found for {case_type} {case_number}/{filing_year}. Please verify the case details.', 'warning')
            elif error_type == 'captcha_failed':
                flash('🔄 CAPTCHA verification failed. Please try again.', 'error')
            elif error_type == 'max_retries_exceeded':
                flash('⏰ Search failed after multiple attempts. Please try again in a few minutes.', 'error')
            else:
                flash(f'❌ Search error: {error_msg}', 'error')
            
            return redirect(url_for('index'))
        
        case_data = search_result.get('case_data')
        logger.info(f"✅ Enhanced scraper returned: {type(case_data)}")
        
        # Log the actual case count from scraper
        if case_data:
            actual_count = case_data.get('total_cases', 0)
            logger.info(f"✅ Enhanced scraper found {actual_count} case(s)")
        else:
            logger.info("❌ No case data returned from scraper")
        
        if case_data and case_data.get('total_cases', 0) > 0:
            # Store case data in new format
            case_record = CaseData(
                query_id=query.id,
                case_type=case_type,
                case_number=case_number,
                filing_year=filing_year,
                parties=json.dumps([]),  # Will be populated from cases
                filing_date=None,
                next_hearing_date=None,
                orders_judgments=json.dumps([]),  # Will be populated from cases
                raw_response=case_data.get('raw_html', ''),
                status='Multiple Cases' if case_data.get('total_cases', 0) > 1 else case_data.get('cases', [{}])[0].get('status', 'Unknown')
            )
            db.session.add(case_record)
            db.session.commit()
            
            # Create search query object for template
            search_query = {
                'case_type': case_type,
                'case_number': case_number,
                'filing_year': filing_year
            }
            
            return render_template('case_results.html', 
                                 case_data=case_data, 
                                 search_query=search_query,
                                 case_id=case_record.id)
        else:
            # Safety net: Case not found - show helpful error message
            logger.warning(f"❌ No case data found for {case_type} {case_number}/{filing_year}")
            flash(f'❌ No case found for {case_type} {case_number}/{filing_year}. Please verify the case details.', 'warning')
            return redirect(url_for('index'))
            
    except Exception as e:
        logger.error(f"Error searching case: {str(e)}")
        flash('An error occurred while searching for the case. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/download_pdf/<int:case_id>/<int:order_index>')
def download_pdf(case_id, order_index):
    """Download PDF for a specific order/judgment"""
    try:
        logger.info(f"PDF download requested: case_id={case_id}, order_index={order_index}")
        
        case_record = db.session.get(CaseData, case_id)
        if not case_record:
            logger.error(f"Case not found: {case_id}")
            flash('Case not found', 'error')
            return redirect(url_for('index'))
            
        orders = json.loads(case_record.orders_judgments)
        logger.info(f"Found {len(orders)} orders for case {case_id}")
        
        if order_index < len(orders):
            order = orders[order_index]
            pdf_url = order.get('pdf_link')
            logger.info(f"Order {order_index}: {order.get('description', 'No description')}")
            logger.info(f"PDF URL: {pdf_url}")
            
            if pdf_url:
                logger.info(f"Attempting to download PDF from: {pdf_url}")
                pdf_data = court_scraper.download_pdf(pdf_url)
                if pdf_data and isinstance(pdf_data, dict):
                    logger.info("PDF generated successfully")
                    return Response(
                        pdf_data['content'],
                        mimetype=pdf_data['mimetype'],
                        headers={'Content-Disposition': f'attachment; filename={pdf_data["filename"]}'}
                    )
                else:
                    logger.error("PDF generation returned None or invalid format")
                    flash('Error generating PDF', 'error')
                    return redirect(url_for('case_details', case_id=case_id))
            else:
                logger.warning(f"No PDF link for order {order_index}")
                flash('PDF not available for this order', 'error')
                return redirect(url_for('case_details', case_id=case_id))
        else:
            logger.error(f"Order index {order_index} out of range (max: {len(orders)-1})")
            flash('Order not found', 'error')
            return redirect(url_for('case_details', case_id=case_id))
        
    except Exception as e:
        logger.error(f"Error downloading PDF: {str(e)}", exc_info=True)
        flash('Error downloading PDF', 'error')
        return redirect(url_for('index'))

@app.route('/case/<int:case_id>')
def case_details(case_id):
    """Display case details"""
    case_record = db.session.get(CaseData, case_id)
    if not case_record:
        flash('Case not found', 'error')
        return redirect(url_for('index'))
    
    # Parse case data
    case_data = {
        'case_type': case_record.case_type,
        'case_number': case_record.case_number,
        'filing_year': case_record.filing_year,
        'parties': json.loads(case_record.parties),
        'filing_date': case_record.filing_date,
        'next_hearing_date': case_record.next_hearing_date,
        'orders_judgments': json.loads(case_record.orders_judgments),
        'status': case_record.status
    }
    
    return render_template('case_details.html', case_data=case_data, case_id=case_id)

@app.route('/history')
def search_history():
    """Display search history"""
    queries = CaseQuery.query.order_by(CaseQuery.timestamp.desc()).limit(50).all()
    return render_template('history.html', queries=queries)

@app.route('/test_pdf')
def test_pdf():
    """Test PDF generation directly"""
    try:
        test_url = "https://delhihighcourt.nic.in/orders/test_document.pdf"
        pdf_data = court_scraper.download_pdf(test_url)
        if pdf_data and isinstance(pdf_data, dict):
            return Response(
                pdf_data['content'],
                mimetype=pdf_data['mimetype'],
                headers={'Content-Disposition': f'attachment; filename={pdf_data["filename"]}'}
            )
        else:
            return "PDF generation failed", 500
    except Exception as e:
        logger.error(f"Test PDF error: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/api/case/<int:case_id>')
def api_case_data(case_id):
    """API endpoint to get case data as JSON"""
    case_record = db.session.get(CaseData, case_id)
    if not case_record:
        return jsonify({'error': 'Case not found'}), 404
        
    return jsonify({
        'case_type': case_record.case_type,
        'case_number': case_record.case_number,
        'filing_year': case_record.filing_year,
        'parties': json.loads(case_record.parties),
        'filing_date': case_record.filing_date,
        'next_hearing_date': case_record.next_hearing_date,
        'orders_judgments': json.loads(case_record.orders_judgments),
        'status': case_record.status
    })

@app.route('/api/case-types')
def api_case_types():
    """API endpoint to get available case types"""
    try:
        case_types = live_scraper.get_case_types()
        return jsonify({
            'success': True,
            'case_types': case_types,
            'count': len(case_types)
        })
    except Exception as e:
        logger.error(f"Error getting case types: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load case types'
        }), 500

@app.route('/api/years')
def api_years():
    """API endpoint to get available years"""
    try:
        years = live_scraper.get_years()
        return jsonify({
            'success': True,
            'years': years,
            'count': len(years)
        })
    except Exception as e:
        logger.error(f"Error getting years: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load years'
        }), 500

@app.route('/debug/test-scraper')
def debug_test_scraper():
    """Debug endpoint to test scraper directly"""
    try:
        # Test with known working case
        case_type = request.args.get('case_type', 'W.P.(C)')
        case_number = request.args.get('case_number', '1')
        filing_year = request.args.get('filing_year', '2024')
        
        logger.info(f"Debug test: {case_type} {case_number}/{filing_year}")
        
        # Test scraper directly
        case_data = live_scraper.scrape_case_data(case_type, case_number, filing_year)
        
        return jsonify({
            'success': True,
            'test_params': {
                'case_type': case_type,
                'case_number': case_number,
                'filing_year': filing_year
            },
            'case_data': case_data,
            'total_cases': case_data.get('total_cases', 0) if case_data else 0,
            'scraper_config': {
                'headless': live_scraper.headless,
                'show_browser': live_scraper.show_browser,
                'base_url': live_scraper.base_url
            }
        })
        
    except Exception as e:
        logger.error(f"Debug test error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        })

@app.route('/debug/test-enhanced-scraper')
def debug_test_enhanced_scraper():
    """Debug endpoint to test enhanced scraper with no data found scenario"""
    try:
        # Test with case that likely doesn't exist
        case_type = request.args.get('case_type', 'C.A.(COMM.IPD-PV)')
        case_number = request.args.get('case_number', '1')
        filing_year = request.args.get('filing_year', '2020')
        
        logger.info(f"Enhanced scraper test: {case_type} {case_number}/{filing_year}")
        
        # Test enhanced scraper directly
        search_result = enhanced_scraper.fast_search_case(case_type, case_number, filing_year)
        
        return jsonify({
            'test_params': {
                'case_type': case_type,
                'case_number': case_number,
                'filing_year': filing_year
            },
            'search_result': search_result,
            'scraper_config': {
                'headless': enhanced_scraper.headless,
                'show_browser': enhanced_scraper.show_browser,
                'base_url': enhanced_scraper.base_url
            }
        })
        
    except Exception as e:
        logger.error(f"Enhanced scraper test error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        })

@app.route('/debug/simple-search', methods=['POST'])
def debug_simple_search():
    """Simplified search route for debugging"""
    try:
        case_type = request.form.get('case_type', 'W.P.(C)')
        case_number = request.form.get('case_number', '1')
        filing_year = request.form.get('filing_year', '2024')
        
        logger.info(f"Simple search: {case_type} {case_number}/{filing_year}")
        
        # Test scraper
        case_data = live_scraper.scrape_case_data(case_type, case_number, filing_year)
        
        logger.info(f"Simple search result: {type(case_data)}")
        if case_data:
            logger.info(f"Total cases: {case_data.get('total_cases', 0)}")
        
        # Skip database operations for now
        if case_data and case_data.get('total_cases', 0) > 0:
            search_query = {
                'case_type': case_type,
                'case_number': case_number,
                'filing_year': filing_year
            }
            
            logger.info("Rendering case_results.html template")
            return render_template('case_results.html', 
                                 case_data=case_data, 
                                 search_query=search_query,
                                 case_id=0)  # Dummy case_id
        else:
            logger.warning("No case data found")
            return f"<h1>Debug: No case data found</h1><p>case_data: {case_data}</p>"
            
    except Exception as e:
        logger.error(f"Simple search error: {str(e)}", exc_info=True)
        return f"<h1>Debug Error</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>"

@app.route('/debug/pdf-url/<path:pdf_url>')
def debug_pdf_url(pdf_url):
    """Debug PDF URL reception"""
    try:
        import urllib.parse
        decoded_url = urllib.parse.unquote(urllib.parse.unquote(pdf_url))
        
        return f"""
        <h1>PDF URL Debug</h1>
        <p><strong>Raw URL:</strong> {pdf_url}</p>
        <p><strong>Decoded URL:</strong> {decoded_url}</p>
        <p><strong>URL Length:</strong> {len(pdf_url)}</p>
        <p><strong>Decoded Length:</strong> {len(decoded_url)}</p>
        <p><strong>Starts with Delhi HC:</strong> {decoded_url.startswith('https://delhihighcourt.nic.in')}</p>
        """
    except Exception as e:
        return f"<h1>Debug Error</h1><p>{str(e)}</p>"

@app.route('/orders/<path:orders_url>')
def view_orders(orders_url):
    """View orders for a specific case"""
    try:
        logger.info(f"Viewing orders: {orders_url}")
        
        # Decode the URL (it comes double-encoded from the template)
        import urllib.parse
        decoded_url = urllib.parse.unquote(urllib.parse.unquote(orders_url))
        logger.info(f"Decoded URL: {decoded_url}")
        
        # Ensure it's a valid Delhi High Court URL
        if not decoded_url.startswith('https://delhihighcourt.nic.in'):
            logger.error(f"Invalid URL: {decoded_url}")
            flash('Invalid orders URL', 'error')
            return redirect(url_for('index'))
        
        logger.info("Starting orders scraping...")
        # Use global scraper instance for better performance (reuses driver session)
        orders_data = live_scraper.scrape_orders_page(decoded_url)
        
        logger.info(f"Orders data received: {type(orders_data)}")
        if orders_data:
            logger.info(f"Total orders: {orders_data.get('total_orders', 0)}")
            logger.info(f"Has error: {orders_data.get('error', 'No error')}")
        
        if orders_data and orders_data.get('total_orders', 0) > 0:
            logger.info("Rendering orders template")
            return render_template('orders.html', 
                                 orders_data=orders_data,
                                 orders_url=decoded_url)
        else:
            error_msg = orders_data.get('error', 'No orders found') if orders_data else 'Scraper returned None'
            logger.warning(f"No orders found: {error_msg}")
            flash(f'No orders found for this case. {error_msg}', 'warning')
            return redirect(url_for('index'))
            
    except Exception as e:
        logger.error(f"Error viewing orders: {str(e)}", exc_info=True)
        flash('Error loading orders. Please try again.', 'error')
        return redirect(url_for('index'))



@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('error.html', error_message="Internal server error"), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)