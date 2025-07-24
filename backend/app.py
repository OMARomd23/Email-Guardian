from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from datetime import datetime
import logging
from functools import wraps
from dotenv import load_dotenv
 
# Load environment variables
load_dotenv()

from model_handler import EmailClassifier
from database import DatabaseManager, init_db
from groq_validator import GroqEmailValidator

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)
limiter.init_app(app)

# Configuration
API_KEY = os.environ.get('API_KEY', 'your_api_key')
MODEL_PATH = os.environ.get('MODEL_PATH', './my-3class-model')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'email_guardian.db')

# Initialize components
db_manager = DatabaseManager(DATABASE_PATH)
email_classifier = None
groq_validator = None

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not api_key:
            logger.warning(f"API request without key from {request.remote_addr}")
            return jsonify({'error': 'API key required'}), 401
        
        if api_key != API_KEY:
            logger.warning(f"Invalid API key attempt from {request.remote_addr}")
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def validate_input(data):
    """Validate input data for scan endpoint"""
    if not data:
        return False, "No data provided"
    
    if 'text' not in data:
        return False, "Missing 'text' field"
    
    text = data['text']
    if not isinstance(text, str):
        return False, "'text' must be a string"
    
    if not text.strip():
        return False, "'text' cannot be empty"
    
    if len(text) > 10000:  # Reasonable limit
        return False, "'text' too long (max 10,000 characters)"
    
    return True, None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        groq_status = groq_validator.test_connection() if groq_validator else {'success': False, 'error': 'Not configured'}
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'model_loaded': email_classifier is not None,
            'groq_validator': groq_status['success'],
            'groq_model': groq_status.get('model', 'N/A') if groq_status['success'] else 'Not configured',
            'database_status': 'connected',
            'api_version': '1.0.0'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@app.route('/api/scan', methods=['POST'])
