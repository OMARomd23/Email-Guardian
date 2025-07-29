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

# Rate limiting with enhanced multi-user support
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    storage_uri="memory://"
)
limiter.init_app(app)

# Configuration
MODEL_PATH = os.environ.get('MODEL_PATH', './my-3class-model')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'email_guardian.db')

# Initialize components
db_manager = DatabaseManager(DATABASE_PATH)
email_classifier = None
groq_validator = None

def require_api_key(f):
    """Enhanced decorator to require API key authentication with database validation"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract API key from headers (support both Bearer and X-API-Key)
        auth_header = request.headers.get('Authorization', '')
        api_key = None
        
        if auth_header.startswith('Bearer '):
            api_key = auth_header[7:]  # Remove 'Bearer ' prefix
        else:
            api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            logger.warning(f"API request without key from {request.remote_addr}")
            return jsonify({'error': 'API key required'}), 401
        
        # Validate API key against database
        if not db_manager.is_valid_api_key(api_key):
            logger.warning(f"Invalid API key attempt from {request.remote_addr}: {api_key[:8]}...")
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Store API key in request context for use in route functions
        request.api_key = api_key
        request.user_id = db_manager.get_user_id_by_api_key(api_key)
        request.user_email = db_manager.get_user_email_by_api_key(api_key)
        
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
    """Health check endpoint (public)"""
    try:
        groq_status = groq_validator.test_connection() if groq_validator else {'success': False, 'error': 'Not configured'}
        
        # Get database info without exposing sensitive data
        db_info = db_manager.get_database_info()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'model_loaded': email_classifier is not None,
            'groq_validator': groq_status['success'],
            'groq_model': groq_status.get('model', 'N/A') if groq_status['success'] else 'Not configured',
            'database_status': 'connected',
            'api_version': '2.0.0',
            'multi_user': True,
            'total_users': db_info.get('total_users', 0),
            'total_scans': db_info.get('total_scans', 0),
            'authentication': 'enabled'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e),
            'multi_user': True,
            'authentication': 'enabled'
        }), 500

@app.route('/api/register', methods=['POST'])
@limiter.limit("5 per minute")
def register_user():
    """User registration endpoint with enhanced validation"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Register user with enhanced validation
        success, message, api_key = db_manager.register_user(email, password)
        
        if success:
            logger.info(f"New user registered: {email} from {request.remote_addr}")
            return jsonify({
                'success': True,
                'message': message,
                'api_key': api_key,
                'email': email,
                'user_id': db_manager.get_user_id_by_api_key(api_key)
            })
        else:
            logger.warning(f"Registration failed for {email}: {message}")
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error in register_user: {str(e)}")
        return jsonify({'error': 'Registration failed due to server error'}), 500

