#!/usr/bin/env python3
"""
Comprehensive database setup script for ERCOT Analytics Dashboard
Combines all database table creation and configuration
"""
import sys
import os
from pathlib import Path

# Add the parent directory to sys.path so we can import from database module
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_connection import db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Combined SQL script for all tables
COMPLETE_DATABASE_SCHEMA = """
-- ERCOT Analytics Dashboard - Complete Database Schema
-- This script creates all necessary tables for the application

-- ==========================================
-- User Authentication Tables
-- ==========================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- User sessions table for JWT token management
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

-- ==========================================
-- AI Visualization Tables
-- ==========================================

-- AI visualization requests table
CREATE TABLE IF NOT EXISTS ai_visualizations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    request_text TEXT NOT NULL,
    visualization_type VARCHAR(50), -- 'chart', 'graph', 'dashboard', etc.
    chart_config JSONB, -- Store chart configuration
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);

-- ==========================================
-- Dashboard Customization Tables
-- ==========================================

-- User dashboard customization table
CREATE TABLE IF NOT EXISTS user_dashboard_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    panel_id VARCHAR(50) NOT NULL, -- e.g., 'chart1', 'chart2', 'ai_viz_123'
    panel_name VARCHAR(100) NOT NULL, -- e.g., 'Real-Time Price Overview'
    panel_type VARCHAR(20) DEFAULT 'predefined', -- 'predefined' or 'ai_generated'
    is_visible BOOLEAN DEFAULT true,
    panel_order INTEGER DEFAULT 0,
    panel_width INTEGER DEFAULT NULL, -- in pixels, null means default
    panel_height INTEGER DEFAULT NULL, -- in pixels, null means default
    panel_grid_column INTEGER DEFAULT NULL, -- grid position (1 or 2)
    iframe_src TEXT, -- Grafana iframe URL
    ai_visualization_id INTEGER REFERENCES ai_visualizations(id) ON DELETE SET NULL,
    dashboard_uid VARCHAR(50), -- Grafana dashboard UID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, panel_id)
);

-- ==========================================
-- API Management Tables
-- ==========================================

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    key_name VARCHAR(100) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    api_secret_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    rate_limit_per_hour INTEGER DEFAULT 1000,
    rate_limit_per_day INTEGER DEFAULT 10000,
    allowed_endpoints TEXT[] DEFAULT ARRAY['/api/v1/*'],
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE,
    usage_count INTEGER DEFAULT 0
);

-- API Usage Tracking table
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id SERIAL PRIMARY KEY,
    api_key_id INTEGER REFERENCES api_keys(id) ON DELETE CASCADE,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER DEFAULT NULL,
    response_time_ms INTEGER DEFAULT NULL,
    ip_address INET,
    user_agent TEXT,
    query_parameters JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- Indexes for Performance
-- ==========================================

-- User table indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Session table indexes
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token_hash ON user_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);

-- AI visualization indexes
CREATE INDEX IF NOT EXISTS idx_ai_visualizations_user_id ON ai_visualizations(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_visualizations_status ON ai_visualizations(status);
CREATE INDEX IF NOT EXISTS idx_ai_visualizations_created_at ON ai_visualizations(created_at);

-- Dashboard settings indexes
CREATE INDEX IF NOT EXISTS idx_user_dashboard_settings_user_id ON user_dashboard_settings(user_id);
CREATE INDEX IF NOT EXISTS idx_user_dashboard_settings_panel_id ON user_dashboard_settings(panel_id);
CREATE INDEX IF NOT EXISTS idx_user_dashboard_settings_panel_type ON user_dashboard_settings(panel_type);
CREATE INDEX IF NOT EXISTS idx_user_dashboard_settings_ai_viz_id ON user_dashboard_settings(ai_visualization_id);

-- API management indexes
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_api_key ON api_keys(api_key);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_api_usage_logs_api_key_id ON api_usage_logs(api_key_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_logs_created_at ON api_usage_logs(created_at);

-- ==========================================
-- Trigger Functions
-- ==========================================

-- Generic updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ==========================================
-- Triggers
-- ==========================================

-- Drop existing triggers to avoid conflicts
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP TRIGGER IF EXISTS update_user_dashboard_settings_updated_at ON user_dashboard_settings;
DROP TRIGGER IF EXISTS update_ai_visualizations_updated_at ON ai_visualizations;

-- Create triggers
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_dashboard_settings_updated_at 
    BEFORE UPDATE ON user_dashboard_settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_visualizations_updated_at 
    BEFORE UPDATE ON ai_visualizations 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
"""

