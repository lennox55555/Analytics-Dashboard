import psycopg2
from datetime import datetime

def cleanup_capacity_data():
    conn = psycopg2.connect(
        host='dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com',
        database='analytics',
        user='dbuser',
        password='Superman1262!'
    )
    
    cursor = conn.cursor()
    
    # Check current state
    print("=== BEFORE CLEANUP ===")
    cursor.execute("SELECT COUNT(*) FROM ercot_capacity_monitor")
    total_before = cursor.fetchone()[0]
    print(f"Total rows: {total_before:,}")
    
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM ercot_capacity_monitor")
    date_range = cursor.fetchone()
    print(f"Date range: {date_range[0]} to {date_range[1]}")
    
    # Strategy: Keep only records where minute is 0, 15, 30, or 45
    print("\n=== CLEANING UP ===")
    print("Keeping only records at 00, 15, 30, 45 minutes past each hour...")
    
    cursor.execute("""
        DELETE FROM ercot_capacity_monitor 
        WHERE EXTRACT(minute FROM timestamp) NOT IN (0, 15, 30, 45)
    """)
    
    deleted_count = cursor.rowcount
    conn.commit()
    
    # Check results
    print("\n=== AFTER CLEANUP ===")
    cursor.execute("SELECT COUNT(*) FROM ercot_capacity_monitor")
    total_after = cursor.fetchone()[0]
    print(f"Total rows: {total_after:,}")
    print(f"Deleted: {deleted_count:,} rows")
    print(f"Reduction: {((total_before - total_after) / total_before * 100):.1f}%")
    
    # Verify 15-minute intervals
    cursor.execute("""
        SELECT DISTINCT EXTRACT(minute FROM timestamp) as minute 
        FROM ercot_capacity_monitor 
        ORDER BY minute
    """)
    minutes = [row[0] for row in cursor.fetchall()]
    print(f"Remaining minutes: {minutes}")
    
    cursor.close()
    conn.close()
    print("\n✅ Cleanup complete!")

if __name__ == "__main__":
    cleanup_capacity_data()
