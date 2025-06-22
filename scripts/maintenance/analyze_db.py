import psycopg2
import os
from psycopg2.extras import RealDictCursor

def analyze_database():
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST', 'dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com'),
            database=os.environ.get('DB_NAME', 'analytics'),
            user=os.environ.get('DB_USER', 'dbuser'),
            password=os.environ.get('DB_PASSWORD', 'Superman1262!')
        )
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("=== DATABASE STRUCTURE ANALYSIS ===\n")
        
        # Get all tables
        cursor.execute("""
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print("📋 Tables in database:")
        for table in tables:
            print(f"   • {table['table_name']} ({table['table_type']})")
        
        print("\n" + "="*60 + "\n")
        
        # Analyze each table
        for table in tables:
            table_name = table['table_name']
            print(f"🔍 TABLE: {table_name.upper()}")
            print("-" * 40)
            
            # Get column information
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position;
            """, (table_name,))
            
            columns = cursor.fetchall()
            print("   Columns:")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"     • {col['column_name']}: {col['data_type']} {nullable}{default}")
            
            # Get row count
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                count = cursor.fetchone()['count']
                print(f"   📊 Total records: {count:,}")
            except Exception as e:
                print(f"   ❌ Error getting count: {e}")
            
            # Get sample data for relevant tables
            if table_name in ['ercot_settlement_prices', 'ercot_capacity_monitor']:
                try:
                    cursor.execute(f"SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT 3")
                    samples = cursor.fetchall()
                    if samples:
                        print("   📄 Sample records:")
                        for i, sample in enumerate(samples, 1):
                            print(f"     Sample {i}: {dict(sample)}")
                except Exception as e:
                    print(f"   ❌ Error getting sample: {e}")
            
            # Get date range for time-series tables
            if table_name in ['ercot_settlement_prices', 'ercot_capacity_monitor']:
                try:
                    cursor.execute(f"SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest FROM {table_name}")
                    date_range = cursor.fetchone()
                    if date_range['earliest'] and date_range['latest']:
                        print(f"   📅 Date range: {date_range['earliest']} to {date_range['latest']}")
                except Exception as e:
                    print(f"   ❌ Error getting date range: {e}")
            
            print("\n")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error analyzing database: {e}")

if __name__ == "__main__":
    analyze_database()