# Default dashboard panels for new users
DEFAULT_DASHBOARD_PANELS = """
INSERT INTO user_dashboard_settings (user_id, panel_id, panel_name, panel_type, is_visible, panel_order, panel_grid_column, iframe_src) 
SELECT 
    u.id,
    panel.panel_id,
    panel.panel_name,
    'predefined',
    true,
    panel.panel_order,
    panel.grid_column,
    panel.iframe_src
FROM users u
CROSS JOIN (
    VALUES 
        ('chart1', 'Real-Time Price Overview', 1, 2, 'http://52.4.166.16:3000/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=14&refresh=30s'),
        ('chart2', 'System Available Capacity', 2, 1, 'http://52.4.166.16:3000/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=7&refresh=30s'),
        ('chart3', 'Emergency & Outage Status', 3, 1, 'http://52.4.166.16:3000/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=1&refresh=30s'),
        ('chart4', 'Reserve Capacity Overview', 4, 2, 'http://52.4.166.16:3000/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=12&refresh=30s'),
        ('chart5', 'Settlement Point Prices', 5, 2, 'http://52.4.166.16:3000/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=13&refresh=30s')
) AS panel(panel_id, panel_name, panel_order, grid_column, iframe_src)
WHERE NOT EXISTS (
    SELECT 1 FROM user_dashboard_settings uds 
    WHERE uds.user_id = u.id AND uds.panel_id = panel.panel_id
);
"""

def test_database_connection():
    """Test database connectivity with enhanced error handling"""
    logger.info("🔍 Testing database connection...")
    try:
        # Test basic connectivity
        connection_result = db.test_connection()
        
        if connection_result:
            logger.info("✅ Database connection successful")
            
            # Additional validation - check if we can create a test table
            try:
                test_sql = "CREATE TEMP TABLE connection_test (id INTEGER); DROP TABLE connection_test;"
                db.execute_script(test_sql, autocommit=True)
                logger.info("✅ Database write permissions verified")
            except Exception as write_test_error:
                logger.warning(f"Database connection successful but write test failed: {write_test_error}")
                
            return True
        else:
            logger.error("❌ Database connection failed")
            return False
            
    except ImportError as e:
        logger.error(f"❌ Missing database libraries: {e}")
        logger.error("Please install psycopg2: pip install psycopg2-binary")
        return False
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        
        # Provide specific guidance based on error type
        error_str = str(e).lower()
        if 'connection refused' in error_str:
            logger.error("Hint: Is PostgreSQL running? Check DB_HOST and DB_PORT environment variables.")
        elif 'authentication failed' in error_str:
            logger.error("Hint: Check DB_USER and DB_PASSWORD environment variables.")
        elif 'database' in error_str and 'does not exist' in error_str:
            logger.error("Hint: Check DB_NAME environment variable. Does the database exist?")
            
        return False

def check_existing_tables():
    """Check what tables already exist"""
    logger.info("📋 Checking existing database structure...")
    try:
        tables = db.get_table_info()
        if tables:
            logger.info("Existing tables:")
            for table_name, table_type in tables:
                logger.info(f"   • {table_name} ({table_type})")
        else:
            logger.info("No existing tables found")
        return tables
    except Exception as e:
        logger.error(f"❌ Error checking tables: {e}")
        return []

