import psycopg2
import os

# SQL script to create authentication and dashboard customization tables
sql_script = """
-- User authentication and AI visualization tables

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
    error_message TEXT
);

-- User dashboard customization table
CREATE TABLE IF NOT EXISTS user_dashboard_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    panel_id VARCHAR(50) NOT NULL, -- e.g., 'chart1', 'chart2', etc.
    panel_name VARCHAR(100) NOT NULL, -- e.g., 'Real-Time Price Overview'
    is_visible BOOLEAN DEFAULT true,
    panel_order INTEGER DEFAULT 0,
    panel_width INTEGER DEFAULT NULL, -- in pixels, null means default
    panel_height INTEGER DEFAULT NULL, -- in pixels, null means default
    panel_grid_column INTEGER DEFAULT NULL, -- grid position
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, panel_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token_hash ON user_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_ai_visualizations_user_id ON ai_visualizations(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_visualizations_status ON ai_visualizations(status);
CREATE INDEX IF NOT EXISTS idx_user_dashboard_settings_user_id ON user_dashboard_settings(user_id);
CREATE INDEX IF NOT EXISTS idx_user_dashboard_settings_panel_id ON user_dashboard_settings(panel_id);

-- Update trigger functions
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE OR REPLACE FUNCTION update_dashboard_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop triggers if they exist, then recreate them
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_dashboard_settings_updated_at ON user_dashboard_settings;
CREATE TRIGGER update_user_dashboard_settings_updated_at 
    BEFORE UPDATE ON user_dashboard_settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_dashboard_updated_at_column();
"""

def setup_database():
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST', 'dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com'),
            database=os.environ.get('DB_NAME', 'analytics'),
            user=os.environ.get('DB_USER', 'dbuser'),
            password=os.environ.get('DB_PASSWORD', 'Superman1262!')
        )
        
        cursor = conn.cursor()
        
        # Execute the SQL script
        cursor.execute(sql_script)
        
        # Insert default panels for existing users (separate transaction to handle conflicts gracefully)
        try:
            cursor.execute("""
                INSERT INTO user_dashboard_settings (user_id, panel_id, panel_name, is_visible, panel_order) 
                SELECT 
                    u.id,
                    panel.panel_id,
                    panel.panel_name,
                    true,
                    panel.panel_order
                FROM users u
                CROSS JOIN (
                    VALUES 
                        ('chart1', 'Real-Time Price Overview', 1),
                        ('chart2', 'System Available Capacity', 2),
                        ('chart3', 'Emergency & Outage Status', 3),
                        ('chart4', 'Reserve Capacity Overview', 4),
                        ('chart5', 'Settlement Point Prices', 5)
                ) AS panel(panel_id, panel_name, panel_order)
                ON CONFLICT (user_id, panel_id) DO NOTHING;
            """)
            print("✅ Default dashboard panels inserted for existing users")
        except Exception as e:
            print(f"⚠️  Note: {e}")
        
        # Commit the changes
        conn.commit()
        
        print("✅ Database tables created successfully!")
        print("✅ Users table created")
        print("✅ User sessions table created") 
        print("✅ AI visualizations table created")
        print("✅ User dashboard settings table created")
        print("✅ Indexes created")
        print("✅ Triggers created")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")

def check_existing_tables():
    """Check what tables already exist in the database"""
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST', 'dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com'),
            database=os.environ.get('DB_NAME', 'analytics'),
            user=os.environ.get('DB_USER', 'dbuser'),
            password=os.environ.get('DB_PASSWORD', 'Superman1262!')
        )
        
        cursor = conn.cursor()
        
        # Check existing tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print("📋 Existing tables in database:")
        for table in tables:
            print(f"   • {table[0]}")
        
        # Check if users exist
        try:
            cursor.execute("SELECT COUNT(*) FROM users;")
            user_count = cursor.fetchone()[0]
            print(f"👥 Current users in database: {user_count}")
        except:
            print("👥 Users table doesn't exist yet")
        
        # Check if dashboard settings table exists
        try:
            cursor.execute("SELECT COUNT(*) FROM user_dashboard_settings;")
            dashboard_count = cursor.fetchone()[0]
            print(f"⚙️  Current dashboard settings: {dashboard_count}")
        except:
            print("⚙️  Dashboard settings table doesn't exist yet")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking existing tables: {e}")

if __name__ == "__main__":
    print("🔍 Checking existing database structure...")
    check_existing_tables()
    print("\n🛠️  Setting up authentication and dashboard tables...")
    setup_database()
    print("\n✅ Setup complete!")
