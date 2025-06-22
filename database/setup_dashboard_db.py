import psycopg2
import os

# SQL script to create dashboard customization tables
sql_script = """
-- Add user dashboard customization table
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_dashboard_settings_user_id ON user_dashboard_settings(user_id);
CREATE INDEX IF NOT EXISTS idx_user_dashboard_settings_panel_id ON user_dashboard_settings(panel_id);

-- Update trigger for user_dashboard_settings
CREATE OR REPLACE FUNCTION update_dashboard_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_dashboard_settings_updated_at 
    BEFORE UPDATE ON user_dashboard_settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_dashboard_updated_at_column();
"""

def setup_dashboard_database():
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
        
        # Commit the changes
        conn.commit()
        
        print("✅ Dashboard customization tables created successfully!")
        print("✅ User dashboard settings table created")
        print("✅ Indexes created")
        print("✅ Triggers created")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error creating dashboard tables: {e}")

if __name__ == "__main__":
    setup_dashboard_database()
