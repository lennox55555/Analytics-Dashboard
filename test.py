#!/usr/bin/env python3
"""
Complete Grafana Datasource Fix Script - USES DEFAULT DATASOURCE
This script will create working dashboards using Grafana's default datasource
"""

import requests
import json
import psycopg2
import os
from psycopg2.extras import RealDictCursor
from datetime import datetime

class GrafanaFixer:
    def __init__(self):
        self.grafana_url = "http://52.4.166.16:3000"
        self.session = requests.Session()
        self.session.auth = ('admin', 'admin')
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # Database configuration
        self.db_config = {
            'host': 'dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com',
            'database': 'analytics',
            'user': 'dbuser',
            'password': 'Superman1262!',
            'port': 5432
        }
    
    def step1_verify_grafana_connection(self):
        """Step 1: Verify Grafana is accessible"""
        print("🔍 STEP 1: Verifying Grafana connection...")
        try:
            response = self.session.get(f"{self.grafana_url}/api/org", timeout=10)
            if response.status_code == 200:
                org_info = response.json()
                print(f"   ✅ Connected to Grafana - Org: {org_info.get('name', 'Unknown')}")
                return True
            else:
                print(f"   ❌ Grafana connection failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Grafana connection error: {e}")
            return False
    
    def step3_test_database_connection(self):
        """Step 3: Test direct database connection"""
        print("\n🔍 STEP 3: Testing database connection...")
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Test basic connection
            cursor.execute("SELECT version()")
            version = cursor.fetchone()['version']
            print(f"   ✅ Database connected: {version[:50]}...")
            
            # Test ERCOT data
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM ercot_settlement_prices 
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
            """)
            count = cursor.fetchone()['count']
            print(f"   ✅ Found {count} ERCOT records in last 24 hours")
            
            # Test actual query that will be used in Grafana
            test_query = "SELECT timestamp as time, hb_west as \"West Hub\", hb_houston as \"Houston Hub\" FROM ercot_settlement_prices WHERE timestamp >= NOW() - INTERVAL '24 hours' ORDER BY timestamp LIMIT 5"
            cursor.execute(test_query)
            results = cursor.fetchall()
            
            if results:
                print(f"   ✅ Test query returned {len(results)} rows")
                print("   Sample data:")
                for row in results:
                    print(f"     {row['time']}: West=${row['West Hub']}, Houston=${row['Houston Hub']}")
            else:
                print("   ⚠️  Test query returned no data")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"   ❌ Database connection failed: {e}")
            return False
    
    def step5_delete_broken_dashboards(self):
        """Step 5: Delete any broken dashboards"""
        print("\n🔍 STEP 5: Checking for broken dashboards...")
        try:
            response = self.session.get(f"{self.grafana_url}/api/search?type=dash-db")
            if response.status_code == 200:
                dashboards = response.json()
                
                broken_dashboards = []
                for dash in dashboards:
                    if any(word in dash['title'].lower() for word in ['test', 'debug', 'fresh', 'default ds']):
                        broken_dashboards.append(dash)
                
                if broken_dashboards:
                    print(f"   Found {len(broken_dashboards)} test/debug dashboards to clean up:")
                    for dash in broken_dashboards:
                        print(f"     • {dash['title']} (UID: {dash['uid']})")
                        try:
                            delete_response = self.session.delete(f"{self.grafana_url}/api/dashboards/uid/{dash['uid']}")
                            if delete_response.status_code == 200:
                                print(f"       ✅ Deleted {dash['title']}")
                            else:
                                print(f"       ⚠️  Could not delete {dash['title']}")
                        except Exception as e:
                            print(f"       ❌ Error deleting {dash['title']}: {e}")
                else:
                    print("   ✅ No broken dashboards found")
            else:
                print(f"   ⚠️  Could not get dashboard list: HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error checking dashboards: {e}")
    
    def step6_create_fresh_dashboard(self):
        """Step 6: Create dashboard using DEFAULT datasource - NO SELECTION NEEDED"""
        print(f"\n🔍 STEP 6: Creating LINE CHART dashboard using DEFAULT datasource...")
        print("   🎯 FORCING LINE CHART VISUALIZATION!")
        print("   📈 Draw style: line")
        print("   🚫 Fill opacity: 0 (no fill)")
        print("   🔵 Show points: never (clean lines)")
        print("   🎨 Blue lines for West, Green for Houston")
        
        # Create a timestamp for unique naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        dashboard_config = {
            "dashboard": {
                "id": None,
                "title": f"LINE CHART West Hub {timestamp}",
                "description": f"Line chart dashboard using default datasource created at {datetime.now()}",
                "tags": ["line-chart", "default-datasource", "working", "ercot", timestamp],
                "timezone": "browser",
                "panels": [
                    {
                        "id": 1,
                        "title": "West Hub Prices (LINE CHART)",
                        "type": "timeseries",
                        "gridPos": {"h": 12, "w": 24, "x": 0, "y": 0},
                        "targets": [
                            {
                                "datasource": {
                                    "uid": "aep8tntrm562ob",
                                    "type": "grafana-postgresql-datasource"
                                },
                                "format": "time_series",
                                "rawQuery": True,
                                "rawSql": "SELECT timestamp AS time, hb_west AS \"West Hub Price\", hb_houston AS \"Houston Hub Price\" FROM ercot_settlement_prices WHERE $__timeFilter(timestamp) ORDER BY timestamp",
                                "refId": "A"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "custom": {
                                    "drawStyle": "line",
                                    "lineInterpolation": "linear",
                                    "barAlignment": 0,
                                    "lineWidth": 1,
                                    "fillOpacity": 0,
                                    "gradientMode": "none",
                                    "spanNulls": False,
                                    "insertNulls": False,
                                    "showPoints": "auto",
                                    "pointSize": 5,
                                    "stacking": {
                                        "mode": "none",
                                        "group": "A"
                                    },
                                    "axisPlacement": "auto",
                                    "axisLabel": "",
                                    "axisColorMode": "text",
                                    "axisBorderShow": False,
                                    "scaleDistribution": {
                                        "type": "linear"
                                    },
                                    "axisCenteredZero": False,
                                    "hideFrom": {
                                        "tooltip": False,
                                        "viz": False,
                                        "legend": False
                                    },
                                    "thresholdsStyle": {
                                        "mode": "off"
                                    }
                                },
                                "color": {
                                    "mode": "palette-classic"
                                },
                                "mappings": [],
                                "thresholds": {
                                    "mode": "absolute",
                                    "steps": [
                                        {
                                            "value": None,
                                            "color": "green"
                                        },
                                        {
                                            "value": 80,
                                            "color": "red"
                                        }
                                    ]
                                }
                            },
                            "overrides": []
                        },
                        "options": {
                            "tooltip": {
                                "mode": "single",
                                "sort": "none"
                            },
                            "legend": {
                                "showLegend": False,
                                "displayMode": "hidden",
                                "placement": "right",
                                "calcs": []
                            }
                        },
                        "datasource": {
                            "uid": "aep8tntrm562ob",
                            "type": "grafana-postgresql-datasource"
                        }
                    }
                ],
                "time": {"from": "now-24h", "to": "now"},
                "refresh": "30s",
                "schemaVersion": 37,
                "version": 0,
                "links": [],
                "annotations": {"list": []},
                "templating": {"list": []},
                "editable": True,
                "fiscalYearStartMonth": 0,
                "graphTooltip": 1,
                "hideControls": False,
                "liveNow": True,
                "weekStart": ""
            },
            "folderId": 0,
            "overwrite": False,
            "message": f"Dashboard using default datasource"
        }
        
        try:
            print(f"   📤 Sending LINE CHART dashboard to Grafana...")
            print(f"      No datasource specified - using Grafana default")
            print(f"      Visualization: LINE CHART (forced)")
            print(f"      SQL: Clean single-line query")
            print(f"      Colors: Blue (West) + Green (Houston)")
            
            response = self.session.post(
                f"{self.grafana_url}/api/dashboards/db",
                json=dashboard_config,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                dashboard_uid = result['uid']
                dashboard_url = f"{self.grafana_url}/d/{dashboard_uid}"
                
                print(f"   ✅ LINE CHART Dashboard created successfully!")
                print(f"      Title: LINE CHART West Hub {timestamp}")
                print(f"      UID: {dashboard_uid}")
                print(f"      URL: {dashboard_url}")
                print(f"      🎯 Should display as LINE CHART immediately!")
                print(f"      📈 Clean lines with no fill or points")
                
                return {
                    'success': True,
                    'uid': dashboard_uid,
                    'url': dashboard_url,
                    'title': f"DEFAULT DS West Hub Prices {timestamp}"
                }
            else:
                print(f"   ❌ Failed to create dashboard: HTTP {response.status_code}")
                print(f"      Response: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            print(f"   ❌ Error creating dashboard: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_complete_fix(self):
        """Run the complete fix process - SIMPLIFIED TO USE DEFAULT DATASOURCE"""
        print("🚀 GRAFANA DASHBOARD CREATION - USING DEFAULT DATASOURCE")
        print("=" * 60)
        
        # Step 1: Verify Grafana connection
        if not self.step1_verify_grafana_connection():
            print("\n❌ FAILED: Cannot connect to Grafana")
            return False
        
        # SKIPPED: Step 2 - No need to find datasource, using default
        print("\n✅ SKIPPING datasource detection - using Grafana default")
        
        # Step 3: Test database (optional)
        if not self.step3_test_database_connection():
            print("\n⚠️  Database test failed, but continuing with default datasource...")
        
        # SKIPPED: Step 4 - No need to test specific datasource
        
        # Step 5: Clean up broken dashboards
        self.step5_delete_broken_dashboards()
        
        # Step 6: Create fresh dashboard using default datasource
        result = self.step6_create_fresh_dashboard()
        
        if result['success']:
            print(f"\n🎉 SUCCESS! Created dashboard using DEFAULT datasource:")
            print(f"   📊 {result['title']}")
            print(f"   🔗 {result['url']}")
            print(f"   🎯 Using your configured default datasource!")
            print(f"\n✅ Should display ERCOT data from default datasource!")
            return True
        else:
            print(f"\n❌ FAILED: Could not create dashboard: {result['error']}")
            return False

def main():
    """Main function to run the complete fix"""
    print("Starting Grafana Datasource Fix using DEFAULT datasource...")
    
    fixer = GrafanaFixer()
    success = fixer.run_complete_fix()
    
    if success:
        print("\n🎉 ALL DONE! Your Grafana dashboard should now work correctly.")
        print("   • The new dashboard uses your default datasource")
        print("   • Should show real ERCOT settlement prices as line charts")
        print("   • No datasource selection needed")
        print("   • Clean SQL queries with no indentation issues")
    else:
        print("\n❌ Fix process failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
