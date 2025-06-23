"""
Shared database connection utilities for ERCOT Analytics Dashboard
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Centralized database connection management with enhanced error handling"""
    
    def __init__(self):
        try:
            self.config = {
                'host': os.getenv("DB_HOST", "localhost"),
                'database': os.getenv("DB_NAME", "analytics"),
                'user': os.getenv("DB_USER", "dbuser"),
                'password': os.getenv("DB_PASSWORD", ""),
                'port': int(os.getenv("DB_PORT", "5432"))
            }
            
            # Validate configuration
            self._validate_config()
            
        except ValueError as e:
            logger.error(f"Invalid database port configuration: {e}")
            # Use safe defaults
            self.config = {
                'host': 'localhost',
                'database': 'analytics', 
                'user': 'dbuser',
                'password': '',
                'port': 5432
            }
        except Exception as e:
            logger.error(f"Error initializing database configuration: {e}")
            # Use safe defaults
            self.config = {
                'host': 'localhost',
                'database': 'analytics',
                'user': 'dbuser', 
                'password': '',
                'port': 5432
            }
    
    def _validate_config(self):
        """Validate database configuration parameters"""
        required_fields = ['host', 'database', 'user']
        missing_fields = [field for field in required_fields if not self.config.get(field)]
        
        if missing_fields:
            logger.warning(f"Missing database configuration fields: {missing_fields}")
            
        # Validate port range
        port = self.config.get('port', 5432)
        if not isinstance(port, int) or port < 1 or port > 65535:
            logger.warning(f"Invalid database port: {port}, using default 5432")
            self.config['port'] = 5432
            
        # Log configuration (without password)
        safe_config = {k: v for k, v in self.config.items() if k != 'password'}
        safe_config['password'] = '***' if self.config.get('password') else 'empty'
        logger.info(f"Database configuration: {safe_config}")
    
    def get_connection(self, autocommit=True, timeout=30):
        """Get a database connection with comprehensive error handling"""
        try:
            # Add connection timeout to config
            connection_config = self.config.copy()
            connection_config['connect_timeout'] = timeout
            
            conn = psycopg2.connect(**connection_config)
            
            if autocommit:
                conn.autocommit = True
                
            # Test the connection
            try:
                with conn.cursor() as test_cursor:
                    test_cursor.execute('SELECT 1')
                    test_cursor.fetchone()
            except Exception as test_error:
                logger.error(f"Database connection test failed: {test_error}")
                conn.close()
                raise ConnectionError(f"Database connection test failed: {test_error}")
                
            return conn
            
        except psycopg2.OperationalError as e:
            error_msg = str(e).lower()
            if 'could not connect' in error_msg:
                logger.error(f"Cannot connect to database server at {self.config['host']}:{self.config['port']}")
                raise ConnectionError(f"Database server unreachable: {self.config['host']}:{self.config['port']}")
            elif 'authentication failed' in error_msg:
                logger.error("Database authentication failed - check username/password")
                raise ConnectionError("Database authentication failed")
            elif 'database' in error_msg and 'does not exist' in error_msg:
                logger.error(f"Database '{self.config['database']}' does not exist")
                raise ConnectionError(f"Database '{self.config['database']}' not found")
            else:
                logger.error(f"Database operational error: {e}")
                raise ConnectionError(f"Database connection failed: {e}")
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error: {e}")
            raise ConnectionError(f"Database error: {e}")
        except Exception as e:
            logger.error(f"Unexpected database connection error: {e}")
            raise ConnectionError(f"Failed to connect to database: {e}")
    
    def get_cursor(self, cursor_factory=None, autocommit=True):
        """Get a database cursor with optional cursor factory"""
        conn = self.get_connection(autocommit=autocommit)
        if cursor_factory:
            return conn, conn.cursor(cursor_factory=cursor_factory)
        return conn, conn.cursor()
    
    def execute_script(self, sql_script, autocommit=True):
        """Execute a SQL script with comprehensive error handling"""
        if not sql_script or not isinstance(sql_script, str):
            logger.error(f"Invalid SQL script provided: {type(sql_script)}")
            raise ValueError("SQL script must be a non-empty string")
            
        conn = None
        cursor = None
        
        try:
            conn = self.get_connection(autocommit=False)
            cursor = conn.cursor()
            
            # Split script into individual statements for better error reporting
            statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
            
            executed_count = 0
            for i, statement in enumerate(statements):
                try:
                    cursor.execute(statement)
                    executed_count += 1
                except psycopg2.Error as stmt_error:
                    logger.error(f"Error executing statement {i+1}/{len(statements)}: {stmt_error}")
                    logger.error(f"Failed statement: {statement[:200]}...")
                    raise
            
            if autocommit:
                conn.commit()
                logger.info(f"Successfully executed {executed_count} SQL statements")
                
            return True
            
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error executing script: {e}")
            if conn:
                try:
                    conn.rollback()
                    logger.info("Transaction rolled back due to error")
                except Exception as rollback_error:
                    logger.error(f"Error during rollback: {rollback_error}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error executing SQL script: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception as rollback_error:
                    logger.error(f"Error during rollback: {rollback_error}")
            raise
        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception as e:
                logger.error(f"Error closing cursor: {e}")
            try:
                if conn:
                    conn.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
    
    def test_connection(self):
        """Test database connectivity with detailed error reporting"""
        conn = None
        cursor = None
        
        try:
            logger.info("Testing database connection...")
            conn = self.get_connection(timeout=10)
            cursor = conn.cursor()
            
            # Test basic connectivity
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
            if not result or result[0] != 1:
                logger.error("Database test query returned unexpected result")
                return False
            
            # Test database version
            try:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                logger.info(f"Connected to: {version.split(',')[0]}")
            except Exception as version_error:
                logger.warning(f"Could not get database version: {version_error}")
            
            # Test if we can access our expected tables
            try:
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('users', 'ercot_capacity_monitor', 'ercot_settlement_prices')
                """)
                tables = cursor.fetchall()
                logger.info(f"Found {len(tables)} expected tables in database")
            except Exception as table_error:
                logger.warning(f"Could not check for expected tables: {table_error}")
            
            logger.info("Database connection test successful")
            return True
            
        except ConnectionError as e:
            logger.error(f"Database connection test failed: {e}")
            return False
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error during connection test: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during connection test: {e}")
            return False
        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception as e:
                logger.error(f"Error closing test cursor: {e}")
            try:
                if conn:
                    conn.close()
            except Exception as e:
                logger.error(f"Error closing test connection: {e}")
    
    def get_table_info(self):
        """Get information about existing tables with enhanced error handling"""
        conn = None
        cursor = None
        
        try:
            conn, cursor = self.get_cursor()
            
            cursor.execute("""
                SELECT table_name, table_type, 
                       COALESCE(table_comment, 'No description') as table_comment
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            
            if not tables:
                logger.warning("No tables found in public schema")
                return []
            
            # Convert to list of tuples for backward compatibility
            table_info = []
            for table in tables:
                try:
                    table_info.append((table[0], table[1]))
                except (IndexError, TypeError) as e:
                    logger.warning(f"Error processing table info: {e}")
                    continue
            
            logger.info(f"Found {len(table_info)} tables in database")
            return table_info
            
        except psycopg2.Error as e:
            logger.error(f"Database error getting table info: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting table info: {e}")
            return []
        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception as e:
                logger.error(f"Error closing cursor: {e}")
            try:
                if conn:
                    conn.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

# Global database instance
db = DatabaseConnection()

def get_db_connection():
    """Convenience function for backward compatibility with error handling"""
    try:
        return db.get_connection()
    except Exception as e:
        logger.error(f"Failed to get database connection via convenience function: {e}")
        return None