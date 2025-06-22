import psycopg2
import os

sql_script = """
-- API Key Management Tables

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
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER,
    ip_address INET,
    user_agent TEXT,
    query_parameters JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_api_key ON api_keys(api_key);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_api_usage_logs_api_key_id ON api_usage_logs(api_key_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_logs_created_at ON api_usage_logs(created_at);
"""

def setup_api_tables():
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST', 'dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com'),
            database=os.environ.get('DB_NAME', 'analytics'),
            user=os.environ.get('DB_USER', 'dbuser'),
            password=os.environ.get('DB_PASSWORD', 'Superman1262!')
        )
        
        cursor = conn.cursor()
        cursor.execute(sql_script)
        conn.commit()
        
        print("✅ API tables created successfully!")
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error creating API tables: {e}")

if __name__ == "__main__":
    setup_api_tables()
