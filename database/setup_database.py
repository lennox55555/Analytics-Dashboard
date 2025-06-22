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
    """Test database connectivity"""
    logger.info("🔍 Testing database connection...")
    try:
        if db.test_connection():
            logger.info("✅ Database connection successful")
            return True
        else:
            logger.error("❌ Database connection failed")
            return False
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
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
    """Create all database tables and schema"""
    logger.info("🛠️  Creating database schema...")
    try:
        db.execute_script(COMPLETE_DATABASE_SCHEMA)
        logger.info("✅ Database schema created successfully!")
        
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
    except Exception as e:
        logger.error(f"❌ Error creating database schema: {e}")
        return False

def setup_default_dashboard_panels():
    """Setup default dashboard panels for existing users"""
    logger.info("⚙️  Setting up default dashboard panels...")
    try:
        db.execute_script(DEFAULT_DASHBOARD_PANELS)
        logger.info("✅ Default dashboard panels configured")
        return True
    except Exception as e:
        logger.warning(f"⚠️  Note: {e}")
        return False

def get_database_statistics():
    """Get basic statistics about the database"""
    logger.info("📊 Gathering database statistics...")
    try:
        conn, cursor = db.get_cursor()
        
        stats = {}
        
        # User statistics
        try:
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = true;")
            stats['active_users'] = cursor.fetchone()[0]
        except:
            stats['active_users'] = 0
            
        # Dashboard settings statistics
        try:
            cursor.execute("SELECT COUNT(*) FROM user_dashboard_settings;")
            stats['dashboard_settings'] = cursor.fetchone()[0]
        except:
            stats['dashboard_settings'] = 0
            
        # AI visualizations statistics
        try:
            cursor.execute("SELECT COUNT(*) FROM ai_visualizations;")
            stats['ai_visualizations'] = cursor.fetchone()[0]
        except:
            stats['ai_visualizations'] = 0
            
        # API keys statistics
        try:
            cursor.execute("SELECT COUNT(*) FROM api_keys WHERE is_active = true;")
            stats['active_api_keys'] = cursor.fetchone()[0]
        except:
            stats['active_api_keys'] = 0
        
        cursor.close()
        conn.close()
        
        logger.info("Database Statistics:")
        logger.info(f"   👥 Active users: {stats['active_users']}")
        logger.info(f"   ⚙️  Dashboard settings: {stats['dashboard_settings']}")
        logger.info(f"   🤖 AI visualizations: {stats['ai_visualizations']}")
        logger.info(f"   🔑 Active API keys: {stats['active_api_keys']}")
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error getting database statistics: {e}")
        return {}

def main():
    """Main setup function"""
    print("🚀 ERCOT Analytics Dashboard - Database Setup")
    print("=" * 50)
    
    # Test connection
    if not test_database_connection():
        print("\n❌ Cannot connect to database. Please check your connection settings.")
        return 1
    
    # Check existing structure
    existing_tables = check_existing_tables()
    
    # Setup schema
    if not setup_database_schema():
        print("\n❌ Failed to create database schema.")
        return 1
    
    # Setup default panels
    setup_default_dashboard_panels()
    
    # Show statistics
    get_database_statistics()
    
    print("\n✅ Database setup completed successfully!")
    print("🎉 Your ERCOT Analytics Dashboard is ready to use!")
    
    return 0

if __name__ == "__main__":
    exit(main())