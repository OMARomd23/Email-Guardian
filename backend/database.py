import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Simple SQLite database manager for email scan results
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
                
                # Create scans table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        text TEXT NOT NULL,
                        classification TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        probabilities TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        ip_address TEXT,
                        user_agent TEXT
                    )
                ''')
                
                # Create index for faster queries
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON scans(timestamp DESC)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_classification 
                    ON scans(classification)
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def store_scan_result(self, text: str, classification: str, confidence: float, 
                         probabilities: Dict, ip_address: str = None, 
                         user_agent: str = None) -> int:
        """
        Store a scan result in the database
        
        Args:
            text: Email text that was scanned
            classification: Classification result
            confidence: Confidence score
            probabilities: Dictionary of class probabilities
            ip_address: Client IP address (optional)
            user_agent: Client user agent (optional)
            
        Returns:
            ID of the inserted record
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO scans (text, classification, confidence, probabilities, 
                                     ip_address, user_agent, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
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
                
                logger.info(f"Stored scan result with ID: {record_id}")
                return record_id
                
        except Exception as e:
            logger.error(f"Failed to store scan result: {str(e)}")
            raise
    
    def get_scan_history(self, limit: int = 10, offset: int = 0) -> List[Dict]:
        """
        Retrieve recent scan history
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of scan records
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, text, classification, confidence, probabilities, timestamp
                    FROM scans
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
                
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
    
    def get_scan_by_id(self, scan_id: int) -> Optional[Dict]:
        """
        Retrieve a specific scan by ID
        
        Args:
            scan_id: ID of the scan to retrieve
            
        Returns:
            Scan record or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM scans WHERE id = ?
                ''', (scan_id,))
                
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
    
    def get_classification_stats(self, days: int = 30) -> Dict:
        """
        Get classification statistics
        
        Args:
            days: Number of days to look back for statistics
            
        Returns:
            Dictionary with statistics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total counts by classification
                cursor.execute('''
                    SELECT classification, COUNT(*) as count
                    FROM scans
                    WHERE timestamp >= datetime('now', '-' || ? || ' days')
                    GROUP BY classification
                    ORDER BY count DESC
                ''', (days,))
                
                classification_counts = {}
                total_scans = 0
                
                for row in cursor.fetchall():
                    classification_counts[row['classification']] = row['count']
                    total_scans += row['count']
                
                # Get average confidence by classification
                cursor.execute('''
                    SELECT classification, AVG(confidence) as avg_confidence
                    FROM scans
                    WHERE timestamp >= datetime('now', '-' || ? || ' days')
                    GROUP BY classification
                ''', (days,))
                
                avg_confidence = {}
                for row in cursor.fetchall():
                    avg_confidence[row['classification']] = round(row['avg_confidence'], 4)
                
                # Get recent activity (scans per day for last 7 days)
                cursor.execute('''
                    SELECT DATE(timestamp) as scan_date, COUNT(*) as count
                    FROM scans
                    WHERE timestamp >= datetime('now', '-7 days')
                    GROUP BY DATE(timestamp)
                    ORDER BY scan_date DESC
                ''')
                
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
    
    def delete_old_scans(self, days: int = 90) -> int:
        """
        Delete scans older than specified days (for cleanup)
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of deleted records
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM scans
                    WHERE timestamp < datetime('now', '-' || ? || ' days')
                ''', (days,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Deleted {deleted_count} old scan records")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to delete old scans: {str(e)}")
            return 0
    
    def get_database_info(self) -> Dict:
        """
        Get database information and statistics
        
        Returns:
            Dictionary with database information
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total record count
                cursor.execute('SELECT COUNT(*) FROM scans')
                total_records = cursor.fetchone()[0]
                
                # Get database size
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                # Get oldest and newest records
                cursor.execute('''
                    SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest
                    FROM scans
                ''')
                
                date_range = cursor.fetchone()
                
                return {
                    'database_path': self.db_path,
                    'total_records': total_records,
                    'database_size_bytes': db_size,
                    'database_size_mb': round(db_size / (1024 * 1024), 2),
                    'oldest_record': date_range['oldest'],
                    'newest_record': date_range['newest']
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
    logger.info(f"Database initialized at: {db_path}")