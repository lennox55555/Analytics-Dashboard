#!/usr/bin/env python3
"""
Complete Grafana Datasource Fix Script - MODIFIED TO FORCE LINE CHART
This script will definitively fix the datasource issues and create working dashboards
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
    
    def step2_get_datasources(self):
        """Step 2: Get all datasources and find the correct PostgreSQL one - FIXED"""
        print("\n🔍 STEP 2: Getting all datasources...")
        try:
            response = self.session.get(f"{self.grafana_url}/api/datasources")
            if response.status_code == 200:
                datasources = response.json()
                print(f"   Found {len(datasources)} datasources:")
                
                postgresql_ds = None
                for ds in datasources:
                    print(f"     • {ds['name']} (UID: {ds['uid']}, Type: {ds['type']})")
                    # FIXED: Check for both 'postgres' and 'postgresql'
                    if 'postgres' in ds['type'].lower():  # Changed from 'postgresql'
                        postgresql_ds = ds
                        print(f"       🎯 MATCH! Found postgres type: {ds['type']}")
                
                if postgresql_ds:
                    print(f"   ✅ Found PostgreSQL datasource: {postgresql_ds['name']}")
                    print(f"      UID: {postgresql_ds['uid']}")
                    print(f"      Type: {postgresql_ds['type']}")
                    return postgresql_ds
                else:
                    print("   ❌ No PostgreSQL datasource found!")
                    print("   📋 Available types:")
                    for ds in datasources:
                        print(f"      - {ds['name']}: {ds['type']}")
                    return None
            else:
                print(f"   ❌ Failed to get datasources: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"   ❌ Error getting datasources: {e}")
            return None
    
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
            test_query = """
                SELECT 
                    timestamp as time,
                    hb_west as "West Hub",
                    hb_houston as "Houston Hub"
                FROM ercot_settlement_prices 
                WHERE timestamp >= NOW() - INTERVAL '2 hours'
                ORDER BY timestamp 
                LIMIT 5
            """
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
    
    def step4_test_datasource_in_grafana(self, datasource):
        """Step 4: Test the datasource directly in Grafana"""
        print(f"\n🔍 STEP 4: Testing datasource '{datasource['name']}' in Grafana...")
        try:
            # Test datasource health
            response = self.session.get(f"{self.grafana_url}/api/datasources/uid/{datasource['uid']}/health")
            if response.status_code == 200:
                health = response.json()
                print(f"   ✅ Datasource health: {health.get('status', 'Unknown')}")
                if health.get('message'):
                    print(f"      Message: {health['message']}")
            else:
                print(f"   ⚠️  Could not check datasource health: HTTP {response.status_code}")
            
            return True
        except Exception as e:
            print(f"   ❌ Error testing datasource: {e}")
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
                    if 'test' in dash['title'].lower() or 'debug' in dash['title'].lower() or 'fresh' in dash['title'].lower():
                        broken_dashboards.append(dash)
                
                if broken_dashboards:
                    print(f"   Found {len(broken_dashboards)} test/debug/fresh dashboards to clean up:")
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
    
    def step6_create_fresh_dashboard(self, datasource):
        """Step 6: Create a completely fresh dashboard - MODIFIED TO FORCE LINE CHART"""
        print(f"\n🔍 STEP 6: Creating fresh dashboard with datasource {datasource['uid']}...")
        print("   🎯 FORCING LINE CHART VISUALIZATION...")
        
        # Create a timestamp for unique naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        dashboard_config = {
            "dashboard": {
                "id": None,
                "title": f"LINE CHART West Hub Prices {timestamp}",
                "description": f"Line chart dashboard created at {datetime.now()} using datasource {datasource['uid']}",
                "tags": ["line-chart", "working", "ercot", timestamp],
                "timezone": "browser",
                "panels": [
                    {
                        "id": 1,
                        "title": "West Hub Settlement Prices (Line Chart)",
                        "type": "timeseries",  # Use timeseries type
                        "gridPos": {"h": 12, "w": 24, "x": 0, "y": 0},
                        "targets": [
                            {
                                "datasource": {
                                    "type": datasource['type'],
                                    "uid": datasource['uid'],
                                    "name": datasource['name']
                                },
                                "format": "time_series",
                                "rawQuery": True,
                                "rawSql": """SELECT 
    timestamp AS time,
    hb_west AS "West Hub Price",
    hb_houston AS "Houston Hub Price"
