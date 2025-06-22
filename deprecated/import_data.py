import os
import csv
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise e

def import_apple_stock_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if table has data
        cursor.execute("SELECT COUNT(*) FROM apple_stock")
        count = cursor.fetchone()[0]
        
        if count > 0:
            logger.info("Apple stock data already imported, skipping...")
            return
        
        logger.info("Importing apple stock data...")
        
        # Read CSV file
        with open('apple_stock.csv', 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header row
            
            # Prepare data for batch insert
            data = []
            for row in reader:
                date_obj = datetime.strptime(row[0], '%Y-%m-%d')
                data.append((
                    date_obj,
                    float(row[1]),  # open
                    float(row[2]),  # high
                    float(row[3]),  # low
                    float(row[4]),  # close
                    float(row[5])     # volume
                ))
            
            # Batch insert
            query = """
                INSERT INTO apple_stock (date, open, high, low, close, volume)
                VALUES %s
            """
            execute_values(cursor, query, data)
            
            logger.info(f"Successfully imported {len(data)} rows of apple stock data")
            
    except Exception as e:
        logger.error(f"Error importing apple stock data: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def calculate_derived_metrics():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if metrics tables have data
        cursor.execute("SELECT COUNT(*) FROM daily_metrics")
        count = cursor.fetchone()[0]
        
        if count > 0:
            logger.info("Metrics already calculated, skipping...")
            return
        
        logger.info("Calculating daily metrics...")
        
        # Calculate daily metrics
        daily_query = """
            INSERT INTO daily_metrics (date, avg_price, volume_change_pct, price_change_pct)
            SELECT 
                date,
                (open + high + low + close) / 4 as avg_price,
                100 * (volume - LAG(volume) OVER (ORDER BY date)) / NULLIF(LAG(volume) OVER (ORDER BY date), 0) as volume_change_pct,
                100 * (close - open) / NULLIF(open, 0) as price_change_pct
            FROM apple_stock
            ORDER BY date
        """
        cursor.execute(daily_query)
        
        logger.info("Calculating monthly metrics...")
        
        # Calculate monthly metrics
        monthly_query = """
            INSERT INTO monthly_metrics (month, avg_price, max_price, min_price, total_volume, volatility)
            SELECT 
                DATE_TRUNC('month', date) as month,
                AVG((open + high + low + close) / 4) as avg_price,
                MAX(high) as max_price,
                MIN(low) as min_price,
                SUM(volume) as total_volume,
                STDDEV(close) as volatility
            FROM apple_stock
            GROUP BY DATE_TRUNC('month', date)
            ORDER BY month
        """
        cursor.execute(monthly_query)
        
        logger.info("Successfully calculated metrics")
        
    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import_apple_stock_data()
    calculate_derived_metrics()
