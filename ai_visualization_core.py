# ai_visualization_core.py
# AI visualization system with WORKING line chart configuration - FIXED VERSION
import boto3
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import os
import re

logger = logging.getLogger(__name__)

@dataclass
class DataSource:
    table_name: str
    description: str
    columns: List[str]
    time_column: str
    sample_data: Optional[Dict] = None

class GrafanaAPI:
    """Grafana API client using WORKING test script configuration"""
    
    def __init__(self):
        self.grafana_url = "http://52.4.166.16:3000"
        self.session = requests.Session()
        self.session.auth = ('admin', 'admin')
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def _clean_sql_query(self, sql_query: str) -> str:
        """Clean SQL query to match working script format - NO INDENTATION"""
        if not sql_query:
            logger.warning("🔍 Empty SQL query provided")
            return ""
        
        logger.info(f"🔍 BEFORE cleaning: {repr(sql_query)}")
        
        # Remove all extra whitespace, tabs, and newlines
        cleaned = re.sub(r'\s+', ' ', sql_query.strip())
        
        logger.info(f"🔍 AFTER whitespace removal: {repr(cleaned)}")
        
        # Ensure proper format: timestamp AS time is always present
        if 'timestamp AS time' not in cleaned and 'timestamp' in cleaned:
            cleaned = cleaned.replace('timestamp', 'timestamp AS time', 1)
            logger.info(f"🔍 AFTER timestamp AS time replacement: {repr(cleaned)}")
        
        # Ensure $__timeFilter is properly formatted
        if '$__timeFilter(timestamp)' not in cleaned and 'timeFilter' in cleaned:
            cleaned = re.sub(r'\$__timeFilter\([^)]*\)', '$__timeFilter(timestamp)', cleaned)
            logger.info(f"🔍 AFTER timeFilter fix: {repr(cleaned)}")
        
        # Replace any remaining NOW() - INTERVAL with $__timeFilter(timestamp)
        if 'NOW() - INTERVAL' in cleaned:
            cleaned = re.sub(r"timestamp >= NOW\(\) - INTERVAL '[^']*'", '$__timeFilter(timestamp)', cleaned)
            logger.info(f"🔍 AFTER NOW() replacement: {repr(cleaned)}")
        
        logger.info(f"🔍 FINAL cleaned SQL: {repr(cleaned)}")
        return cleaned
    
    def create_dashboard_from_analysis(self, analysis: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Create dashboard using EXACT working configuration"""
        try:
            title = analysis.get('title', 'AI Generated Dashboard')
            sql_query = self._clean_sql_query(analysis.get('sql_query', ''))
            
            # Validate SQL query has required components
            if not sql_query:
                return {'success': False, 'error': 'No SQL query provided'}
            
            if 'timestamp AS time' not in sql_query:
                # Force proper time column format
                sql_query = sql_query.replace('timestamp', 'timestamp AS time', 1)
            
            logger.info(f"🎯 Creating AI dashboard: {title}")
            logger.info(f"📈 Using WORKING line chart configuration")
            logger.info(f"🔍 Clean SQL: {sql_query}")
            
            # Create timestamp for unique naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # EXACT working dashboard configuration - COPY FROM TEST SCRIPT
            dashboard_config = {
                "dashboard": {
                    "id": None,
                    "title": f"AI: {title} {timestamp}",
                    "description": f"AI-generated dashboard created at {datetime.now()}",
                    "tags": ["ai-generated", f"user-{user_id}", "ercot", "working", timestamp],
                    "timezone": "browser",
                    "panels": [
                        {
                            "id": 1,
                            "title": title,
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
                                    "rawSql": sql_query,
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
                "message": f"AI-generated dashboard for user {user_id}"
            }
            
            # Send to Grafana
            logger.info(f"📤 Sending AI dashboard to Grafana...")
            logger.info(f" Using datasource: grafana-postgresql-datasource (aep8tntrm562ob)")
            logger.info(f" Visualization: LINE CHART")
            logger.info(f" SQL (cleaned): {sql_query}")
            
            response = self.session.post(
                f"{self.grafana_url}/api/dashboards/db",
                json=dashboard_config,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                dashboard_uid = result['uid']
                dashboard_url = f"{self.grafana_url}/d/{dashboard_uid}"
                
                logger.info(f"✅ AI Dashboard created successfully!")
                logger.info(f" Title: AI: {title} {timestamp}")
                logger.info(f" UID: {dashboard_uid}")
                logger.info(f" URL: {dashboard_url}")
                
                return {
                    'success': True,
                    'dashboard_uid': dashboard_uid,
                    'dashboard_id': result['id'],
                    'dashboard_url': dashboard_url,
                    'embed_url': f"{self.grafana_url}/d-solo/{dashboard_uid}",
                    'panel_embed_url': f"{self.grafana_url}/d-solo/{dashboard_uid}?orgId=1&panelId=1&refresh=30s&kiosk",
                    'panel_id': 1,
                    'title': f"AI: {title} {timestamp}",
                    'sql_used': sql_query
                }
            else:
                logger.error(f"❌ Failed to create AI dashboard: HTTP {response.status_code}")
                logger.error(f" Response: {response.text}")
                return {
                    'success': False,
                    'error': f"Grafana API error: {response.status_code}",
                    'details': response.text
                }
                
        except Exception as e:
            logger.error(f"❌ Error creating AI dashboard: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Grafana"""
        try:
            response = self.session.get(f"{self.grafana_url}/api/org", timeout=10)
            if response.status_code == 200:
                org_info = response.json()
                return {
                    'success': True,
                    'message': f"Connected to Grafana - Organization: {org_info.get('name', 'Unknown')}",
                    'org_info': org_info
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

class DatabaseAnalyzer:
    """Database analyzer with working database configuration"""
    
    def __init__(self):
        # Working database configuration
        self.db_config = {
            'host': 'dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com',
            'database': 'analytics',
            'user': 'dbuser',
            'password': 'Superman1262!',
            'port': 5432
        }
    
    def get_db_connection(self):
        return psycopg2.connect(**self.db_config)
    
    def analyze_existing_data(self) -> List[DataSource]:
        """Analyze your existing ERCOT tables"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            data_sources = []
            
            # Analyze ercot_settlement_prices table
            cursor.execute("SELECT * FROM ercot_settlement_prices LIMIT 1")
            sample_prices = cursor.fetchone()
            if sample_prices:
                price_columns = list(sample_prices.keys())
                data_sources.append(DataSource(
                    table_name="ercot_settlement_prices",
                    description="Real-time settlement point prices across ERCOT zones and hubs",
                    columns=price_columns,
                    time_column="timestamp",
                    sample_data=dict(sample_prices)
                ))
            
            # Analyze ercot_capacity_monitor table
            cursor.execute("SELECT * FROM ercot_capacity_monitor LIMIT 1")
            sample_capacity = cursor.fetchone()
            if sample_capacity:
                capacity_columns = list(sample_capacity.keys())
                data_sources.append(DataSource(
                    table_name="ercot_capacity_monitor",
                    description="ERCOT system capacity, reserves, and ancillary services data",
                    columns=capacity_columns,
                    time_column="timestamp",
                    sample_data=dict(sample_capacity)
                ))
            
            cursor.close()
            conn.close()
            logger.info(f"Analyzed {len(data_sources)} data sources")
            return data_sources
            
        except Exception as e:
            logger.error(f"Error analyzing database: {e}")
            return []

class BedrockAIClient:
    """AWS Bedrock client for AI-powered data analysis"""
    
    def __init__(self, region_name: str = "us-east-1"):
        self.region_name = region_name
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Bedrock client with error handling"""
        try:
            self.client = boto3.client('bedrock-runtime', region_name=self.region_name)
            logger.info("AWS Bedrock client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            self.client = None
    
    async def analyze_user_request(self, user_request: str, data_sources: List[DataSource]) -> Dict[str, Any]:
        """Use Claude to analyze user request and suggest visualization"""
        if not self.client:
            logger.warning("Bedrock client not available, using fallback analysis")
            return self._fallback_analysis(user_request, data_sources)
        
        # Build context about your ERCOT data
        data_context = self._build_data_context(data_sources)
        
        prompt = f"""
You are an expert ERCOT data analyst. Generate EXACTLY formatted SQL for Grafana dashboards.

User Request: "{user_request}"

Available ERCOT Data Sources:
{data_context}

CRITICAL: Generate a JSON response with these exact requirements:

SQL QUERY MUST BE EXACTLY THIS FORMAT (single line, no spaces, no newlines):
"sql_query": "SELECT timestamp AS time, column_name AS \"Column Label\" FROM table_name WHERE $__timeFilter(timestamp) ORDER BY timestamp"

EXAMPLE WORKING QUERIES:
- West Hub: "SELECT timestamp AS time, hb_west AS \"West Hub Price\", hb_houston AS \"Houston Hub Price\" FROM ercot_settlement_prices WHERE $__timeFilter(timestamp) ORDER BY timestamp"
- Houston Hub: "SELECT timestamp AS time, hb_houston AS \"Houston Hub Price\", lz_houston AS \"Houston Load Zone\" FROM ercot_settlement_prices WHERE $__timeFilter(timestamp) ORDER BY timestamp"

JSON fields required:
1. "recommended_table": "ercot_settlement_prices" or "ercot_capacity_monitor"
2. "title": Chart title
3. "description": Brief description
4. "sql_query": SINGLE LINE SQL with exact format above
5. "chart_type": "line"
6. "time_range": "24h"

ABSOLUTE REQUIREMENTS:
- sql_query MUST be single line with no indentation
- MUST use "timestamp AS time"
- MUST use $__timeFilter(timestamp) not NOW() - INTERVAL
- MUST use quoted column aliases like "West Hub Price"
- NO tabs, NO newlines, NO extra spaces

Respond with valid JSON only.
"""
        
        try:
            response = self.client.invoke_model(
                modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 2000,
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ]
                })
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                # Clean the SQL query from AI response
                if 'sql_query' in analysis:
                    analysis['sql_query'] = self._clean_ai_sql(analysis['sql_query'])
                logger.info("Successfully analyzed user request with Bedrock")
                return analysis
            else:
                logger.warning("No valid JSON in Bedrock response, using fallback")
                return self._fallback_analysis(user_request, data_sources)
                
        except Exception as e:
            logger.error(f"Bedrock analysis failed: {e}")
            return self._fallback_analysis(user_request, data_sources)
    
    def _clean_ai_sql(self, sql_query: str) -> str:
        """Clean SQL query from AI to ensure working format"""
        if not sql_query:
            return ""
        
        logger.info(f"🤖 AI SQL BEFORE cleaning: {repr(sql_query)}")
        
        # Remove all extra whitespace, newlines, and tabs
        cleaned = re.sub(r'\s+', ' ', sql_query.strip())
        
        # Ensure timestamp AS time format
        if 'timestamp AS time' not in cleaned and 'timestamp' in cleaned:
            cleaned = cleaned.replace('timestamp', 'timestamp AS time', 1)
        
        # Replace NOW() - INTERVAL with $__timeFilter(timestamp)
        if 'NOW() - INTERVAL' in cleaned:
            cleaned = re.sub(r"timestamp >= NOW\(\) - INTERVAL '[^']*'", '$__timeFilter(timestamp)', cleaned)
        
        # Ensure proper timeFilter format
        if '$__timeFilter(timestamp)' not in cleaned and ('timeFilter' in cleaned or 'NOW()' in cleaned):
            # Replace any existing timeFilter or add it
            if 'WHERE' in cleaned:
                cleaned = re.sub(r'WHERE [^O]*ORDER', 'WHERE $__timeFilter(timestamp) ORDER', cleaned)
            else:
                cleaned = cleaned.replace('ORDER BY', 'WHERE $__timeFilter(timestamp) ORDER BY')
        
        logger.info(f"🤖 AI SQL AFTER cleaning: {repr(cleaned)}")
        return cleaned
    
    def _build_data_context(self, data_sources: List[DataSource]) -> str:
        """Build context string about available data"""
        context_parts = []
        for ds in data_sources:
            sample_str = ""
            if ds.sample_data:
                # Show a few key sample values
                sample_items = list(ds.sample_data.items())[:5]
                sample_str = f"\nSample data: {dict(sample_items)}"
            
            context_parts.append(f"""
Table: {ds.table_name}
Description: {ds.description}
Columns: {', '.join(ds.columns)}
Time Column: {ds.time_column}{sample_str}
""")
        return '\n'.join(context_parts)
    
    def _fallback_analysis(self, user_request: str, data_sources: List[DataSource]) -> Dict[str, Any]:
        """Fallback analysis generating EXACT working queries - NO INDENTATION"""
        request_lower = user_request.lower()
        
        # Generate EXACT queries that match working test script format
        if any(word in request_lower for word in ['price', 'pricing', 'settlement', 'hub', 'zone', 'north', 'houston', 'south', 'west']):
            # Determine specific hub if mentioned
            if 'north' in request_lower:
                title = "North Hub Settlement Prices"
                sql_query = "SELECT timestamp AS time, hb_north AS \"North Hub Price\", lz_north AS \"North Load Zone\" FROM ercot_settlement_prices WHERE $__timeFilter(timestamp) ORDER BY timestamp"
            elif 'houston' in request_lower:
                title = "Houston Hub Settlement Prices"
                sql_query = "SELECT timestamp AS time, hb_houston AS \"Houston Hub Price\", lz_houston AS \"Houston Load Zone\" FROM ercot_settlement_prices WHERE $__timeFilter(timestamp) ORDER BY timestamp"
            elif 'south' in request_lower:
                title = "South Hub Settlement Prices"
                sql_query = "SELECT timestamp AS time, hb_south AS \"South Hub Price\", lz_south AS \"South Load Zone\" FROM ercot_settlement_prices WHERE $__timeFilter(timestamp) ORDER BY timestamp"
            elif 'west' in request_lower:
                title = "West Hub Settlement Prices"
                # EXACT query from working test script
                sql_query = "SELECT timestamp AS time, hb_west AS \"West Hub Price\", hb_houston AS \"Houston Hub Price\" FROM ercot_settlement_prices WHERE $__timeFilter(timestamp) ORDER BY timestamp"
            else:
                title = "ERCOT Settlement Point Prices"
                sql_query = "SELECT timestamp AS time, hb_busavg AS \"Bus Average Price\", hb_houston AS \"Houston Hub Price\", hb_north AS \"North Hub Price\" FROM ercot_settlement_prices WHERE $__timeFilter(timestamp) ORDER BY timestamp"
            
            return {
                "recommended_table": "ercot_settlement_prices",
                "recommended_columns": ["timestamp", "price_columns"],
                "chart_type": "line",
                "time_range": "24h",
                "aggregation": "none",
                "filters": {},
                "title": title,
                "description": "Real-time settlement point prices across ERCOT hubs",
                "sql_query": sql_query,
                "grafana_config": {
                    "type": "timeseries",
                    "title": title
                }
            }
            
        elif any(word in request_lower for word in ['capacity', 'reserve', 'ancillary', 'outage', 'emr']):
            return {
                "recommended_table": "ercot_capacity_monitor",
                "recommended_columns": ["timestamp", "category", "subcategory", "value", "unit"],
                "chart_type": "line",
                "time_range": "24h",
                "aggregation": "none",
                "filters": {},
                "title": "ERCOT Capacity Monitor",
                "description": "System capacity and ancillary services data",
                "sql_query": "SELECT timestamp AS time, value AS \"Capacity Value\", category AS \"Category\" FROM ercot_capacity_monitor WHERE $__timeFilter(timestamp) ORDER BY timestamp",
                "grafana_config": {
                    "type": "timeseries",
                    "title": "Capacity Monitor"
                }
            }
        else:
            # Default to prices using EXACT working query format
            return {
                "recommended_table": "ercot_settlement_prices",
                "recommended_columns": ["timestamp", "hb_busavg"],
                "chart_type": "line",
                "time_range": "24h",
                "aggregation": "none",
                "filters": {},
                "title": "ERCOT Data Overview",
                "description": "General ERCOT data visualization",
                "sql_query": "SELECT timestamp AS time, hb_busavg AS \"Bus Average Price\" FROM ercot_settlement_prices WHERE $__timeFilter(timestamp) ORDER BY timestamp",
                "grafana_config": {
                    "type": "timeseries",
                    "title": "ERCOT Overview"
                }
            }

class AIVisualizationProcessor:
    """Main processor that coordinates the AI visualization workflow"""
    
    def __init__(self):
        self.db_analyzer = DatabaseAnalyzer()
        self.ai_client = BedrockAIClient()
        self.grafana_api = GrafanaAPI()
        self.data_sources = []
    
    async def initialize(self):
        """Initialize the processor by analyzing available data"""
        self.data_sources = self.db_analyzer.analyze_existing_data()
        logger.info(f"AI Visualization Processor initialized with {len(self.data_sources)} data sources")
    
    async def process_user_request(self, user_id: int, request_text: str, visualization_type: str = "chart") -> Dict[str, Any]:
        """Process a user's visualization request and create Grafana dashboard"""
        try:
            # Step 1: Analyze the request with AI
            logger.info(f"🔄 Processing AI request from user {user_id}: {request_text}")
            analysis = await self.ai_client.analyze_user_request(request_text, self.data_sources)
            
            # Debug the SQL generation
            sql_query = analysis.get('sql_query', '')
            logger.info(f"📊 AI Analysis complete: {analysis.get('title', 'Unknown')}")
            logger.info(f"🔍 Generated SQL (RAW): '{sql_query}'")
            logger.info(f"🔍 SQL Length: {len(sql_query)} characters")
            logger.info(f"🔍 SQL has newlines: {chr(10) in sql_query}")
            logger.info(f"🔍 SQL has tabs: {chr(9) in sql_query}")
            logger.info(f"🔍 SQL repr: {repr(sql_query)}")
            
            # Step 2: Store the analysis in your existing ai_visualizations table
            viz_id = await self._store_analysis(user_id, request_text, visualization_type, analysis)
            
            # Step 3: Execute the SQL query to validate data availability (separate preview)
            data_preview = await self._get_data_preview(sql_query)
            
            # Step 4: Create Grafana dashboard using WORKING configuration
            logger.info(f"🎯 Creating Grafana dashboard with WORKING configuration...")
            logger.info(f"🎯 SQL being sent to Grafana: '{sql_query}'")
            grafana_result = await self._create_grafana_dashboard(analysis, user_id)
            
            # Step 5: Update the visualization record with results
            if grafana_result['success']:
                await self._update_visualization_status(viz_id, 'completed', {
                    **analysis,
                    'grafana_dashboard': grafana_result
                })
                logger.info(f"✅ SUCCESS! AI Dashboard created: {grafana_result.get('dashboard_url', 'N/A')}")
                logger.info(f"📈 SQL used in dashboard: {grafana_result.get('sql_used', 'N/A')}")
                
                return {
                    'success': True,
                    'visualization_id': viz_id,
                    'analysis': analysis,
                    'data_preview': data_preview,
                    'grafana_dashboard': grafana_result,
                    'message': 'AI visualization created successfully with working line chart configuration'
                }
            else:
                await self._update_visualization_status(viz_id, 'failed', analysis)
                logger.error(f"❌ Dashboard creation failed: {grafana_result.get('error', 'Unknown')}")
                
                return {
                    'success': False,
                    'visualization_id': viz_id,
                    'analysis': analysis,
                    'data_preview': data_preview,
                    'grafana_error': grafana_result.get('error'),
                    'message': f'Grafana dashboard creation failed: {grafana_result.get("error", "Unknown error")}'
                }
                
        except Exception as e:
            logger.error(f"❌ Error processing AI request: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process AI visualization request'
            }
    
    async def _create_grafana_dashboard(self, analysis: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Create a Grafana dashboard using WORKING configuration"""
        try:
            # Test connection first
            connection_test = self.grafana_api.test_connection()
            if not connection_test['success']:
                return {
                    'success': False,
                    'error': f"Cannot connect to Grafana: {connection_test['error']}"
                }
            
            # Create the dashboard using WORKING configuration
            logger.info(f"🔄 Using WORKING line chart configuration...")
            result = self.grafana_api.create_dashboard_from_analysis(analysis, user_id)
            
            if result['success']:
                logger.info(f"✅ Created AI Grafana dashboard {result['dashboard_uid']} for user {user_id}")
                # Store dashboard info in database
                await self._store_grafana_dashboard(user_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error creating AI Grafana dashboard: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _store_grafana_dashboard(self, user_id: int, grafana_result: Dict[str, Any]):
        """Store Grafana dashboard information in database"""
        try:
            conn = self.db_analyzer.get_db_connection()
            cursor = conn.cursor()
            
            # Get the next panel order
            cursor.execute("""
                SELECT COALESCE(MAX(panel_order), 0) + 1
                FROM user_dashboard_settings 
                WHERE user_id = %s
            """, (user_id,))
            next_order = cursor.fetchone()[0]
            
            # Add dashboard info to user's dashboard settings
            cursor.execute("""
                INSERT INTO user_dashboard_settings 
                (user_id, panel_id, panel_name, is_visible, panel_order, panel_grid_column)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                f"ai_dashboard_{grafana_result['dashboard_uid']}",
                f"AI: {grafana_result.get('title', 'Custom Visualization')}",
                True,
                next_order,
                2  # Full width
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Stored AI dashboard {grafana_result['dashboard_uid']} in user settings")
            
        except Exception as e:
            logger.error(f"Error storing AI dashboard info: {e}")
    
    async def _store_analysis(self, user_id: int, request_text: str, viz_type: str, analysis: Dict) -> int:
        """Store analysis in your existing ai_visualizations table"""
        try:
            conn = self.db_analyzer.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ai_visualizations 
                (user_id, request_text, visualization_type, chart_config, status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, request_text, viz_type, json.dumps(analysis), 'processing'))
            
            viz_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            return viz_id
            
        except Exception as e:
            logger.error(f"Error storing AI analysis: {e}")
            raise
    
    async def _get_data_preview(self, sql_query: str, limit: int = 10) -> List[Dict]:
        """Get a preview of the data - DOES NOT MODIFY ORIGINAL QUERY"""
        if not sql_query:
            return []
        
        try:
            conn = self.db_analyzer.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Create a SEPARATE preview query (DO NOT modify original)
            preview_query = sql_query.replace(
                '$__timeFilter(timestamp)', 
                "timestamp >= NOW() - INTERVAL '24 hours'"
            )
            
            # Add LIMIT to the PREVIEW query only
            if 'LIMIT' not in preview_query.upper():
                preview_query += f' LIMIT {limit}'
            
            logger.info(f"🔍 Preview query (separate from dashboard): {preview_query}")
            logger.info(f"📊 Original dashboard query remains: {sql_query}")
            
            cursor.execute(preview_query)
            data = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Convert datetime objects to strings for JSON serialization
            result = []
            for row in data:
                row_dict = dict(row)
                for key, value in row_dict.items():
                    if isinstance(value, datetime):
                        row_dict[key] = value.isoformat()
                result.append(row_dict)
            
            logger.info(f"✅ Preview returned {len(result)} rows")
            return result
            
        except Exception as e:
            logger.error(f"Error getting data preview: {e}")
            return []
    
    async def _update_visualization_status(self, viz_id: int, status: str, analysis: Dict):
        """Update visualization status in database"""
        try:
            conn = self.db_analyzer.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE ai_visualizations 
                SET status = %s, chart_config = %s, updated_at = NOW()
                WHERE id = %s
            """, (status, json.dumps(analysis), viz_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating AI visualization status: {e}")

# Global processor instance
_ai_processor = None

async def initialize_ai_system(db_config: Dict[str, Any]) -> None:
    """Initialize the AI visualization system - called from app.py startup"""
    global _ai_processor
    try:
        logger.info("🚀 Initializing AI Visualization System...")
        _ai_processor = AIVisualizationProcessor()
        await _ai_processor.initialize()
        logger.info("✅ AI Visualization System initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize AI system: {e}")
        raise

def get_ai_processor() -> AIVisualizationProcessor:
    """Get the global AI processor instance"""
    global _ai_processor
    if _ai_processor is None:
        raise RuntimeError("AI processor not initialized. Call initialize_ai_system() first.")
    return _ai_processor

# Testing and utility functions
def test_ai_visualization():
    """Test the AI visualization system"""
    print("🔍 Testing AI Visualization System")
    print("=" * 40)
    
    processor = AIVisualizationProcessor()
    
    async def run_test():
        await processor.initialize()
        
        # Test user request
        test_request = "Show me west hub settlement prices"
        result = await processor.process_user_request(1, test_request)
        
        print(f"AI Visualization result: {'✅' if result['success'] else '❌'}")
        if result['success']:
            print(f" Created visualization: {result['analysis']['title']}")
            if 'grafana_dashboard' in result and result['grafana_dashboard']['success']:
                grafana_info = result['grafana_dashboard']
                print(f" Dashboard URL: {grafana_info.get('dashboard_url', 'N/A')}")
                print(f" SQL Query: {grafana_info.get('sql_used', 'N/A')}")
                print(f" Should display as LINE CHART immediately!")
                return True
            else:
                print(f" ❌ Grafana dashboard creation failed: {result.get('grafana_error', 'Unknown')}")
                return False
        else:
            print(f" Error: {result.get('error', 'Unknown error')}")
            return False
    
    # Run the async test
    return asyncio.run(run_test())

# Example usage and testing
if __name__ == "__main__":
    print("🚀 AI VISUALIZATION CORE - FIXED VERSION")
    print("=" * 50)
    print("✅ FIXED: Clean SQL queries with no indentation")
    print("✅ FIXED: Proper timestamp AS time column aliasing")
    print("✅ FIXED: Exact working dashboard configuration")
    print("✅ FIXED: SQL cleaning and validation")
    print("\n📋 Available Functions:")
    print("1. test_ai_visualization() - Test the complete AI system")
    print("\n🎯 KEY FIXES:")
    print("✅ Added _clean_sql_query() method")
    print("✅ Ensures 'timestamp AS time' format")
    print("✅ Removes all indentation/tabs/extra spaces")
    print("✅ Validates SQL before sending to Grafana")
    print("✅ Uses EXACT working JSON structure")
    print("\n💡 QUICK TEST:")
    print("Run: test_ai_visualization()")
    
    # Uncomment to run test immediately
    # test_ai_visualization()