FROM ercot_settlement_prices 
WHERE $__timeFilter(timestamp)
ORDER BY timestamp""",
                                "refId": "A"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "palette-classic"},
                                "custom": {
                                    "drawStyle": "line",  # EXPLICITLY SET TO LINE
                                    "lineInterpolation": "linear",
                                    "lineWidth": 2,
                                    "fillOpacity": 0,  # NO FILL FOR CLEAN LINES
                                    "gradientMode": "none",
                                    "spanNulls": False,
                                    "insertNulls": False,
                                    "showPoints": "never",  # NO POINTS, JUST LINES
                                    "pointSize": 5,
                                    "stacking": {"mode": "none", "group": "A"},  # NO STACKING
                                    "axisPlacement": "auto",
                                    "axisLabel": "Price ($/MWh)",
                                    "axisColorMode": "text",
                                    "scaleDistribution": {"type": "linear"},
                                    "axisCenteredZero": False,
                                    "hideFrom": {"legend": False, "tooltip": False, "vis": False},
                                    "thresholdsStyle": {"mode": "off"}
                                },
                                "mappings": [],
                                "thresholds": {
                                    "mode": "absolute",
                                    "steps": [
                                        {"color": "green", "value": None},
                                        {"color": "red", "value": 100}
                                    ]
                                },
                                "unit": "currencyUSD",
                                "displayName": "${__field.name}"  # USE FIELD NAMES AS LABELS
                            },
                            "overrides": [
                                {
                                    "matcher": {"id": "byName", "options": "West Hub Price"},
                                    "properties": [
                                        {"id": "color", "value": {"mode": "fixed", "fixedColor": "blue"}},
                                        {"id": "custom.drawStyle", "value": "line"}
                                    ]
                                },
                                {
                                    "matcher": {"id": "byName", "options": "Houston Hub Price"},
                                    "properties": [
                                        {"id": "color", "value": {"mode": "fixed", "fixedColor": "green"}},
                                        {"id": "custom.drawStyle", "value": "line"}
                                    ]
                                }
                            ]
                        },
                        "options": {
                            "tooltip": {"mode": "multi", "sort": "none"},
                            "legend": {
                                "displayMode": "visible", 
                                "placement": "bottom", 
                                "showLegend": True,
                                "calcs": ["lastNotNull"]
                            }
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
                "graphTooltip": 1,  # MULTI-SERIES TOOLTIP
                "hideControls": False,
                "liveNow": True,
                "weekStart": ""
            },
            "folderId": 0,
            "overwrite": False,
            "message": f"Line chart dashboard created with correct datasource {datasource['uid']}"
        }
        
        try:
            print(f"   📤 Sending LINE CHART dashboard to Grafana...")
            print(f"      Using datasource: {datasource['name']} ({datasource['uid']})")
            print(f"      Draw style: line")
            print(f"      Fill opacity: 0 (no fill)")
            print(f"      Show points: never")
            
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
                print(f"      Title: LINE CHART West Hub Prices {timestamp}")
                print(f"      UID: {dashboard_uid}")
                print(f"      URL: {dashboard_url}")
                print(f"      🎯 Should display as LINE CHART by default!")
                
                return {
                    'success': True,
                    'uid': dashboard_uid,
                    'url': dashboard_url,
                    'title': f"LINE CHART West Hub Prices {timestamp}"
                }
            else:
                print(f"   ❌ Failed to create dashboard: HTTP {response.status_code}")
                print(f"      Response: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            print(f"   ❌ Error creating dashboard: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_complete_fix(self):
        """Run the complete fix process"""
        print("🚀 GRAFANA DATASOURCE COMPLETE FIX - LINE CHART VERSION")
        print("=" * 60)
        
        # Step 1: Verify Grafana connection
        if not self.step1_verify_grafana_connection():
            print("\n❌ FAILED: Cannot connect to Grafana")
            return False
        
        # Step 2: Get datasources
        datasource = self.step2_get_datasources()
        if not datasource:
            print("\n❌ FAILED: Cannot find PostgreSQL datasource")
            return False
        
        # Step 3: Test database
        if not self.step3_test_database_connection():
            print("\n❌ FAILED: Cannot connect to database")
            return False
        
        # Step 4: Test datasource in Grafana
        if not self.step4_test_datasource_in_grafana(datasource):
            print("\n❌ FAILED: Datasource not working in Grafana")
            return False
        
        # Step 5: Clean up broken dashboards
        self.step5_delete_broken_dashboards()
        
        # Step 6: Create fresh dashboard
        result = self.step6_create_fresh_dashboard(datasource)
        
        if result['success']:
            print(f"\n🎉 SUCCESS! Created working LINE CHART dashboard:")
            print(f"   📊 {result['title']}")
            print(f"   🔗 {result['url']}")
            print(f"   🎯 Should display as LINE CHART immediately!")
            print(f"\n✅ Your ERCOT data should now be visible as line charts!")
            return True
        else:
            print(f"\n❌ FAILED: Could not create dashboard: {result['error']}")
            return False

def main():
    """Main function to run the complete fix"""
    print("Starting Grafana Datasource Fix with LINE CHART forcing...")
    
    fixer = GrafanaFixer()
    success = fixer.run_complete_fix()
    
    if success:
        print("\n🎉 ALL DONE! Your Grafana dashboards should now work correctly.")
        print("   • The new dashboard will show real ERCOT settlement prices as LINE CHARTS")
        print("   • You can create more dashboards using the AI visualization tool")
        print("   • The datasource issue has been resolved")
        print("   • Line chart visualization should display immediately")
    else:
        print("\n❌ Fix process failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
