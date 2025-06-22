# langgraph_ai_visualization.py
# LangGraph-based AI Visualization System for ERCOT Analytics Dashboard

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, field
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import os
import re
import boto3

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)

# State Management for LangGraph
class AIVisualizationState(TypedDict):
    """State object for the AI visualization workflow"""
    # Input data
    user_id: int
    request_text: str
    visualization_type: str
    
    # Processing context
    available_data_sources: List[Dict[str, Any]]
    selected_data_source: Optional[Dict[str, Any]]
    
    # AI-generated artifacts
    analysis_result: Optional[Dict[str, Any]]
    raw_sql_query: Optional[str]
    cleaned_sql_query: Optional[str]
    chart_type: Optional[str]
    chart_title: Optional[str]
    detected_visualization_type: Optional[str]
    
    # Validation results
    sql_validation_result: Optional[Dict[str, Any]]
    data_preview: Optional[List[Dict]]
    
    # Grafana integration
    dashboard_config: Optional[Dict[str, Any]]
    grafana_response: Optional[Dict[str, Any]]
    dashboard_uid: Optional[str]
    
    # Error handling
    errors: List[str]
    status: Literal["processing", "completed", "failed"]
    
    # Output
    visualization_id: Optional[int]
    iframe_url: Optional[str]

@dataclass
class DataSource:
    """Data source metadata for LangGraph processing"""
    table_name: str
    description: str
    columns: List[str]
    time_column: str
    sample_data: Optional[Dict] = None

