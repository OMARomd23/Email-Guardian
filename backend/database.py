import sqlite3
import json
import logging
import hashlib
import uuid
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Enhanced SQLite database manager for email scan results and user management
    """
    
    def __init__(self, db_path: str = "email_guardian.db"):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT UNIQUE NOT NULL,
                        hashed_password TEXT NOT NULL,
                        api_key TEXT UNIQUE NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_login DATETIME
                    )
                ''')
                
                # Create scans table with user_id reference
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        text TEXT NOT NULL,
                        classification TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        probabilities TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        ip_address TEXT,
                        user_agent TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # Create indexes for faster queries
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_users_email 
                    ON users(email)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_users_api_key 
                    ON users(api_key)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_scans_timestamp 
                    ON scans(timestamp DESC)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_scans_classification 
                    ON scans(classification)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_scans_user_id 
                    ON scans(user_id)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_scans_user_timestamp 
                    ON scans(user_id, timestamp DESC)
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def _hash_password(self, password: str) -> str:
        """
        Hash password using SHA-256
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def _generate_api_key(self) -> str:
        """
        Generate a unique API key
        
        Returns:
            Unique 32-character hex API key
        """
        return uuid.uuid4().hex
    
    def _validate_email(self, email: str) -> bool:
        """
        Validate email format
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid email format
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def register_user(self, email: str, password: str) -> Tuple[bool, str, Optional[str]]:
        """
        Register a new user with validation and unique API key generation
        
        Args:
            email: User email address
            password: Plain text password
            
        Returns:
            Tuple of (success, message, api_key)
        """
        try:
            # Validate input
            if not email or not password:
                return False, "Email and password are required", None
            
            email = email.strip().lower()
            
            if not self._validate_email(email):
                return False, "Invalid email format", None
            
            if len(password) < 6:
                return False, "Password must be at least 6 characters long", None
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if user already exists
                cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
                if cursor.fetchone():
                    return False, "User with this email already exists", None
                
                # Hash password and generate unique API key
                hashed_password = self._hash_password(password)
                
                # Ensure API key is unique (collision detection)
                max_attempts = 10
                for attempt in range(max_attempts):
                    api_key = self._generate_api_key()
                    cursor.execute('SELECT id FROM users WHERE api_key = ?', (api_key,))
                    if not cursor.fetchone():
                        break
                    if attempt == max_attempts - 1:
                        return False, "Failed to generate unique API key", None
                
                # Insert new user
                cursor.execute('''
                    INSERT INTO users (email, hashed_password, api_key, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (email, hashed_password, api_key, datetime.utcnow().isoformat()))
                
                conn.commit()
                user_id = cursor.lastrowid
                
                logger.info(f"User registered successfully: {email} (ID: {user_id})")
                return True, "User registered successfully", api_key
                
        except Exception as e:
            logger.error(f"Failed to register user: {str(e)}")
            return False, "Registration failed due to server error", None
    
    def authenticate_user(self, email: str, password: str) -> Tuple[bool, str, Optional[str]]:
        """
        Authenticate user and return API key
        
        Args:
            email: User email address
            password: Plain text password
            
        Returns:
            Tuple of (success, message, api_key)
        """
        try:
            if not email or not password:
                return False, "Email and password are required", None
                
            email = email.strip().lower()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get user by email
                cursor.execute('''
                    SELECT id, hashed_password, api_key 
                    FROM users 
                    WHERE email = ?
                ''', (email,))
                
                user = cursor.fetchone()
                if not user:
                    return False, "Invalid email or password", None
                
                # Verify password
                hashed_password = self._hash_password(password)
                if user['hashed_password'] != hashed_password:
                    return False, "Invalid email or password", None
                
                # Update last login
                cursor.execute('''
                    UPDATE users 
                    SET last_login = ? 
                    WHERE id = ?
                ''', (datetime.utcnow().isoformat(), user['id']))
                
                conn.commit()
                
                logger.info(f"User authenticated successfully: {email}")
                return True, "Login successful", user['api_key']
                
        except Exception as e:
            logger.error(f"Failed to authenticate user: {str(e)}")
            return False, "Authentication failed due to server error", None
    
    def is_valid_api_key(self, api_key: str) -> bool:
        """
        Check if an API key is valid
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not api_key or len(api_key) != 32:  # UUID4 hex is 32 chars
                return False
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT id FROM users WHERE api_key = ?', (api_key,))
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Failed to validate API key: {str(e)}")
            return False
    
    def get_user_id_by_api_key(self, api_key: str) -> Optional[int]:
        """
        Get user ID by API key
        
        Args:
            api_key: API key
            
        Returns:
            User ID or None if not found
        """
        try:
            if not api_key:
                return None
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT id FROM users WHERE api_key = ?', (api_key,))
                result = cursor.fetchone()
                return result['id'] if result else None
                
        except Exception as e:
            logger.error(f"Failed to get user ID by API key: {str(e)}")
            return None
    
    def get_user_email_by_api_key(self, api_key: str) -> Optional[str]:
        """
        Get user email by API key
        
        Args:
            api_key: API key
            
        Returns:
            User email or None if not found
        """
        try:
            if not api_key:
                return None
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT email FROM users WHERE api_key = ?', (api_key,))
                result = cursor.fetchone()
                return result['email'] if result else None
                
        except Exception as e:
            logger.error(f"Failed to get user email by API key: {str(e)}")
            return None
    
    def store_scan_result(self, text: str, classification: str, confidence: float, 
                         probabilities: Dict, api_key: str, ip_address: str = None, 
                         user_agent: str = None) -> int:
        """
        Store a scan result in the database with user isolation
        
        Args:
            text: Email text that was scanned
            classification: Classification result
            confidence: Confidence score
            probabilities: Dictionary of class probabilities
            api_key: User's API key
            ip_address: Client IP address (optional)
            user_agent: Client user agent (optional)
            
        Returns:
            ID of the inserted record
        """
        try:
            user_id = self.get_user_id_by_api_key(api_key)
            if not user_id:
                raise ValueError("Invalid API key - user not found")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO scans (user_id, text, classification, confidence, probabilities, 
                                     ip_address, user_agent, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    text,
                    classification,
                    confidence,
                    json.dumps(probabilities),
                    ip_address,
                    user_agent,
                    datetime.utcnow().isoformat()
                ))
                
                conn.commit()
                record_id = cursor.lastrowid
                
                logger.info(f"Stored scan result with ID: {record_id} for user: {user_id}")
                return record_id
                
        except Exception as e:
            logger.error(f"Failed to store scan result: {str(e)}")
            raise
    
    def get_scan_history(self, api_key: str, limit: int = 10, offset: int = 0) -> List[Dict]:
        """
        Retrieve recent scan history for a user (with user data isolation)
        
        Args:
            api_key: User's API key
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of scan records for the authenticated user only
        """
        try:
            user_id = self.get_user_id_by_api_key(api_key)
            if not user_id:
                return []
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, text, classification, confidence, probabilities, timestamp
                    FROM scans
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                ''', (user_id, limit, offset))
                
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    result = {
                        'id': row['id'],
                        'text': row['text'][:100] + '...' if len(row['text']) > 100 else row['text'],
                        'full_text': row['text'],  # Include full text for detailed view
                        'classification': row['classification'],
                        'confidence': row['confidence'],
                        'probabilities': json.loads(row['probabilities']),
                        'timestamp': row['timestamp']
                    }
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"Failed to get scan history: {str(e)}")
            return []
    
    def get_scan_by_id(self, scan_id: int, api_key: str) -> Optional[Dict]:
        """
        Retrieve a specific scan by ID for a user (with user data isolation)
        
        Args:
            scan_id: ID of the scan to retrieve
            api_key: User's API key
            
        Returns:
            Scan record or None if not found or not owned by user
        """
        try:
            user_id = self.get_user_id_by_api_key(api_key)
            if not user_id:
                return None
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM scans 
                    WHERE id = ? AND user_id = ?
                ''', (scan_id, user_id))
                
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row['id'],
                        'text': row['text'],
                        'classification': row['classification'],
                        'confidence': row['confidence'],
                        'probabilities': json.loads(row['probabilities']),
                        'timestamp': row['timestamp'],
                        'ip_address': row['ip_address'],
                        'user_agent': row['user_agent']
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get scan by ID: {str(e)}")
            return None
    
    def get_classification_stats(self, api_key: str, days: int = 30) -> Dict:
        """
        Get classification statistics for a user (with user data isolation)
        
        Args:
            api_key: User's API key
            days: Number of days to look back for statistics
            
        Returns:
            Dictionary with statistics for the authenticated user only
        """
        try:
            user_id = self.get_user_id_by_api_key(api_key)
            if not user_id:
                return {
                    'total_scans': 0,
                    'classification_counts': {},
                    'average_confidence': {},
                    'daily_activity': [],
                    'period_days': days
                }
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total counts by classification
                cursor.execute('''
                    SELECT classification, COUNT(*) as count
                    FROM scans
                    WHERE user_id = ? AND timestamp >= datetime('now', '-' || ? || ' days')
                    GROUP BY classification
                    ORDER BY count DESC
                ''', (user_id, days))
                
                classification_counts = {}
                total_scans = 0
                
                for row in cursor.fetchall():
                    classification_counts[row['classification']] = row['count']
                    total_scans += row['count']
                
                # Get average confidence by classification
                cursor.execute('''
                    SELECT classification, AVG(confidence) as avg_confidence
                    FROM scans
                    WHERE user_id = ? AND timestamp >= datetime('now', '-' || ? || ' days')
                    GROUP BY classification
                ''', (user_id, days))
                
                avg_confidence = {}
                for row in cursor.fetchall():
                    avg_confidence[row['classification']] = round(row['avg_confidence'], 4)
                
                # Get recent activity (scans per day for last 7 days)
                cursor.execute('''
                    SELECT DATE(timestamp) as scan_date, COUNT(*) as count
                    FROM scans
                    WHERE user_id = ? AND timestamp >= datetime('now', '-7 days')
                    GROUP BY DATE(timestamp)
                    ORDER BY scan_date DESC
                ''', (user_id,))
                
                daily_activity = []
                for row in cursor.fetchall():
                    daily_activity.append({
                        'date': row['scan_date'],
                        'count': row['count']
                    })
                
                return {
                    'total_scans': total_scans,
                    'classification_counts': classification_counts,
                    'average_confidence': avg_confidence,
                    'daily_activity': daily_activity,
                    'period_days': days
                }
                
        except Exception as e:
            logger.error(f"Failed to get classification stats: {str(e)}")
            return {
                'total_scans': 0,
                'classification_counts': {},
                'average_confidence': {},
                'daily_activity': [],
                'period_days': days
            }
    
    def delete_old_scans(self, api_key: str, days: int = 90) -> int:
        """
        Delete scans older than specified days for a user (with user data isolation)
        
        Args:
            api_key: User's API key
            days: Number of days to keep
            
        Returns:
            Number of deleted records
        """
        try:
            user_id = self.get_user_id_by_api_key(api_key)
            if not user_id:
                return 0
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM scans
                    WHERE user_id = ? AND timestamp < datetime('now', '-' || ? || ' days')
                ''', (user_id, days))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Deleted {deleted_count} old scan records for user: {user_id}")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to delete old scans: {str(e)}")
            return 0
    
    def delete_scan_by_id(self, scan_id: int, api_key: str) -> bool:
        """
        Delete a specific scan by ID for a user (with user data isolation)
        
        Args:
            scan_id: ID of the scan to delete
            api_key: User's API key
            
        Returns:
            True if deleted, False if not found or not owned by user
        """
        try:
            user_id = self.get_user_id_by_api_key(api_key)
            if not user_id:
                return False
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM scans 
                    WHERE id = ? AND user_id = ?
                ''', (scan_id, user_id))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Deleted scan {scan_id} for user {user_id}")
                    return True
                else:
                    logger.warning(f"Scan {scan_id} not found or not owned by user {user_id}")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to delete scan by ID: {str(e)}")
            return False
    
    def get_database_info(self) -> Dict:
        """
        Get database information and statistics (admin view)
        
        Returns:
            Dictionary with database information
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total record counts
                cursor.execute('SELECT COUNT(*) FROM scans')
                total_scans = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM users')
                total_users = cursor.fetchone()[0]
                
                # Get database size
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                # Get oldest and newest records
                cursor.execute('''
                    SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest
                    FROM scans
                ''')
                
                date_range = cursor.fetchone()
                
                # Get user registration dates
                cursor.execute('''
                    SELECT MIN(created_at) as first_user, MAX(created_at) as latest_user
                    FROM users
                ''')
                
                user_range = cursor.fetchone()
                
                return {
                    'database_path': self.db_path,
                    'total_scans': total_scans,
                    'total_users': total_users,
                    'database_size_bytes': db_size,
                    'database_size_mb': round(db_size / (1024 * 1024), 2),
                    'oldest_scan': date_range['oldest'] if date_range else None,
                    'newest_scan': date_range['newest'] if date_range else None,
                    'first_user_registered': user_range['first_user'] if user_range else None,
                    'latest_user_registered': user_range['latest_user'] if user_range else None,
                    'multi_user_enabled': True,
                    'schema_version': '2.0'
                }
                
        except Exception as e:
            logger.error(f"Failed to get database info: {str(e)}")
            return {}

def init_db(db_path: str = "email_guardian.db"):
    """
    Initialize the database (convenience function)
    
    Args:
        db_path: Path to the database file
    """
    db_manager = DatabaseManager(db_path)
    logger.info(f"Multi-user database initialized at: {db_path}")
    return db_manager