def setup_database_schema():
    """Create all database tables and schema with enhanced error handling"""
    logger.info("🛠️  Creating database schema...")
    try:
        # Validate the SQL script before execution
        if not COMPLETE_DATABASE_SCHEMA or not isinstance(COMPLETE_DATABASE_SCHEMA, str):
            logger.error("Invalid database schema script")
            return False
            
        if len(COMPLETE_DATABASE_SCHEMA.strip()) == 0:
            logger.error("Empty database schema script")
            return False
            
        # Execute the schema creation
        db.execute_script(COMPLETE_DATABASE_SCHEMA)
        logger.info("✅ Database schema created successfully!")
        
        # Verify tables were created
        try:
            tables = db.get_table_info()
            expected_tables = ['users', 'user_sessions', 'ai_visualizations', 'user_dashboard_settings', 'api_keys', 'api_usage_logs']
            created_tables = [table[0] for table in tables]
            
            missing_tables = [table for table in expected_tables if table not in created_tables]
            if missing_tables:
                logger.warning(f"Some expected tables were not created: {missing_tables}")
            else:
                logger.info("✅ All expected tables created successfully")
                
        except Exception as verification_error:
            logger.warning(f"Could not verify table creation: {verification_error}")
        
        # List created tables
        logger.info("📊 Created tables:")
        logger.info("   • users (authentication)")
        logger.info("   • user_sessions (JWT token management)")
        logger.info("   • ai_visualizations (AI-generated charts)")
        logger.info("   • user_dashboard_settings (dashboard customization)")
        logger.info("   • api_keys (API access management)")
        logger.info("   • api_usage_logs (API usage tracking)")
        logger.info("✅ Indexes and triggers created")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Missing required libraries: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error creating database schema: {e}")
        
        # Provide specific guidance based on error type
        error_str = str(e).lower()
        if 'permission denied' in error_str:
            logger.error("Hint: Database user needs CREATE permissions")
        elif 'syntax error' in error_str:
            logger.error("Hint: SQL syntax error in schema script")
        elif 'already exists' in error_str:
            logger.info("Note: Some tables already exist (this is usually OK)")
            return True  # This is often not an error
            
        return False

def setup_default_dashboard_panels():
    """Setup default dashboard panels for existing users with enhanced error handling"""
    logger.info("⚙️  Setting up default dashboard panels...")
    
    try:
        # Validate the SQL script
        if not DEFAULT_DASHBOARD_PANELS or not isinstance(DEFAULT_DASHBOARD_PANELS, str):
            logger.error("Invalid default dashboard panels script")
            return False
            
        # Check if users table exists before trying to add panels
        try:
            tables = db.get_table_info()
            table_names = [table[0] for table in tables]
            
            required_tables = ['users', 'user_dashboard_settings']
            missing_tables = [table for table in required_tables if table not in table_names]
            
            if missing_tables:
                logger.warning(f"Cannot setup default panels: missing tables {missing_tables}")
                return False
                
        except Exception as table_check_error:
            logger.warning(f"Could not verify required tables: {table_check_error}")
            # Continue anyway, let the actual execution fail if needed
        
        db.execute_script(DEFAULT_DASHBOARD_PANELS)
        logger.info("✅ Default dashboard panels configured")
        
        # Verify panels were created
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM user_dashboard_settings WHERE panel_type = 'predefined'")
            panel_count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            if panel_count > 0:
                logger.info(f"✅ {panel_count} default dashboard panels configured")
            else:
                logger.warning("No default dashboard panels were created (possibly no users exist yet)")
                
        except Exception as verification_error:
            logger.warning(f"Could not verify panel creation: {verification_error}")
            
        return True
        
    except Exception as e:
        error_str = str(e).lower()
        if 'does not exist' in error_str and ('users' in error_str or 'user_dashboard_settings' in error_str):
            logger.warning("⚠️  Cannot create default panels: required tables don't exist yet")
            logger.info("This is normal if running setup for the first time")
        else:
            logger.warning(f"⚠️  Could not setup default dashboard panels: {e}")
            
        return False