@app.route('/api/login', methods=['POST'])
@limiter.limit("10 per minute")
def login_user():
    """User login endpoint with enhanced security"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Authenticate user
        success, message, api_key = db_manager.authenticate_user(email, password)
        
        if success:
            logger.info(f"User logged in: {email} from {request.remote_addr}")
            return jsonify({
                'success': True,
                'message': message,
                'api_key': api_key,
                'email': email,
                'user_id': db_manager.get_user_id_by_api_key(api_key)
            })
        else:
            logger.warning(f"Login failed for {email}: {message}")
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error in login_user: {str(e)}")
        return jsonify({'error': 'Login failed due to server error'}), 500

@app.route('/api/scan', methods=['POST'])
@limiter.limit("20 per minute")
@require_api_key
def scan_email():
    """Main endpoint to classify emails with user authentication"""
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
        
        logger.info(f"Classifying email of length {len(text)} characters for user {request.user_email}")
        result = email_classifier.classify(text)
        
        # Apply LLM validation if enabled and available
        if use_llm_validation and groq_validator and groq_validator.enabled:
            try:
                logger.info(f"Applying LLM validation for user {request.user_email}")
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
        
        # Store result in database with user's API key (user data isolation)
        try:
            scan_id = db_manager.store_scan_result(
                text=text,
                classification=result['classification'],
                confidence=result['confidence'],
                probabilities=result['probabilities'],
                api_key=request.api_key,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            result['scan_id'] = scan_id
        except Exception as e:
            logger.error(f"Failed to store scan result for user {request.user_email}: {e}")
            # Don't fail the request if database storage fails
        
        logger.info(f"Email classified as: {result['classification']} (confidence: {result['confidence']:.2f}) for user {request.user_email}")
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in scan_email for user {getattr(request, 'user_email', 'unknown')}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/history', methods=['GET'])
@require_api_key
def get_history():
    """Get recent scan history for authenticated user (with data isolation)"""
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(max(1, limit), 100)  # Ensure limit is between 1-100
        
        offset = request.args.get('offset', 0, type=int)
        offset = max(0, offset)  # Ensure offset is non-negative
        
        history = db_manager.get_scan_history(
            api_key=request.api_key,
            limit=limit,
            offset=offset
        )
        
        logger.info(f"Retrieved {len(history)} history records for user {request.user_email}")
        
        return jsonify({
            'history': history,
            'count': len(history),
            'limit': limit,
            'offset': offset,
            'user_email': request.user_email
        })
    
    except Exception as e:
        logger.error(f"Error in get_history for user {request.user_email}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/stats', methods=['GET'])
@require_api_key
def get_stats():
    """Get classification statistics for authenticated user (with data isolation)"""
    try:
        days = request.args.get('days', 30, type=int)
        days = min(max(1, days), 365)  # Ensure days is between 1-365
        
        stats = db_manager.get_classification_stats(
            api_key=request.api_key,
            days=days
        )
        
        logger.info(f"Retrieved stats for {days} days for user {request.user_email}")
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"Error in get_stats for user {request.user_email}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/scan/<int:scan_id>', methods=['GET'])
@require_api_key
def get_scan_details(scan_id):
    """Get details of a specific scan for authenticated user (with data isolation)"""
    try:
        scan = db_manager.get_scan_by_id(scan_id, request.api_key)
        
        if scan is None:
            return jsonify({'error': 'Scan not found or access denied'}), 404
        
        return jsonify(scan)
    
    except Exception as e:
        logger.error(f"Error getting scan details for user {request.user_email}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/scan/<int:scan_id>', methods=['DELETE'])
@require_api_key
def delete_scan(scan_id):
    """Delete a specific scan for authenticated user (with data isolation)"""
    try:
        success = db_manager.delete_scan_by_id(scan_id, request.api_key)
        
        if success:
            logger.info(f"Deleted scan {scan_id} for user {request.user_email}")
            return jsonify({'success': True, 'message': 'Scan deleted successfully'})
        else:
            return jsonify({'error': 'Scan not found or access denied'}), 404
    
    except Exception as e:
        logger.error(f"Error deleting scan for user {request.user_email}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/groq-test', methods=['GET'])
@require_api_key
def test_groq():
    """Test Groq LLM connection (authenticated users only)"""
    try:
        if not groq_validator:
            return jsonify({
                'success': False,
                'error': 'Groq validator not initialized - check GROQ_API_KEY environment variable'
            })
        
        result = groq_validator.test_connection()
        logger.info(f"Groq test performed by user {request.user_email}")
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error testing Groq connection for user {request.user_email}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Test failed: {str(e)}'
        }), 500

@app.route('/api/cleanup', methods=['POST'])
@require_api_key
def cleanup_database():
    """Clean up old scan records for authenticated user (with data isolation)"""
    try:
        data = request.get_json() or {}
        days = data.get('days', 90)
        days = min(max(1, days), 365)  # Ensure days is between 1-365
        
        deleted_count = db_manager.delete_old_scans(
            api_key=request.api_key,
            days=days
        )
        
        logger.info(f"Cleaned up {deleted_count} old records for user {request.user_email}")
        
        return jsonify({
            'success': True,
            'deleted_records': deleted_count,
            'retention_days': days
        })
    
    except Exception as e:
        logger.error(f"Error in cleanup for user {request.user_email}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/user/profile', methods=['GET'])
@require_api_key
def get_user_profile():
    """Get user profile information"""
    try:
        # Get basic user stats
        stats = db_manager.get_classification_stats(request.api_key, days=365)
        
        return jsonify({
            'user_id': request.user_id,
            'email': request.user_email,
            'total_scans_all_time': stats['total_scans'],
            'api_key_prefix': request.api_key[:8] + '...',
            'profile_type': 'authenticated_user'
        })
    
    except Exception as e:
        logger.error(f"Error getting user profile for {request.user_email}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/database-info', methods=['GET'])
@require_api_key
def get_database_info():
    """Get database information (limited to non-sensitive data for regular users)"""
    try:
        info = db_manager.get_database_info()
        
        # Return limited info for regular users
        public_info = {
            'database_status': 'connected',
            'api_version': '2.0.0',
            'multi_user_enabled': info.get('multi_user_enabled', True),
            'schema_version': info.get('schema_version', '2.0'),
            'your_total_scans': db_manager.get_classification_stats(request.api_key, days=365)['total_scans']
        }
        
        return jsonify(public_info)
    
    except Exception as e:
        logger.error(f"Error getting database info for user {request.user_email}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Enhanced rate limiting for auth endpoints
@app.route('/api/auth/rate-limit-info', methods=['GET'])
def get_rate_limit_info():
    """Get current rate limit information (public endpoint)"""
    return jsonify({
        'registration_limit': '5 per minute',
        'login_limit': '10 per minute', 
        'scan_limit': '20 per minute per user',
        'general_limit': '200 per hour',
        'multi_user': True
    })

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded with enhanced logging"""
    logger.warning(f"Rate limit exceeded for {request.remote_addr} on {request.endpoint}")
    return jsonify({
        'error': 'Rate limit exceeded. Please try again later.',
        'retry_after': '60 seconds',
        'endpoint': request.endpoint
    }), 429

@app.errorhandler(401)
def unauthorized_handler(e):
    """Handle unauthorized access attempts"""
    logger.warning(f"Unauthorized access attempt from {request.remote_addr} to {request.endpoint}")
    return jsonify({
        'error': 'Authentication required. Please provide a valid API key.',
        'authentication': 'required'
    }), 401

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
        logger.info("Initializing Email Guardian Multi-User backend...")
        
        # Initialize database with multi-user schema
        logger.info("Initializing multi-user database...")
        init_db(DATABASE_PATH)
        logger.info("Multi-user database initialized successfully")
        
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
        
        logger.info("Email Guardian Multi-User backend initialized successfully!")
        logger.info("🔐 Multi-user authentication: ENABLED")
        logger.info("🛡️ User data isolation: ENABLED")
        logger.info("🔑 Individual API keys: ENABLED")
        
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
    
    logger.info(f"Starting Email Guardian Multi-User backend on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Multi-user authentication: ENABLED")
    logger.info(f"Groq integration: {'ENABLED' if groq_validator and groq_validator.enabled else 'DISABLED'}")
    logger.info(f"Database: {DATABASE_PATH}")
    
    # Run the app
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )
