"""
Shared database connection utilities for ERCOT Analytics Dashboard
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Centralized database connection management"""
    
    def __init__(self):
        self.config = {
            'host': os.getenv("DB_HOST", "localhost"),
            'database': os.getenv("DB_NAME", "analytics"),
            'user': os.getenv("DB_USER", "dbuser"),
            'password': os.getenv("DB_PASSWORD", ""),
            'port': int(os.getenv("DB_PORT", "5432"))
        }
    
    def get_connection(self, autocommit=True):
        """Get a database connection with optional autocommit"""
        try:
            conn = psycopg2.connect(**self.config)
            if autocommit:
                conn.autocommit = True
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise ConnectionError(f"Failed to connect to database: {e}")
    
    def get_cursor(self, cursor_factory=None, autocommit=True):
        """Get a database cursor with optional cursor factory"""
        conn = self.get_connection(autocommit=autocommit)
        if cursor_factory:
            return conn, conn.cursor(cursor_factory=cursor_factory)
        return conn, conn.cursor()
    
    def execute_script(self, sql_script, autocommit=True):
        """Execute a SQL script and handle errors"""
        try:
            conn = self.get_connection(autocommit=False)
            cursor = conn.cursor()
            
            cursor.execute(sql_script)
            
            if autocommit:
                conn.commit()
                
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error executing SQL script: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            raise
    
    def test_connection(self):
        """Test database connectivity"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_table_info(self):
        """Get information about existing tables"""
        try:
            conn, cursor = self.get_cursor()
            
            cursor.execute("""
                SELECT table_name, table_type
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return [(table[0], table[1]) for table in tables]
            
        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            return []

# Global database instance
db = DatabaseConnection()

def get_db_connection():
    """Convenience function for backward compatibility"""
    return db.get_connection()