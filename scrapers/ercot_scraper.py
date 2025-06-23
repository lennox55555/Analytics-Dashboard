import requests
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db_connection import get_db_connection
from bs4 import BeautifulSoup
from datetime import datetime
import re
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()


def scrape_ercot():
    """Scrape ERCOT capacity monitor data and store in database with enhanced error handling."""
    conn = None
    cursor = None
    
    try:
        # Fetch the ERCOT data with timeout and retry logic
        url = "https://www.ercot.com/content/cdr/html/as_capacity_monitor.html"
        logger.info(f"Fetching data from {url}")
        
        # Add timeout and headers to prevent blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            response = requests.get(url, timeout=30, headers=headers)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout occurred while fetching data from {url}")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while fetching data: {e}")
            return False
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {response.status_code} while fetching data: {e}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while fetching data: {e}")
            return False
        
        # Parse the HTML with error handling
        try:
            if not response.text:
                logger.error("Empty response received from ERCOT")
                return False
                
            soup = BeautifulSoup(response.text, 'html.parser')
            if not soup:
                logger.error("Failed to parse HTML content")
                return False
                
        except Exception as e:
            logger.error(f"Error parsing HTML content: {e}")
            return False
        
        # Initialize data structure
        data = []
        current_category = None
        parsing_errors = 0
        
        try:
            # Find all table rows
            rows = soup.find_all('tr')
            
            if not rows:
                logger.warning("No table rows found in ERCOT page")
                return False
                
            logger.info(f"Found {len(rows)} table rows to process")
            
            for i, row in enumerate(rows):
                try:
                    # Check if this is a header row (category)
                    header_cells = row.find_all('td', class_='headerValueClass')
                    if header_cells and len(header_cells) > 0:
                        category_text = header_cells[0].text.strip() if header_cells[0].text else None
                        if category_text:
                            current_category = category_text
                            logger.debug(f"Found category: {current_category}")
                        continue
                    
                    # Get the subcategory and value from regular rows
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        try:
                            subcategory = cells[0].text.strip() if cells[0].text else ''
                            value_text = cells[1].text.strip() if cells[1].text else ''
                            
                            if not subcategory or not value_text:
                                continue
                                
                            # Clean and convert the value
                            value_text = value_text.replace(',', '')
                            
                            # Extract numeric value and unit
                            match = re.match(r'(-?\d+\.?\d*)\s*(\w*)', value_text)
                            if match:
                                try:
                                    value = float(match.group(1))
                                    unit = match.group(2) if match.group(2) else 'MW'
                                    
                                    # Validate the parsed data
                                    if current_category and subcategory:
                                        # Add to our data list
                                        data.append({
                                            'category': current_category,
                                            'subcategory': subcategory,
                                            'value': value,
                                            'unit': unit,
                                            'timestamp': datetime.utcnow()
                                        })
                                    else:
                                        logger.debug(f"Skipping row {i}: missing category or subcategory")
                                        
                                except ValueError as e:
                                    logger.warning(f"Could not convert value '{match.group(1)}' to float: {e}")
                                    parsing_errors += 1
                                    continue
                            else:
                                logger.debug(f"No numeric value found in '{value_text}'")
                                
                        except Exception as e:
                            logger.warning(f"Error processing cells in row {i}: {e}")
                            parsing_errors += 1
                            continue
                            
                except Exception as e:
                    logger.warning(f"Error processing row {i}: {e}")
                    parsing_errors += 1
                    continue
                    
        except Exception as e:
            logger.error(f"Error during data parsing: {e}")
            return False
        
        if parsing_errors > 0:
            logger.warning(f"Encountered {parsing_errors} parsing errors while processing data")
            
        if not data:
            logger.error("No data points were successfully parsed from ERCOT")
            return False
            
        logger.info(f"Parsed {len(data)} data points from ERCOT")
        
        # Connect to the database using shared connection
        try:
            conn = get_db_connection()
            if not conn:
                logger.error("Failed to get database connection")
                return False
                
            cursor = conn.cursor()
            
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return False
        
        # Insert data into the database with error handling for each record
        inserted_count = 0
        failed_count = 0
        
        try:
            for i, item in enumerate(data):
                try:
                    # Validate item data before insertion
                    if not all(key in item for key in ['timestamp', 'category', 'subcategory', 'value', 'unit']):
                        logger.warning(f"Item {i} missing required fields: {item}")
                        failed_count += 1
                        continue
                        
                    # Additional validation
                    if not isinstance(item['value'], (int, float)):
                        logger.warning(f"Item {i} has invalid value type: {type(item['value'])}")
                        failed_count += 1
                        continue
                        
                    cursor.execute(
                        """
                        INSERT INTO ercot_capacity_monitor 
                        (timestamp, category, subcategory, value, unit) 
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            item['timestamp'],
                            item['category'],
                            item['subcategory'],
                            item['value'],
                            item['unit']
                        )
                    )
                    inserted_count += 1
                    
                except Exception as e:
                    logger.error(f"Error inserting item {i}: {e}")
                    logger.error(f"Failed item data: {item}")
                    failed_count += 1
                    continue
            
            # Commit all successful insertions
            conn.commit()
            
            logger.info(f"Successfully stored {inserted_count} data points in the database")
            if failed_count > 0:
                logger.warning(f"Failed to store {failed_count} data points")
                
            return inserted_count > 0
            
        except Exception as e:
            logger.error(f"Database transaction error: {e}")
            try:
                conn.rollback()
                logger.info("Database transaction rolled back")
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            return False
            
    except ImportError as e:
        logger.error(f"Missing required libraries: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during ERCOT scraping: {e}")
        return False
    finally:
        # Ensure database resources are cleaned up
        try:
            if cursor:
                cursor.close()
        except Exception as e:
            logger.error(f"Error closing cursor: {e}")
        try:
            if conn:
                conn.close()
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")


if __name__ == "__main__":
    try:
        success = scrape_ercot()
        if success:
            logger.info("ERCOT scraping completed successfully")
            exit(0)
        else:
            logger.error("ERCOT scraping failed")
            exit(1)
    except KeyboardInterrupt:
        logger.info("ERCOT scraping interrupted by user")
        exit(1)
    except Exception as e:
        logger.error(f"Fatal error in ERCOT scraper: {e}")
        exit(1)
