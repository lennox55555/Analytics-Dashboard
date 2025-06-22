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
    """Scrape ERCOT capacity monitor data and store in database."""
    try:
        # Fetch the ERCOT data
        url = "https://www.ercot.com/content/cdr/html/as_capacity_monitor.html"
        logger.info(f"Fetching data from {url}")
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Initialize data structure
        data = []
        current_category = None
        
        # Find all table rows
        rows = soup.find_all('tr')
        
        for row in rows:
            # Check if this is a header row (category)
            header_cells = row.find_all('td', class_='headerValueClass')
            if header_cells and len(header_cells) > 0:
                current_category = header_cells[0].text.strip()
                continue
            
            # Get the subcategory and value from regular rows
            cells = row.find_all('td')
            if len(cells) >= 2:
                subcategory = cells[0].text.strip()
                value_text = cells[1].text.strip()
                
                # Clean and convert the value
                value_text = value_text.replace(',', '')
                
                # Extract numeric value and unit
                match = re.match(r'(-?\d+\.?\d*)\s*(\w*)', value_text)
                if match:
                    value = float(match.group(1))
                    unit = match.group(2) if match.group(2) else 'MW'
                    
                    # Add to our data list
                    data.append({
                        'category': current_category,
                        'subcategory': subcategory,
                        'value': value,
                        'unit': unit,
                        'timestamp': datetime.utcnow()
                    })
        
        logger.info(f"Parsed {len(data)} data points from ERCOT")
        
        # Connect to the database using shared connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert data into the database
        for item in data:
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
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully stored {len(data)} data points in the database")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")


if __name__ == "__main__":
    scrape_ercot()