@limiter.limit("20 per minute")
@require_api_key
def scan_email():
    """Main endpoint to classify emails"""
    try:
        # Validate request
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        is_valid, error_msg = validate_input(data)
        
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        text = data['text'].strip()
        
        # Get LLM validation preference (default to True if not specified)
        use_llm_validation = data.get('use_llm_validation', True)
        
        # Classify email with primary classifier
        if email_classifier is None:
            logger.error("Model not loaded when scan requested")
            return jsonify({'error': 'Model not loaded'}), 500
        
        logger.info(f"Classifying email of length {len(text)} characters")
        result = email_classifier.classify(text)
        
        # Apply LLM validation if enabled and available
        if use_llm_validation and groq_validator and groq_validator.enabled:
            try:
                logger.info("Applying LLM validation")
                result = groq_validator.validate_classification(text, result)
                logger.info(f"LLM validation completed for classification: {result['classification']}")
            except Exception as e:
                logger.warning(f"LLM validation failed, using primary result: {e}")
                result['llm_validation'] = {
                    'enabled': False,
                    'error': f"Validation failed: {str(e)}"
                }
        elif use_llm_validation:
            result['llm_validation'] = {
                'enabled': False,
                'reason': 'Groq validator not available or not configured'
            }
        
        # Store result in database
        try:
            db_manager.store_scan_result(
                text=text,
                classification=result['classification'],
                confidence=result['confidence'],
                probabilities=result['probabilities'],
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
        except Exception as e:
            logger.error(f"Failed to store scan result: {e}")
            # Don't fail the request if database storage fails
        
        logger.info(f"Email classified as: {result['classification']} (confidence: {result['confidence']:.2f})")
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in scan_email: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/history', methods=['GET'])
@require_api_key
def get_history():
    """Get recent scan history"""
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(max(1, limit), 100)  # Ensure limit is between 1-100
        
        offset = request.args.get('offset', 0, type=int)
        offset = max(0, offset)  # Ensure offset is non-negative
        
        history = db_manager.get_scan_history(limit=limit, offset=offset)
        
        return jsonify({
            'history': history,
            'count': len(history),
            'limit': limit,
            'offset': offset
        })
    
    except Exception as e:
        logger.error(f"Error in get_history: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/stats', methods=['GET'])
@require_api_key
def get_stats():
    """Get classification statistics"""
    try:
        days = request.args.get('days', 30, type=int)
        days = min(max(1, days), 365)  # Ensure days is between 1-365
        
        stats = db_manager.get_classification_stats(days=days)
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"Error in get_stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/scan/<int:scan_id>', methods=['GET'])
@require_api_key
def get_scan_details(scan_id):
    """Get details of a specific scan"""
    try:
        scan = db_manager.get_scan_by_id(scan_id)
        
        if scan is None:
            return jsonify({'error': 'Scan not found'}), 404
        
        return jsonify(scan)
    
    except Exception as e:
        logger.error(f"Error getting scan details: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/groq-test', methods=['GET'])
@require_api_key
def test_groq():
    """Test Groq LLM connection"""
    try:
        if not groq_validator:
            return jsonify({
                'success': False,
                'error': 'Groq validator not initialized - check GROQ_API_KEY environment variable'
            })
        
        result = groq_validator.test_connection()
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error testing Groq connection: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Test failed: {str(e)}'
        }), 500

@app.route('/api/database-info', methods=['GET'])
@require_api_key
def get_database_info():
    """Get database information and statistics"""
    try:
        info = db_manager.get_database_info()
        return jsonify(info)
    
    except Exception as e:
        logger.error(f"Error getting database info: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cleanup', methods=['POST'])
@require_api_key
def cleanup_database():
    """Clean up old scan records"""
    try:
        data = request.get_json() or {}
        days = data.get('days', 90)
        days = min(max(1, days), 365)  # Ensure days is between 1-365
        
        deleted_count = db_manager.delete_old_scans(days=days)
        
        return jsonify({
            'success': True,
            'deleted_records': deleted_count,
            'retention_days': days
        })
    
    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded"""
    logger.warning(f"Rate limit exceeded for {request.remote_addr}")
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    """Handle method not allowed errors"""
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

def initialize_app():
    """Initialize the application components"""
    global email_classifier, groq_validator
    
    try:
        logger.info("Initializing Email Guardian backend...")
        
        # Initialize database
        init_db(DATABASE_PATH)
        logger.info("Database initialized successfully")
        
        # Load ML model
        logger.info(f"Loading ML model from: {MODEL_PATH}")
        email_classifier = EmailClassifier(MODEL_PATH)
        logger.info("Email classifier loaded successfully")
        
        # Initialize Groq validator
        if GROQ_API_KEY:
            logger.info("Initializing Groq LLM validator...")
            try:
                groq_validator = GroqEmailValidator(GROQ_API_KEY)
                if groq_validator.enabled:
                    logger.info("Groq LLM validator initialized successfully")
                else:
                    logger.warning("Groq LLM validator failed to initialize")
            except Exception as e:
                logger.error(f"Failed to initialize Groq validator: {e}")
                groq_validator = None
        else:
            logger.info("Groq API key not provided - LLM validation disabled")
            groq_validator = None
        
        logger.info("Email Guardian backend initialized successfully!")
        
    except Exception as e:
        logger.error(f"Failed to initialize app: {str(e)}")
        raise

def create_app():
    """Application factory function"""
    initialize_app()
    return app

if __name__ == '__main__':
    # Initialize components
    initialize_app()
    
    # Get configuration from environment
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    host = '0.0.0.0' if not debug else '127.0.0.1'
    
    logger.info(f"Starting Email Guardian backend on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"API Key configured: {'Yes' if API_KEY != 'your-api-key' else 'No (using default)'}")
    logger.info(f"Groq integration: {'Enabled' if groq_validator and groq_validator.enabled else 'Disabled'}")
    
    # Run the app
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )
