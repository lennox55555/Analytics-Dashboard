import requests
import psycopg2
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import logging
import os
import sys
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ercot_price_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

def get_ercot_now():
    """Get current time in ERCOT's timezone (Central Time)."""
    central_tz = pytz.timezone('US/Central')
    utc_now = datetime.now(pytz.UTC)
    central_now = utc_now.astimezone(central_tz)
    logger.info(f"Current UTC time: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"Current Central time: {central_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    return central_now

def create_price_table():
    """Create the ERCOT price table if it doesn't exist."""
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST', 'dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com'),
            database=os.environ.get('DB_NAME', 'analytics'),
            user=os.environ.get('DB_USER', 'dbuser'),
            password=os.environ.get('DB_PASSWORD', 'Superman1262!')
        )
        cursor = conn.cursor()
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS ercot_settlement_prices (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            oper_day DATE NOT NULL,
            interval_ending TIME NOT NULL,
            hb_busavg DECIMAL(10,2),
            hb_houston DECIMAL(10,2),
            hb_hubavg DECIMAL(10,2),
            hb_north DECIMAL(10,2),
            hb_pan DECIMAL(10,2),
            hb_south DECIMAL(10,2),
            hb_west DECIMAL(10,2),
            lz_aen DECIMAL(10,2),
            lz_cps DECIMAL(10,2),
            lz_houston DECIMAL(10,2),
            lz_lcra DECIMAL(10,2),
            lz_north DECIMAL(10,2),
            lz_raybn DECIMAL(10,2),
            lz_south DECIMAL(10,2),
            lz_west DECIMAL(10,2),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(oper_day, interval_ending)
        );
        
        CREATE INDEX IF NOT EXISTS idx_ercot_settlement_timestamp ON ercot_settlement_prices(timestamp);
        CREATE INDEX IF NOT EXISTS idx_ercot_settlement_oper_day ON ercot_settlement_prices(oper_day);
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Price table created successfully")
        
    except Exception as e:
        logger.error(f"Error creating price table: {str(e)}")
        raise

def clear_price_table():
    """Clear all data from the price table."""
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST', 'dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com'),
            database=os.environ.get('DB_NAME', 'analytics'),
            user=os.environ.get('DB_USER', 'dbuser'),
            password=os.environ.get('DB_PASSWORD', 'Superman1262!')
        )
        cursor = conn.cursor()
        
        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM ercot_settlement_prices;")
        count_before = cursor.fetchone()[0]
        
        # Clear the table
        cursor.execute("DELETE FROM ercot_settlement_prices;")
        
        # Get count after deletion
        cursor.execute("SELECT COUNT(*) FROM ercot_settlement_prices;")
        count_after = cursor.fetchone()[0]
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Table cleared successfully. Deleted {count_before} rows, {count_after} remaining")
        
    except Exception as e:
        logger.error(f"Error clearing price table: {str(e)}")
        raise

