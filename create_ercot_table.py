import psycopg2

def create_ercot_table():
    conn = psycopg2.connect(
        host='db',  # Use 'db' as the host name in Docker network
        database='analytics',
        user='dbuser',
        password='03SVZH7GPGNbRxeX'
    )
    cursor = conn.cursor()
    
    # Create the table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ercot_capacity_monitor (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        category VARCHAR(255),
        subcategory VARCHAR(255),
        value NUMERIC,
        unit VARCHAR(10)
    );
    
    -- Create index for faster queries
    CREATE INDEX IF NOT EXISTS idx_ercot_timestamp ON ercot_capacity_monitor (timestamp);
    CREATE INDEX IF NOT EXISTS idx_ercot_category ON ercot_capacity_monitor (category);
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()
    print("ERCOT capacity monitor table created successfully")

if __name__ == "__main__":
    create_ercot_table()
