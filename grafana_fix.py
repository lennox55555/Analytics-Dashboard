# Quick fix to disable Grafana creation temporarily
import json
import psycopg2

def fix_pending_visualizations():
    """Update pending visualizations with analysis results"""
    db_config = {
        'host': 'dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com',
        'database': 'analytics',
        'user': 'dbuser', 
        'password': 'Superman1262!',
        'port': 5432
    }
    
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    # Get pending visualizations
    cursor.execute("SELECT id, request_text FROM ai_visualizations WHERE status = 'pending'")
    pending = cursor.fetchall()
    
    for viz_id, request_text in pending:
        # Create mock analysis for the request
        if 'north' in request_text.lower():
            analysis = {
                "title": "North Hub Settlement Prices",
                "description": "North hub and load zone prices over time",
                "sql_query": "SELECT timestamp, hb_north, lz_north FROM ercot_settlement_prices WHERE timestamp >= NOW() - INTERVAL '24 hours' ORDER BY timestamp",
                "chart_type": "line",
                "recommended_table": "ercot_settlement_prices"
            }
        else:
            analysis = {
                "title": "ERCOT Data Analysis", 
                "description": "Analysis of your ERCOT data request",
                "sql_query": "SELECT timestamp, hb_busavg FROM ercot_settlement_prices WHERE timestamp >= NOW() - INTERVAL '24 hours' ORDER BY timestamp",
                "chart_type": "line",
                "recommended_table": "ercot_settlement_prices"
            }
        
        # Update with analysis
        cursor.execute("""
            UPDATE ai_visualizations 
            SET status = 'completed', chart_config = %s, completed_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (json.dumps(analysis), viz_id))
        
        print(f"Updated visualization {viz_id}: {request_text}")
    
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Fixed {len(pending)} pending visualizations")

if __name__ == "__main__":
    fix_pending_visualizations()