def get_existing_records(target_date):
    """Get existing records for a specific date to avoid duplicates."""
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST', 'dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com'),
            database=os.environ.get('DB_NAME', 'analytics'),
            user=os.environ.get('DB_USER', 'dbuser'),
            password=os.environ.get('DB_PASSWORD', 'Superman1262!')
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT interval_ending 
            FROM ercot_settlement_prices 
            WHERE oper_day = %s
        """, (target_date,))
        
        existing_intervals = set(row[0] for row in cursor.fetchall())
        cursor.close()
        conn.close()
        
        logger.info(f"Found {len(existing_intervals)} existing records for {target_date}")
        return existing_intervals
        
    except Exception as e:
        logger.error(f"Error getting existing records: {str(e)}")
        return set()

def parse_time_to_24h(time_str):
    """Convert HHMM time string to HH:MM:SS format, handling 2400 as 0000."""
    try:
        # Handle special case of 2400 (midnight)
        if time_str == '2400':
            return "00:00:00"
        
        # Pad with zeros if needed and format as HH:MM:SS
        time_str = time_str.zfill(4)
        hours = time_str[:2]
        minutes = time_str[2:]
        
        # Validate hours and minutes
        if int(hours) > 23 or int(minutes) > 59:
            logger.warning(f"Invalid time format: {time_str}")
            return None
            
        return f"{hours}:{minutes}:00"
    except Exception as e:
        logger.error(f"Error parsing time {time_str}: {e}")
        return None

def scrape_ercot_prices_for_date(target_date, check_existing=True):
    """Scrape ERCOT settlement point prices for a specific date."""
    try:
        date_str = target_date.strftime("%Y%m%d")
        url = f"https://www.ercot.com/content/cdr/html/{date_str}_real_time_spp.html"
        logger.info(f"Fetching price data from {url}")
        
        # Get existing records if we need to check
        existing_intervals = set()
        if check_existing:
            existing_intervals = get_existing_records(target_date.date())
        
        # Fetch the data
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch data from {url}: {e}")
            return 0
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all table rows
        rows = soup.find_all('tr')
        logger.info(f"Found {len(rows)} table rows")
        
        # Connect to database
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST', 'dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com'),
            database=os.environ.get('DB_NAME', 'analytics'),
            user=os.environ.get('DB_USER', 'dbuser'),
            password=os.environ.get('DB_PASSWORD', 'Superman1262!')
        )
        cursor = conn.cursor()
        
        # Process data rows
        data_rows = []
        skipped_existing = 0
        skipped_header = 0
        
        for row in rows:
            # Get all cells in this row
            cells = row.find_all(['td', 'th'])
            
            if len(cells) < 17:  # Should have at least 17 columns
                continue
            
            # Extract cell text values
            cell_values = [cell.get_text().strip() for cell in cells]
            
            # Skip header rows (look for column names)
            if any(header in cell_values[0].upper() for header in ['OPER', 'DAY', 'INTERVAL']):
                skipped_header += 1
                continue
            
            # Skip empty or invalid rows
            if not cell_values[0] or '/' not in cell_values[0]:
                continue
            
            try:
                # Parse date (first column) - format: MM/DD/YYYY
                date_str_raw = cell_values[0]
                oper_day = datetime.strptime(date_str_raw, '%m/%d/%Y').date()
                
                # Parse time (second column) - format: HHMM
                time_str_raw = cell_values[1]
                time_formatted = parse_time_to_24h(time_str_raw)
                if not time_formatted:
                    continue
                
                # Handle 2400 time - it represents 00:00 of the next day
                if time_str_raw == '2400':
                    # Move to next day and use 00:00:00
                    oper_day = oper_day + timedelta(days=1)
                    time_formatted = "00:00:00"
                
                interval_time = datetime.strptime(time_formatted, '%H:%M:%S').time()
                
                # Skip if we already have this record
                if check_existing and interval_time in existing_intervals:
                    skipped_existing += 1
                    continue
                
                # Create full timestamp
                timestamp = datetime.combine(oper_day, interval_time)
                
                # Parse price columns (columns 2-16)
                # Expected column order: Oper Day, Interval Ending, HB_BUSAVG, HB_HOUSTON, HB_HUBAVG, 
                # HB_NORTH, HB_PAN, HB_SOUTH, HB_WEST, LZ_AEN, LZ_CPS, LZ_HOUSTON, LZ_LCRA, 
                # LZ_NORTH, LZ_RAYBN, LZ_SOUTH, LZ_WEST
                
                def safe_float(value):
                    """Safely convert string to float, handling empty/invalid values."""
                    try:
                        if value and value != '-' and value.strip():
                            return float(value.strip())
                        return None
                    except (ValueError, AttributeError):
                        return None
                
                row_data = {
                    'timestamp': timestamp,
                    'oper_day': oper_day,
                    'interval_ending': time_formatted,
                    'hb_busavg': safe_float(cell_values[2]) if len(cell_values) > 2 else None,
                    'hb_houston': safe_float(cell_values[3]) if len(cell_values) > 3 else None,
                    'hb_hubavg': safe_float(cell_values[4]) if len(cell_values) > 4 else None,
                    'hb_north': safe_float(cell_values[5]) if len(cell_values) > 5 else None,
                    'hb_pan': safe_float(cell_values[6]) if len(cell_values) > 6 else None,
                    'hb_south': safe_float(cell_values[7]) if len(cell_values) > 7 else None,
                    'hb_west': safe_float(cell_values[8]) if len(cell_values) > 8 else None,
                    'lz_aen': safe_float(cell_values[9]) if len(cell_values) > 9 else None,
                    'lz_cps': safe_float(cell_values[10]) if len(cell_values) > 10 else None,
                    'lz_houston': safe_float(cell_values[11]) if len(cell_values) > 11 else None,
                    'lz_lcra': safe_float(cell_values[12]) if len(cell_values) > 12 else None,
                    'lz_north': safe_float(cell_values[13]) if len(cell_values) > 13 else None,
                    'lz_raybn': safe_float(cell_values[14]) if len(cell_values) > 14 else None,
                    'lz_south': safe_float(cell_values[15]) if len(cell_values) > 15 else None,
                    'lz_west': safe_float(cell_values[16]) if len(cell_values) > 16 else None
                }
                
                data_rows.append(row_data)
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse row with {len(cell_values)} cells: {cell_values[:3]}... Error: {e}")
                continue
        
        logger.info(f"Parsed {len(data_rows)} new price data rows (skipped {skipped_existing} existing, {skipped_header} headers)")
        
        # Insert data into database using ON CONFLICT to handle duplicates
        insert_sql = """
        INSERT INTO ercot_settlement_prices 
        (timestamp, oper_day, interval_ending, hb_busavg, hb_houston, hb_hubavg, hb_north, 
         hb_pan, hb_south, hb_west, lz_aen, lz_cps, lz_houston, lz_lcra, lz_north, 
         lz_raybn, lz_south, lz_west)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (oper_day, interval_ending) 
        DO UPDATE SET
            timestamp = EXCLUDED.timestamp,
            hb_busavg = EXCLUDED.hb_busavg,
            hb_houston = EXCLUDED.hb_houston,
            hb_hubavg = EXCLUDED.hb_hubavg,
            hb_north = EXCLUDED.hb_north,
            hb_pan = EXCLUDED.hb_pan,
            hb_south = EXCLUDED.hb_south,
            hb_west = EXCLUDED.hb_west,
            lz_aen = EXCLUDED.lz_aen,
            lz_cps = EXCLUDED.lz_cps,
            lz_houston = EXCLUDED.lz_houston,
            lz_lcra = EXCLUDED.lz_lcra,
            lz_north = EXCLUDED.lz_north,
            lz_raybn = EXCLUDED.lz_raybn,
            lz_south = EXCLUDED.lz_south,
            lz_west = EXCLUDED.lz_west,
            created_at = CURRENT_TIMESTAMP
        """
        
        inserted_count = 0
        for row_data in data_rows:
            try:
                cursor.execute(insert_sql, (
                    row_data.get('timestamp'),
                    row_data.get('oper_day'),
                    row_data.get('interval_ending'),
                    row_data.get('hb_busavg'),
                    row_data.get('hb_houston'),
                    row_data.get('hb_hubavg'),
                    row_data.get('hb_north'),
                    row_data.get('hb_pan'),
                    row_data.get('hb_south'),
                    row_data.get('hb_west'),
                    row_data.get('lz_aen'),
                    row_data.get('lz_cps'),
                    row_data.get('lz_houston'),
                    row_data.get('lz_lcra'),
                    row_data.get('lz_north'),
                    row_data.get('lz_raybn'),
                    row_data.get('lz_south'),
                    row_data.get('lz_west')
                ))
                inserted_count += 1
            except Exception as e:
                logger.warning(f"Could not insert row: {e}")
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully stored {inserted_count} price records for {date_str}")
        return inserted_count
        
    except Exception as e:
        logger.error(f"Error scraping prices for {target_date}: {str(e)}")
        return 0

def scrape_today_only():
    """Scrape only today's data for regular updates - using ERCOT's timezone."""
    logger.info("Scraping today's price data (in Central Time)...")
    
    # Get current time in Central timezone
    central_today = get_ercot_now()
    
    logger.info(f"Using ERCOT date: {central_today.strftime('%Y-%m-%d')} (Central Time)")
    return scrape_ercot_prices_for_date(central_today, check_existing=True)

def scrape_latest_available():
    """Scrape the most recent available data, trying today first, then yesterday - in Central Time."""
    logger.info("Scraping latest available price data (in Central Time)...")
    
    # Get current time in Central timezone
    central_now = get_ercot_now()
    
    # Try today first
    logger.info(f"Attempting to scrape data for {central_now.strftime('%Y-%m-%d')} (Central Time)")
    
    inserted_today = scrape_ercot_prices_for_date(central_now, check_existing=True)
    
    if inserted_today > 0:
        logger.info(f"Successfully scraped {inserted_today} records for today")
        return inserted_today
    
    # If today fails, try yesterday
    yesterday = central_now - timedelta(days=1)
    logger.info(f"No data available for today, trying {yesterday.strftime('%Y-%m-%d')} (Central Time)")
    
    inserted_yesterday = scrape_ercot_prices_for_date(yesterday, check_existing=True)
    
    if inserted_yesterday > 0:
        logger.info(f"Successfully scraped {inserted_yesterday} records for yesterday")
        return inserted_yesterday
    
    # If both fail, try 2 days ago
    two_days_ago = central_now - timedelta(days=2)
    logger.info(f"No data available for yesterday, trying {two_days_ago.strftime('%Y-%m-%d')} (Central Time)")
    
    inserted_two_days = scrape_ercot_prices_for_date(two_days_ago, check_existing=True)
    
    if inserted_two_days > 0:
        logger.info(f"Successfully scraped {inserted_two_days} records for two days ago")
        return inserted_two_days
    
    logger.warning("No data available for today, yesterday, or two days ago")
    return 0

def backfill_historical_data():
    """Backfill the last 5 days + today of price data - using Central Time."""
    logger.info("Starting historical data backfill (in Central Time)...")
    
    # Get current time in Central timezone
    central_today = get_ercot_now()
    dates_to_scrape = []
    
    for i in range(6):  # 0-5 = 6 days total (5 days ago + today)
        date_to_scrape = central_today - timedelta(days=i)
        dates_to_scrape.append(date_to_scrape)
    
    # Reverse to scrape oldest first
    dates_to_scrape.reverse()
    
    total_inserted = 0
    
    for target_date in dates_to_scrape:
        logger.info(f"Processing {target_date.strftime('%Y-%m-%d')} (Central Time)")
        inserted = scrape_ercot_prices_for_date(target_date, check_existing=True)
        total_inserted += inserted
    
    logger.info(f"Historical backfill completed. Total records inserted: {total_inserted}")
    return total_inserted

if __name__ == "__main__":
    # Create table first
    create_price_table()
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--clear':
        # Clear the table
        clear_price_table()
    elif len(sys.argv) > 1 and sys.argv[1] == '--backfill':
        # Run historical backfill
        backfill_historical_data()
    elif len(sys.argv) > 1 and sys.argv[1] == '--fallback':
        # Run latest available data scrape
        scrape_latest_available()
    else:
        # Run regular daily scrape using Central Time
        scrape_today_only()