def get_database_statistics():
    """Get basic statistics about the database with enhanced error handling"""
    logger.info("📊 Gathering database statistics...")
    
    conn = None
    cursor = None
    stats = {
        'active_users': 0,
        'dashboard_settings': 0,
        'ai_visualizations': 0,
        'active_api_keys': 0
    }
    
    try:
        conn, cursor = db.get_cursor()
        
        # User statistics
        try:
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = true;")
            result = cursor.fetchone()
            stats['active_users'] = result[0] if result else 0
        except Exception as e:
            logger.debug(f"Could not get user statistics: {e}")
            stats['active_users'] = 0
            
        # Dashboard settings statistics
        try:
            cursor.execute("SELECT COUNT(*) FROM user_dashboard_settings;")
            result = cursor.fetchone()
            stats['dashboard_settings'] = result[0] if result else 0
        except Exception as e:
            logger.debug(f"Could not get dashboard settings statistics: {e}")
            stats['dashboard_settings'] = 0
            
        # AI visualizations statistics
        try:
            cursor.execute("SELECT COUNT(*) FROM ai_visualizations;")
            result = cursor.fetchone()
            stats['ai_visualizations'] = result[0] if result else 0
        except Exception as e:
            logger.debug(f"Could not get AI visualizations statistics: {e}")
            stats['ai_visualizations'] = 0
            
        # API keys statistics
        try:
            cursor.execute("SELECT COUNT(*) FROM api_keys WHERE is_active = true;")
            result = cursor.fetchone()
            stats['active_api_keys'] = result[0] if result else 0
        except Exception as e:
            logger.debug(f"Could not get API keys statistics: {e}")
            stats['active_api_keys'] = 0
        
        # Additional statistics for health checking
        try:
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
            result = cursor.fetchone()
            stats['total_tables'] = result[0] if result else 0
        except Exception as e:
            logger.debug(f"Could not get table count: {e}")
            stats['total_tables'] = 0
        
        logger.info("Database Statistics:")
        logger.info(f"   👥 Active users: {stats['active_users']}")
        logger.info(f"   ⚙️  Dashboard settings: {stats['dashboard_settings']}")
        logger.info(f"   🤖 AI visualizations: {stats['ai_visualizations']}")
        logger.info(f"   🔑 Active API keys: {stats['active_api_keys']}")
        logger.info(f"   📊 Total tables: {stats['total_tables']}")
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error getting database statistics: {e}")
        return stats
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception as e:
            logger.error(f"Error closing statistics cursor: {e}")
        try:
            if conn:
                conn.close()
        except Exception as e:
            logger.error(f"Error closing statistics connection: {e}")

def main():
    """Main setup function with comprehensive error handling"""
    print("🚀 ERCOT Analytics Dashboard - Database Setup")
    print("=" * 50)
    
    setup_success = True
    error_messages = []
    
    try:
        # Test connection
        print("\n🔍 Phase 1: Testing database connection...")
        if not test_database_connection():
            error_messages.append("Database connection failed")
            print("\n❌ Cannot connect to database. Please check your connection settings.")
            print("\nTroubleshooting tips:")
            print("1. Ensure PostgreSQL is running")
            print("2. Check environment variables: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD")
            print("3. Verify database exists and user has proper permissions")
            return 1
        
        # Check existing structure
        print("\n📊 Phase 2: Checking existing database structure...")
        try:
            existing_tables = check_existing_tables()
        except Exception as e:
            logger.warning(f"Could not check existing tables: {e}")
            existing_tables = []
        
        # Setup schema
        print("\n🛠️ Phase 3: Creating database schema...")
        if not setup_database_schema():
            error_messages.append("Database schema creation failed")
            setup_success = False
            print("\n❌ Failed to create database schema.")
        else:
            print("✅ Database schema setup completed")
        
        # Setup default panels
        print("\n⚙️ Phase 4: Setting up default dashboard panels...")
        try:
            if not setup_default_dashboard_panels():
                error_messages.append("Default dashboard panels setup had issues")
                logger.info("This is often normal for fresh installations")
        except Exception as e:
            logger.warning(f"Error setting up default panels: {e}")
            error_messages.append(f"Default panels error: {e}")
        
        # Show statistics
        print("\n📊 Phase 5: Gathering database statistics...")
        try:
            stats = get_database_statistics()
            if not stats or all(v == 0 for v in stats.values()):
                logger.info("Database is empty - this is normal for a fresh installation")
        except Exception as e:
            logger.warning(f"Could not gather statistics: {e}")
            error_messages.append(f"Statistics error: {e}")
        
        # Final status
        if setup_success and not error_messages:
            print("\n✅ Database setup completed successfully!")
            print("🎉 Your ERCOT Analytics Dashboard is ready to use!")
            return 0
        elif setup_success:
            print("\n⚠️ Database setup completed with warnings:")
            for msg in error_messages:
                print(f"   - {msg}")
            print("\n🎉 Your ERCOT Analytics Dashboard should still work properly!")
            return 0
        else:
            print("\n❌ Database setup failed!")
            for msg in error_messages:
                print(f"   - {msg}")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Fatal error during database setup: {e}")
        print(f"\n❌ Fatal error during setup: {e}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        exit(exit_code)
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        exit(1)