class LangGraphAIVisualizer:
    """LangGraph-based AI Visualization System"""
    
    def __init__(self):
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.grafana_url = os.getenv("GRAFANA_URL", "http://grafana:3000")
        self.grafana_external_url = os.getenv("GRAFANA_EXTERNAL_URL", "http://localhost:3000")
        
        # Initialize data sources
        self.data_sources = self._initialize_data_sources()
        
        # Build the LangGraph workflow
        self.workflow = self._build_workflow()
    
    def _initialize_data_sources(self) -> List[DataSource]:
        """Initialize available data sources with enhanced metadata"""
        return [
            DataSource(
                table_name="ercot_settlement_prices",
                description="ERCOT settlement point prices for various hubs and load zones. Contains locational marginal pricing (LMP) data for energy markets, real-time and day-ahead pricing.",
                columns=[
                    "timestamp", "oper_day", "interval_ending",
                    "hb_busavg", "hb_houston", "hb_hubavg", "hb_north", 
                    "hb_pan", "hb_south", "hb_west",
                    "lz_aen", "lz_cps", "lz_houston", "lz_lcra", 
                    "lz_north", "lz_raybn", "lz_south", "lz_west"
                ],
                time_column="timestamp"
            ),
            DataSource(
                table_name="ercot_capacity_monitor",
                description="ERCOT grid operations, capacity monitoring, ancillary services, and system stress indicators. Includes reserve margins, generation capacity, demand response, grid stability metrics, emergency conditions, outages, and frequency response data.",
                columns=["timestamp", "category", "subcategory", "value", "unit"],
                time_column="timestamp"
            )
        ]
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with nodes and edges"""
        
        # Create the workflow graph
        workflow = StateGraph(AIVisualizationState)
        
        # Add nodes
        workflow.add_node("parse_request", self._parse_request_node)
        workflow.add_node("detect_visualization_type", self._detect_visualization_type_node)
        workflow.add_node("analyze_data_sources", self._analyze_data_sources_node)
        workflow.add_node("generate_query", self._generate_query_node)
        workflow.add_node("validate_query", self._validate_query_node)
        workflow.add_node("preview_data", self._preview_data_node)
        workflow.add_node("build_dashboard", self._build_dashboard_node)
        workflow.add_node("deploy_grafana", self._deploy_grafana_node)
        workflow.add_node("store_results", self._store_results_node)
        workflow.add_node("handle_error", self._handle_error_node)
        
        # Define edges and routing logic
        workflow.add_edge(START, "parse_request")
        workflow.add_edge("parse_request", "detect_visualization_type")
        workflow.add_edge("detect_visualization_type", "analyze_data_sources")
        workflow.add_edge("analyze_data_sources", "generate_query")
        
        # Conditional routing after query generation
        workflow.add_conditional_edges(
            "generate_query",
            self._should_validate_query,
            {
                "validate": "validate_query",
                "error": "handle_error"
            }
        )
        
        # Conditional routing after validation
        workflow.add_conditional_edges(
            "validate_query",
            self._should_preview_data,
            {
                "preview": "preview_data",
                "error": "handle_error"
            }
        )
        
        # Conditional routing after preview
        workflow.add_conditional_edges(
            "preview_data",
            self._should_build_dashboard,
            {
                "build": "build_dashboard",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("build_dashboard", "deploy_grafana")
        
        # Conditional routing after Grafana deployment
        workflow.add_conditional_edges(
            "deploy_grafana",
            self._should_store_results,
            {
                "store": "store_results",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("store_results", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    # Node Implementations
    
    async def _parse_request_node(self, state: AIVisualizationState) -> AIVisualizationState:
        """Parse and validate the user request"""
        logger.info(f"🔍 Parsing user request: {state['request_text']}")
        
        try:
            # Basic validation
            if not state['request_text'] or len(state['request_text'].strip()) < 3:
                state['errors'].append("Request text is too short or empty")
                state['status'] = "failed"
                return state
            
            # Initialize data sources in state
            state['available_data_sources'] = [
                {
                    'table_name': ds.table_name,
                    'description': ds.description,
                    'columns': ds.columns,
                    'time_column': ds.time_column
                }
                for ds in self.data_sources
            ]
            
            logger.info(f"✅ Request parsed successfully. Found {len(state['available_data_sources'])} data sources")
            return state
            
        except Exception as e:
            logger.error(f"❌ Error parsing request: {e}")
            state['errors'].append(f"Request parsing failed: {str(e)}")
            state['status'] = "failed"
            return state
    
    async def _detect_visualization_type_node(self, state: AIVisualizationState) -> AIVisualizationState:
        """Detect the desired visualization type from the user request"""
        logger.info("🎨 Detecting visualization type from request")
        
        try:
            request_lower = state['request_text'].lower()
            
            # Define visualization type patterns
            visualization_patterns = {
                'bar': ['bar chart', 'bar graph', 'bars', 'column chart', 'histogram'],
                'line': ['line chart', 'line graph', 'time series', 'trend', 'over time'],
                'area': ['area chart', 'filled chart', 'area graph'],
                'scatter': ['scatter plot', 'scatter chart', 'correlation', 'relationship'],
                'pie': ['pie chart', 'donut', 'distribution', 'breakdown', 'percentage'],
                'gauge': ['gauge', 'meter', 'dial', 'speedometer'],
                'table': ['table', 'list', 'tabular', 'data table'],
                'heatmap': ['heatmap', 'heat map', 'intensity', 'correlation matrix'],
                'stat': ['stat', 'single value', 'metric', 'number', 'current value'],
                'timeseries': ['timeseries', 'time series', 'timeline', 'historical', 'over time']
            }
            
            # Default to timeseries for time-based data
            detected_type = 'timeseries'
            confidence = 0.3  # Default confidence
            
            # Check for explicit chart type mentions
            for chart_type, keywords in visualization_patterns.items():
                for keyword in keywords:
                    if keyword in request_lower:
                        detected_type = chart_type
                        confidence = 0.9
                        logger.info(f"🎯 Detected visualization type: {chart_type} (keyword: '{keyword}')")
                        break
                if confidence > 0.8:
                    break
            
            # Smart defaults based on data context
            if confidence < 0.8:
                if any(word in request_lower for word in ['compare', 'vs', 'versus', 'against']):
                    detected_type = 'bar'
                    confidence = 0.7
                    logger.info("🎯 Detected comparison context → bar chart")
                elif any(word in request_lower for word in ['current', 'now', 'latest', 'today']):
                    detected_type = 'stat'
                    confidence = 0.7
                    logger.info("🎯 Detected current value context → stat")
                elif any(word in request_lower for word in ['trend', 'change', 'evolution', 'history']):
                    detected_type = 'timeseries'
                    confidence = 0.8
                    logger.info("🎯 Detected trend context → timeseries")
                else:
                    # Default for energy data is timeseries
                    detected_type = 'timeseries'
                    confidence = 0.6
                    logger.info("🎯 Default for energy data → timeseries")
            
            state['detected_visualization_type'] = detected_type
            state['chart_type'] = detected_type
            
            logger.info(f"✅ Visualization type detection complete: {detected_type} (confidence: {confidence})")
            return state
            
        except Exception as e:
            logger.error(f"❌ Error detecting visualization type: {e}")
            # Default fallback
            state['detected_visualization_type'] = 'timeseries'
            state['chart_type'] = 'timeseries'
            return state
    
    async def _analyze_data_sources_node(self, state: AIVisualizationState) -> AIVisualizationState:
        """Analyze which data sources are relevant for the request"""
        logger.info("🔍 Analyzing data sources for relevance")
        
        try:
            request_lower = state['request_text'].lower()
            
            # Enhanced rule-based data source selection
            capacity_keywords = [
                'capacity', 'reserve', 'ancillary', 'stress', 'grid stress', 'system stress',
                'demand', 'load', 'generation', 'responsive', 'regulation', 'contingency',
                'spinning', 'non-spin', 'emergency', 'outage', 'availability', 'margin',
                'reliability', 'stability', 'frequency response', 'volt', 'reactive'
            ]
            
            price_keywords = [
                'price', 'pricing', 'settlement', 'hub', 'cost', 'market', 'clearing',
                'locational marginal', 'lmp', 'energy price', 'real time', 'day ahead'
            ]
            
            if any(word in request_lower for word in capacity_keywords):
                # Capacity/grid stress related request
                state['selected_data_source'] = next(
                    ds for ds in state['available_data_sources']
                    if ds['table_name'] == 'ercot_capacity_monitor'
                )
                logger.info("📊 Selected data source: ERCOT Capacity Monitor (grid operations/stress)")
                
            elif any(word in request_lower for word in price_keywords):
                # Price-related request
                state['selected_data_source'] = next(
                    ds for ds in state['available_data_sources'] 
                    if ds['table_name'] == 'ercot_settlement_prices'
                )
                logger.info("📊 Selected data source: ERCOT Settlement Prices")
                
            else:
                # For ambiguous requests, use AI to analyze context
                selected_source = await self._ai_analyze_data_source(request_lower, state['available_data_sources'])
                if selected_source:
                    state['selected_data_source'] = selected_source
                    logger.info(f"📊 AI-selected data source: {selected_source['table_name']}")
                else:
                    # Final fallback to capacity monitor for operational queries
                    state['selected_data_source'] = next(
                        ds for ds in state['available_data_sources']
                        if ds['table_name'] == 'ercot_capacity_monitor'
                    )
                    logger.info("📊 Default data source: ERCOT Capacity Monitor")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error analyzing data sources: {e}")
            state['errors'].append(f"Data source analysis failed: {str(e)}")
            state['status'] = "failed"
            return state
    
    async def _generate_query_node(self, state: AIVisualizationState) -> AIVisualizationState:
        """Generate SQL query using AWS Bedrock"""
        logger.info("🤖 Generating SQL query using AI")
        
        try:
            # Build context for AI
            data_source = state['selected_data_source']
            context = self._build_ai_context(data_source)
            
            # Create AI prompt
            prompt = self._create_query_generation_prompt(state['request_text'], context)
            
            # Call AWS Bedrock
            response = await self._call_bedrock_ai(prompt)
            
            if response and response.get('sql_query'):
                state['raw_sql_query'] = response['sql_query']
                state['chart_type'] = response.get('chart_type', 'timeseries')
                state['chart_title'] = response.get('title', 'AI Generated Chart')
                
                logger.info(f"✅ AI generated SQL query: {state['raw_sql_query'][:100]}...")
            else:
                # Fallback to rule-based generation
                logger.warning("🔄 AI generation failed, using fallback logic")
                fallback_result = self._generate_fallback_query(state['request_text'], data_source)
                state['raw_sql_query'] = fallback_result['sql_query']
                state['chart_type'] = fallback_result['chart_type']
                state['chart_title'] = fallback_result['title']
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error generating query: {e}")
            state['errors'].append(f"Query generation failed: {str(e)}")
            state['status'] = "failed"
            return state
    
    async def _validate_query_node(self, state: AIVisualizationState) -> AIVisualizationState:
        """Validate and clean the generated SQL query"""
        logger.info("🔍 Validating and cleaning SQL query")
        
        try:
            raw_query = state['raw_sql_query']
            
            # Apply critical cleaning rules
            cleaned_query = self._clean_sql_query(raw_query)
            
            # Validate required components
            validation_result = self._validate_sql_components(cleaned_query)
            
            if validation_result['valid']:
                state['cleaned_sql_query'] = cleaned_query
                state['sql_validation_result'] = validation_result
                logger.info(f"✅ SQL query validated: {cleaned_query[:100]}...")
            else:
                state['errors'].append(f"SQL validation failed: {validation_result['errors']}")
                state['status'] = "failed"
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error validating query: {e}")
            state['errors'].append(f"Query validation failed: {str(e)}")
            state['status'] = "failed"
            return state
    
    async def _preview_data_node(self, state: AIVisualizationState) -> AIVisualizationState:
        """Preview data to ensure query works correctly"""
        logger.info("📊 Previewing data with generated query")
        
        try:
            # Create a limited preview query
            preview_query = f"SELECT * FROM ({state['cleaned_sql_query']}) AS preview LIMIT 5"
            
            # Execute preview query
            preview_data = await self._execute_preview_query(preview_query)
            
            if preview_data:
                state['data_preview'] = preview_data
                logger.info(f"✅ Data preview successful: {len(preview_data)} rows")
            else:
                state['errors'].append("Data preview returned no results")
                state['status'] = "failed"
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error previewing data: {e}")
            state['errors'].append(f"Data preview failed: {str(e)}")
            state['status'] = "failed"
            return state
    
    async def _build_dashboard_node(self, state: AIVisualizationState) -> AIVisualizationState:
        """Build Grafana dashboard configuration"""
        logger.info("🏗️ Building Grafana dashboard configuration")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            title = state['chart_title']
            
            # Get panel configuration based on detected chart type
            panel_config = self._get_panel_config_for_type(state['chart_type'])
            
            # Build dashboard configuration using the detected chart type
            dashboard_config = {
                "dashboard": {
                    "id": None,
                    "title": f"AI: {title} {timestamp}",
                    "description": f"AI-generated {state['chart_type']} visualization created at {datetime.now().isoformat()}",
                    "tags": ["ai-generated", f"user-{state['user_id']}", "ercot", "langgraph", timestamp, state['chart_type']],
                    "timezone": "browser",
                    "panels": [{
                        "id": 1,
                        "title": title,
                        "type": panel_config['type'],
                        "gridPos": {"h": 12, "w": 24, "x": 0, "y": 0},
                        "targets": [{
                            "datasource": {
                                "uid": "aep8tntrm562ob",
                                "type": "grafana-postgresql-datasource"
                            },
                            "format": panel_config['format'],
                            "rawQuery": True,
                            "rawSql": state['cleaned_sql_query'],
                            "refId": "A"
                        }],
                        "fieldConfig": panel_config['fieldConfig'],
                        "options": panel_config['options']
                    }],
                    "time": {"from": "now-24h", "to": "now"},
                    "refresh": "30s",
                    "schemaVersion": 37,
                    "version": 0,
                    "fiscalYearStartMonth": 0,
                    "liveNow": False,
                    "weekStart": ""
                },
                "folderId": 0,
                "overwrite": False,
                "message": f"AI-generated {state['chart_type']} dashboard for user {state['user_id']}"
            }
            
            state['dashboard_config'] = dashboard_config
            logger.info(f"✅ Dashboard configuration built successfully")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error building dashboard: {e}")
            state['errors'].append(f"Dashboard building failed: {str(e)}")
            state['status'] = "failed"
            return state
    
    async def _deploy_grafana_node(self, state: AIVisualizationState) -> AIVisualizationState:
        """Deploy dashboard to Grafana"""
        logger.info("🚀 Deploying dashboard to Grafana")
        
        try:
            # Create Grafana session
            session = requests.Session()
            session.auth = (os.getenv("GRAFANA_USER", "admin"), os.getenv("GRAFANA_PASSWORD", "admin"))
            session.headers.update({'Content-Type': 'application/json'})
            
            # Deploy to Grafana
            response = session.post(
                f"{self.grafana_url}/api/dashboards/db",
                json=state['dashboard_config'],
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                state['grafana_response'] = result
                state['dashboard_uid'] = result['uid']
                
                # Generate iframe URL
                state['iframe_url'] = f"{self.grafana_external_url}/d-solo/{result['uid']}?orgId=1&panelId=1&refresh=30s&kiosk"
                
                logger.info(f"✅ Dashboard deployed successfully: {result['uid']}")
            else:
                state['errors'].append(f"Grafana deployment failed: HTTP {response.status_code}")
                state['status'] = "failed"
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error deploying to Grafana: {e}")
            state['errors'].append(f"Grafana deployment failed: {str(e)}")
            state['status'] = "failed"
            return state
    
    async def _store_results_node(self, state: AIVisualizationState) -> AIVisualizationState:
        """Store results in database"""
        logger.info("💾 Storing visualization results in database")
        
        try:
            # Store AI visualization record
            viz_id = await self._store_ai_visualization(state)
            state['visualization_id'] = viz_id
            
            # Add to user dashboard
            await self._add_to_user_dashboard(state, viz_id)
            
            state['status'] = "completed"
            logger.info(f"✅ Results stored successfully: visualization ID {viz_id}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error storing results: {e}")
            state['errors'].append(f"Result storage failed: {str(e)}")
            state['status'] = "failed"
            return state
    
    async def _handle_error_node(self, state: AIVisualizationState) -> AIVisualizationState:
        """Handle errors and cleanup"""
        logger.error(f"🚨 Handling error state. Errors: {state['errors']}")
        
        try:
            # Store error state in database if we have enough context
            if state.get('user_id'):
                await self._store_error_state(state)
            
            state['status'] = "failed"
            return state
            
        except Exception as e:
            logger.error(f"❌ Error in error handler: {e}")
            state['errors'].append(f"Error handling failed: {str(e)}")
            return state
    
    # Conditional Edge Functions
    
    def _should_validate_query(self, state: AIVisualizationState) -> str:
        """Determine if query should be validated or if there's an error"""
        if state['status'] == "failed" or not state.get('raw_sql_query'):
            return "error"
        return "validate"
    
    def _should_preview_data(self, state: AIVisualizationState) -> str:
        """Determine if data should be previewed or if there's an error"""
        if state['status'] == "failed" or not state.get('cleaned_sql_query'):
            return "error"
        return "preview"
    
    def _should_build_dashboard(self, state: AIVisualizationState) -> str:
        """Determine if dashboard should be built or if there's an error"""
        if state['status'] == "failed" or not state.get('data_preview'):
            return "error"
        return "build"
    
    def _should_store_results(self, state: AIVisualizationState) -> str:
        """Determine if results should be stored or if there's an error"""
        if state['status'] == "failed" or not state.get('dashboard_uid'):
            return "error"
        return "store"
    
    # Helper Methods
    
    async def _ai_analyze_data_source(self, request_text: str, available_sources: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Use AI to analyze which data source best matches the request"""
        try:
            # Build context about available data sources
            sources_context = "\n".join([
                f"- {ds['table_name']}: {ds['description']}"
                for ds in available_sources
            ])
            
            prompt = f"""
            Analyze this user request and determine which data source is most appropriate:
            
            User Request: "{request_text}"
            
            Available Data Sources:
            {sources_context}
            
            Respond with just the table name that best matches the request:
            - ercot_settlement_prices (for pricing, market, cost data)
            - ercot_capacity_monitor (for grid operations, stress, capacity, reserves, stability)
            """
            
            # Simple pattern matching for now (can be enhanced with actual AI call)
            if any(word in request_text.lower() for word in [
                'stress', 'capacity', 'reserve', 'grid', 'system', 'stability', 
                'emergency', 'outage', 'regulation', 'frequency', 'demand', 'load'
            ]):
                return next(ds for ds in available_sources if ds['table_name'] == 'ercot_capacity_monitor')
            else:
                return next(ds for ds in available_sources if ds['table_name'] == 'ercot_settlement_prices')
                
        except Exception as e:
            logger.error(f"❌ AI data source analysis failed: {e}")
            return None
    
    def _build_ai_context(self, data_source: Dict[str, Any]) -> str:
        """Build context for AI query generation"""
        context = f"""
        Data Source: {data_source['table_name']}
        Description: {data_source['description']}
        Columns: {', '.join(data_source['columns'])}
        Time Column: {data_source['time_column']}
        
        Important SQL Requirements:
        - Use 'timestamp AS time' for time column
        - Use $__timeFilter(timestamp) for time filtering
        - Use quoted aliases for metrics like "Hub Price"
        - Single line query, no extra whitespace
        """
        return context
    
    def _create_query_generation_prompt(self, request_text: str, context: str) -> str:
        """Create prompt for AI query generation"""
        return f"""
        You are an expert SQL query generator for ERCOT energy data visualization.
        
        Context:
        {context}
        
        User Request: {request_text}
        
        Generate a JSON response with:
        {{
            "sql_query": "Single line SQL query",
            "chart_type": "timeseries",
            "title": "Descriptive chart title"
        }}
        
        Requirements:
        - MUST use 'timestamp AS time'
        - MUST use $__timeFilter(timestamp) not NOW()
        - MUST be single line, no indentation
        - Use proper quoted aliases
        """
    
    async def _call_bedrock_ai(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call AWS Bedrock AI for query generation"""
        try:
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = self.bedrock_client.invoke_model(
                body=json.dumps(payload),
                modelId="anthropic.claude-3-sonnet-20240229-v1:0"
            )
            
            result = json.loads(response['body'].read())
            content = result['content'][0]['text']
            
            # Parse JSON response
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"❌ Bedrock AI call failed: {e}")
            return None
    
    def _generate_fallback_query(self, request_text: str, data_source: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback query using enhanced rule-based logic"""
        request_lower = request_text.lower()
        
        if data_source['table_name'] == 'ercot_settlement_prices':
            if 'houston' in request_lower:
                return {
                    'sql_query': 'SELECT timestamp AS time, hb_houston AS "Houston Hub Price" FROM ercot_settlement_prices WHERE $__timeFilter(timestamp) ORDER BY timestamp',
                    'chart_type': 'timeseries',
                    'title': 'Houston Hub Settlement Prices'
                }
            elif 'north' in request_lower:
                return {
                    'sql_query': 'SELECT timestamp AS time, hb_north AS "North Hub Price" FROM ercot_settlement_prices WHERE $__timeFilter(timestamp) ORDER BY timestamp',
                    'chart_type': 'timeseries',
                    'title': 'North Hub Settlement Prices'
                }
            elif 'south' in request_lower:
                return {
                    'sql_query': 'SELECT timestamp AS time, hb_south AS "South Hub Price" FROM ercot_settlement_prices WHERE $__timeFilter(timestamp) ORDER BY timestamp',
                    'chart_type': 'timeseries',
                    'title': 'South Hub Settlement Prices'
                }
            elif 'west' in request_lower:
                return {
                    'sql_query': 'SELECT timestamp AS time, hb_west AS "West Hub Price" FROM ercot_settlement_prices WHERE $__timeFilter(timestamp) ORDER BY timestamp',
                    'chart_type': 'timeseries',
                    'title': 'West Hub Settlement Prices'
                }
            else:
                return {
                    'sql_query': 'SELECT timestamp AS time, hb_houston AS "Houston Hub", hb_north AS "North Hub", hb_south AS "South Hub", hb_west AS "West Hub" FROM ercot_settlement_prices WHERE $__timeFilter(timestamp) ORDER BY timestamp',
                    'chart_type': 'timeseries',
                    'title': 'ERCOT Settlement Point Prices'
                }
        
        elif data_source['table_name'] == 'ercot_capacity_monitor':
            # Enhanced capacity monitor queries based on actual data categories
            if any(word in request_lower for word in ['stress', 'grid stress', 'system stress', 'strain']):
                return {
                    'sql_query': 'SELECT timestamp AS time, value AS "Available Capacity to Increase (MW)" FROM ercot_capacity_monitor WHERE category = \'System Available Capacity (MW)\' AND subcategory = \'Capacity available to increase Generation Resource Base Points in the next 5 minutes in SCED (HDL)\' AND $__timeFilter(timestamp) ORDER BY timestamp',
                    'chart_type': 'timeseries',
                    'title': 'Grid Stress - Available Generation Capacity'
                }
            elif any(word in request_lower for word in ['reserve', 'margin', 'contingency']):
                return {
                    'sql_query': 'SELECT timestamp AS time, value AS "Responsive Reserve (MW)" FROM ercot_capacity_monitor WHERE category = \'Responsive Reserve Capacity (MW)\' AND subcategory = \'Generation Resources\' AND $__timeFilter(timestamp) ORDER BY timestamp',
                    'chart_type': 'timeseries',
                    'title': 'Reserve Margin - Generation Resources'
                }
            elif any(word in request_lower for word in ['emergency', 'outage', 'emr', 'out']):
                return {
                    'sql_query': 'SELECT timestamp AS time, value AS "Emergency/Outage Capacity (MW)" FROM ercot_capacity_monitor WHERE category = \'EMR, OUT, and OUTL Capacity (MW)\' AND subcategory = \'Aggregate telemetered HSL capacity for Resources with a telemetered Resource Status of EMR\' AND $__timeFilter(timestamp) ORDER BY timestamp',
                    'chart_type': 'timeseries',
                    'title': 'Emergency and Outage Conditions'
                }
            elif any(word in request_lower for word in ['regulation', 'frequency', 'freq']):
                return {
                    'sql_query': 'SELECT timestamp AS time, value AS "Regulation Up (MW)" FROM ercot_capacity_monitor WHERE category = \'Regulation Capacity (MW)\' AND subcategory = \'Deployed Reg-Up\' AND $__timeFilter(timestamp) ORDER BY timestamp',
                    'chart_type': 'timeseries',
                    'title': 'Frequency Regulation - Deployed Up'
                }
            elif any(word in request_lower for word in ['spin', 'spinning', 'non-spin']):
                return {
                    'sql_query': 'SELECT timestamp AS time, value AS "Non-Spin Reserve (MW)" FROM ercot_capacity_monitor WHERE category = \'Non-Spin Reserve Capacity (MW)\' AND subcategory = \'On-Line Generation Resources with Output Schedules\' AND $__timeFilter(timestamp) ORDER BY timestamp',
                    'chart_type': 'timeseries',
                    'title': 'Non-Spinning Reserve Capacity'
                }
            elif any(word in request_lower for word in ['demand', 'curve', 'operating']):
                return {
                    'sql_query': 'SELECT timestamp AS time, value AS "Operating Reserve (MW)" FROM ercot_capacity_monitor WHERE category = \'Real-Time Operating Reserve Demand Curve Capacity (MW)\' AND subcategory = \'Real-Time On-Line reserve capacity\' AND $__timeFilter(timestamp) ORDER BY timestamp',
                    'chart_type': 'timeseries',
                    'title': 'Real-Time Operating Reserve'
                }
            else:
                # General capacity overview showing multiple metrics
                return {
                    'sql_query': 'SELECT timestamp AS time, value AS "Available Increase Capacity (MW)" FROM ercot_capacity_monitor WHERE category = \'System Available Capacity (MW)\' AND subcategory = \'Capacity available to increase Generation Resource Base Points in the next 5 minutes in SCED (HDL)\' AND $__timeFilter(timestamp) ORDER BY timestamp',
                    'chart_type': 'timeseries',
                    'title': 'System Available Capacity Overview'
                }
        
        # Final fallback
        return {
            'sql_query': 'SELECT timestamp AS time, value AS "Value" FROM ercot_capacity_monitor WHERE $__timeFilter(timestamp) ORDER BY timestamp LIMIT 1000',
            'chart_type': 'timeseries',
            'title': 'ERCOT Data Overview'
        }
    
    def _clean_sql_query(self, sql_query: str) -> str:
        """Clean SQL query to match Grafana requirements"""
        if not sql_query:
            return ""
        
        # Remove all extra whitespace, tabs, and newlines
        cleaned = re.sub(r'\s+', ' ', sql_query.strip())
        
        # Ensure proper time filtering
        if 'NOW() - INTERVAL' in cleaned:
            cleaned = re.sub(r'WHERE.*NOW\(\).*?(?=ORDER|$)', 'WHERE $__timeFilter(timestamp) ', cleaned)
        
        return cleaned
    
    def _validate_sql_components(self, sql_query: str) -> Dict[str, Any]:
        """Validate required SQL components"""
        errors = []
        
        if 'timestamp AS time' not in sql_query:
            errors.append("Missing 'timestamp AS time' requirement")
        
        if '$__timeFilter(timestamp)' not in sql_query:
            errors.append("Missing '$__timeFilter(timestamp)' requirement")
        
        if 'FROM' not in sql_query.upper():
            errors.append("Missing FROM clause")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    async def _execute_preview_query(self, query: str) -> Optional[List[Dict]]:
        """Execute preview query against database"""
        try:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST'),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD')
            )
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Replace Grafana variables for preview
            preview_query = query.replace(
                '$__timeFilter(timestamp)',
                "timestamp >= NOW() - INTERVAL '24 hours'"
            )
            
            cursor.execute(preview_query)
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"❌ Preview query failed: {e}")
            return None
    
    def _get_panel_config_for_type(self, chart_type: str) -> Dict[str, Any]:
        """Get complete panel configuration for different chart types"""
        
        base_config = {
            "type": "timeseries",
            "format": "time_series",
            "fieldConfig": self._get_timeseries_field_config(),
            "options": self._get_timeseries_options()
        }
        
        if chart_type == "bar":
            return {
                "type": "barchart",
                "format": "time_series", 
                "fieldConfig": self._get_bar_field_config(),
                "options": self._get_bar_options()
            }
        elif chart_type == "stat":
            return {
                "type": "stat",
                "format": "time_series",
                "fieldConfig": self._get_stat_field_config(),
                "options": self._get_stat_options()
            }
        elif chart_type == "gauge":
            return {
                "type": "gauge",
                "format": "time_series",
                "fieldConfig": self._get_gauge_field_config(),
                "options": self._get_gauge_options()
            }
        elif chart_type == "table":
            return {
                "type": "table",
                "format": "table",
                "fieldConfig": self._get_table_field_config(),
                "options": self._get_table_options()
            }
        elif chart_type == "area":
            config = base_config.copy()
            config["fieldConfig"] = self._get_area_field_config()
            return config
        else:
            # Default to timeseries for line, timeseries, and unknown types
            return base_config
    
    def _get_timeseries_field_config(self) -> Dict[str, Any]:
        """Get field configuration for timeseries charts"""
        return {
            "defaults": {
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "linear",
                    "barAlignment": 0,
                    "lineWidth": 2,
                    "fillOpacity": 0,
                    "gradientMode": "none",
                    "spanNulls": False,
                    "insertNulls": False,
                    "showPoints": "auto",
                    "pointSize": 5,
                    "stacking": {"mode": "none", "group": "A"},
                    "axisPlacement": "auto",
                    "axisLabel": "",
                    "axisColorMode": "text",
                    "axisBorderShow": False,
                    "scaleDistribution": {"type": "linear"},
                    "axisCenteredZero": False,
                    "hideFrom": {"tooltip": False, "viz": False, "legend": False},
                    "thresholdsStyle": {"mode": "off"}
                },
                "color": {"mode": "palette-classic"},
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "red", "value": 80}
                    ]
                }
            },
            "overrides": []
        }
    
    def _get_bar_field_config(self) -> Dict[str, Any]:
        """Get field configuration for bar charts"""
        return {
            "defaults": {
                "custom": {
                    "orientation": "auto",
                    "barWidth": 0.97,
                    "barMaxWidth": 100,
                    "groupWidth": 0.7,
                    "axisPlacement": "auto",
                    "axisLabel": "",
                    "axisColorMode": "text",
                    "scaleDistribution": {"type": "linear"},
                    "axisCenteredZero": False,
                    "hideFrom": {"tooltip": False, "viz": False, "legend": False},
                    "thresholdsStyle": {"mode": "off"}
                },
                "color": {"mode": "palette-classic"},
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "red", "value": 80}
                    ]
                }
            },
            "overrides": []
        }
    
    def _get_stat_field_config(self) -> Dict[str, Any]:
        """Get field configuration for stat panels"""
        return {
            "defaults": {
                "color": {"mode": "thresholds"},
                "custom": {
                    "displayMode": "basic",
                    "cellDisplayMode": "basic",
                    "orientation": "auto",
                    "textMode": "auto",
                    "wideLayout": True,
                    "showUnfilled": True
                },
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "red", "value": 80}
                    ]
                },
                "unit": "short"
            },
            "overrides": []
        }
    
    def _get_gauge_field_config(self) -> Dict[str, Any]:
        """Get field configuration for gauge panels"""
        return {
            "defaults": {
                "color": {"mode": "thresholds"},
                "custom": {},
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "yellow", "value": 50},
                        {"color": "red", "value": 80}
                    ]
                },
                "unit": "short",
                "min": 0,
                "max": 100
            },
            "overrides": []
        }
    
    def _get_area_field_config(self) -> Dict[str, Any]:
        """Get field configuration for area charts"""
        config = self._get_timeseries_field_config()
        config["defaults"]["custom"]["fillOpacity"] = 30
        config["defaults"]["custom"]["gradientMode"] = "opacity"
        return config
    
    def _get_table_field_config(self) -> Dict[str, Any]:
        """Get field configuration for table panels"""
        return {
            "defaults": {
                "color": {"mode": "thresholds"},
                "custom": {
                    "align": "auto",
                    "cellOptions": {"type": "auto"},
                    "inspect": False
                },
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "red", "value": 80}
                    ]
                }
            },
            "overrides": []
        }
    
    def _get_timeseries_options(self) -> Dict[str, Any]:
        """Get options for timeseries panels"""
        return {
            "tooltip": {"mode": "single", "sort": "none"},
            "legend": {
                "showLegend": True,
                "displayMode": "list",
                "placement": "bottom",
                "calcs": []
            }
        }
    
    def _get_bar_options(self) -> Dict[str, Any]:
        """Get options for bar chart panels"""
        return {
            "tooltip": {"mode": "single", "sort": "none"},
            "legend": {
                "showLegend": True,
                "displayMode": "list",
                "placement": "bottom",
                "calcs": []
            },
            "orientation": "auto"
        }
    
    def _get_stat_options(self) -> Dict[str, Any]:
        """Get options for stat panels"""
        return {
            "reduceOptions": {
                "values": False,
                "calcs": ["lastNotNull"],
                "fields": ""
            },
            "orientation": "auto",
            "textMode": "auto",
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "auto"
        }
    
    def _get_gauge_options(self) -> Dict[str, Any]:
        """Get options for gauge panels"""
        return {
            "reduceOptions": {
                "values": False,
                "calcs": ["lastNotNull"],
                "fields": ""
            },
            "orientation": "auto",
            "showThresholdLabels": False,
            "showThresholdMarkers": True
        }
    
    def _get_table_options(self) -> Dict[str, Any]:
        """Get options for table panels"""
        return {
            "showHeader": True,
            "cellHeight": "sm",
            "footer": {
                "show": False,
                "reducer": ["sum"],
                "countRows": False,
                "fields": ""
            }
        }
    
    async def _store_ai_visualization(self, state: AIVisualizationState) -> int:
        """Store AI visualization in database"""
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()
        
        chart_config = {
            'title': state['chart_title'],
            'chart_type': state['chart_type'],
            'sql_query': state['cleaned_sql_query'],
            'dashboard_uid': state['dashboard_uid'],
            'data_source': state['selected_data_source']['table_name'],
            'workflow': 'langgraph'
        }
        
        cursor.execute("""
            INSERT INTO ai_visualizations 
            (user_id, request_text, visualization_type, chart_config, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            state['user_id'],
            state['request_text'],
            state['visualization_type'],
            json.dumps(chart_config),
            'completed'
        ))
        
        viz_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return viz_id
    
    async def _add_to_user_dashboard(self, state: AIVisualizationState, viz_id: int):
        """Add visualization to user dashboard"""
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()
        
        # Get next panel order
        cursor.execute("""
            SELECT COALESCE(MAX(panel_order), 0) + 1
            FROM user_dashboard_settings 
            WHERE user_id = %s
        """, (state['user_id'],))
        next_order = cursor.fetchone()[0]
        
        panel_id = f"ai_viz_{viz_id}"
        panel_name = f"AI: {state['chart_title']}"
        
        cursor.execute("""
            INSERT INTO user_dashboard_settings 
            (user_id, panel_id, panel_name, panel_type, is_visible, panel_order, 
             panel_grid_column, iframe_src, ai_visualization_id, dashboard_uid)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            state['user_id'], panel_id, panel_name, 'ai_generated', True, next_order,
            2, state['iframe_url'], viz_id, state['dashboard_uid']
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    async def _store_error_state(self, state: AIVisualizationState):
        """Store error state in database"""
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()
        
        error_config = {
            'errors': state['errors'],
            'partial_state': {
                'selected_data_source': state.get('selected_data_source'),
                'raw_sql_query': state.get('raw_sql_query'),
                'chart_type': state.get('chart_type')
            },
            'workflow': 'langgraph'
        }
        
        cursor.execute("""
            INSERT INTO ai_visualizations 
            (user_id, request_text, visualization_type, chart_config, status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            state['user_id'],
            state['request_text'],
            state['visualization_type'],
            json.dumps(error_config),
            'failed',
            '; '.join(state['errors'])
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    # Main execution method
    
    async def process_visualization_request(
        self, 
        user_id: int, 
        request_text: str, 
        visualization_type: str = "chart"
    ) -> Dict[str, Any]:
        """Process a visualization request using the LangGraph workflow"""
        
        logger.info(f"🚀 Starting LangGraph AI visualization workflow for user {user_id}")
        
        # Initialize state
        initial_state = AIVisualizationState(
            user_id=user_id,
            request_text=request_text,
            visualization_type=visualization_type,
            available_data_sources=[],
            selected_data_source=None,
            analysis_result=None,
            raw_sql_query=None,
            cleaned_sql_query=None,
            chart_type=None,
            chart_title=None,
            detected_visualization_type=None,
            sql_validation_result=None,
            data_preview=None,
            dashboard_config=None,
            grafana_response=None,
            dashboard_uid=None,
            errors=[],
            status="processing",
            visualization_id=None,
            iframe_url=None
        )
        
        try:
            # Execute the workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Return results
            if final_state['status'] == "completed":
                return {
                    'success': True,
                    'visualization_id': final_state['visualization_id'],
                    'dashboard_uid': final_state['dashboard_uid'],
                    'iframe_url': final_state['iframe_url'],
                    'title': final_state['chart_title'],
                    'sql_query': final_state['cleaned_sql_query'],
                    'workflow': 'langgraph'
                }
            else:
                return {
                    'success': False,
                    'errors': final_state['errors'],
                    'workflow': 'langgraph'
                }
                
        except Exception as e:
            logger.error(f"❌ LangGraph workflow failed: {e}")
            return {
                'success': False,
                'errors': [f"Workflow execution failed: {str(e)}"],
                'workflow': 'langgraph'
            }

# Initialize the LangGraph AI Visualizer
langgraph_visualizer = LangGraphAIVisualizer()