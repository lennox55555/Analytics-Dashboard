import os
from fastapi import FastAPI, Request, HTTPException, Depends, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import json
import secrets
import hashlib
import time
from functools import wraps
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import auth utils after other imports
from auth_utils import auth_manager, get_current_user_optional, get_current_user

# Import AI visualization system
try:
    from ai_visualization_core import initialize_ai_system, get_ai_processor
    from langgraph_ai_visualization import langgraph_visualizer
    AI_SYSTEM_AVAILABLE = True
    LANGGRAPH_AVAILABLE = True
    logger.info("AI Visualization system imported successfully")
    logger.info("LangGraph AI Visualization system imported successfully")
except ImportError as e:
    AI_SYSTEM_AVAILABLE = False
    LANGGRAPH_AVAILABLE = False
    logger.warning(f"AI Visualization system not available: {e}")

# Create FastAPI app
app = FastAPI(title="ERCOT Analytics Dashboard")

# Database configuration for AI system
DB_CONFIG = {
    'host': os.getenv("DB_HOST", "localhost"),
    'database': os.getenv("DB_NAME", "analytics"),
    'user': os.getenv("DB_USER", "dbuser"),
    'password': os.getenv("DB_PASSWORD", ""),
    'port': int(os.getenv("DB_PORT", "5432"))
}

# Startup event handler
@app.on_event("startup")
async def startup_event():
    """Initialize AI system on startup"""
    if AI_SYSTEM_AVAILABLE:
        try:
            await initialize_ai_system(DB_CONFIG)
            logger.info("AI Visualization System started successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI system: {e}")
            # Don't fail startup if AI system fails to initialize
    else:
        logger.info("AI system not available, running in basic mode")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware for iframe embedding
class IFrameMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers['X-Frame-Options'] = 'ALLOWALL'
        response.headers['Content-Security-Policy'] = "frame-ancestors *;"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

app.add_middleware(IFrameMiddleware)

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models
class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    first_name: str = None
    last_name: str = None

class UserLogin(BaseModel):
    email: str
    password: str

class AIVisualizationRequest(BaseModel):
    request_text: str
    visualization_type: str = "chart"

class DashboardPanelSettings(BaseModel):
    panel_id: str
    panel_name: str
    panel_type: str = "predefined"  # "predefined" or "ai_generated"
    is_visible: bool
    panel_order: int
    panel_width: Optional[int] = None
    panel_height: Optional[int] = None
    panel_grid_column: Optional[int] = None
    iframe_src: Optional[str] = None
    ai_visualization_id: Optional[int] = None
    dashboard_uid: Optional[str] = None

class DashboardSettingsUpdate(BaseModel):
    panels: List[DashboardPanelSettings]

# API Key models
class APIKeyCreate(BaseModel):
    key_name: str
    description: Optional[str] = None

class APIKeyResponse(BaseModel):
    id: int
    key_name: str
    api_key: str
    api_secret: str
    rate_limit_per_hour: int
    rate_limit_per_day: int
    created_at: str
    expires_at: Optional[str] = None

class APIUsageStats(BaseModel):
    total_requests: int
    requests_today: int
    requests_this_hour: int
    last_used: Optional[str] = None

# Import shared database connection
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db_connection import get_db_connection

# API Key utilities
def generate_api_credentials():
    """Generate API key and secret"""
    api_key = f"ercot_{''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(32))}"
    api_secret = secrets.token_urlsafe(32)
    secret_hash = hashlib.sha256(api_secret.encode()).hexdigest()
    return api_key, api_secret, secret_hash

def verify_api_key(api_key: str, api_secret: str = None):
    """Verify API key and optional secret"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if api_secret:
            secret_hash = hashlib.sha256(api_secret.encode()).hexdigest()
            cursor.execute("""
                SELECT ak.*, u.email, u.username 
                FROM api_keys ak 
                JOIN users u ON ak.user_id = u.id 
                WHERE ak.api_key = %s AND ak.api_secret_hash = %s AND ak.is_active = true
            """, (api_key, secret_hash))
        else:
            cursor.execute("""
                SELECT ak.*, u.email, u.username 
                FROM api_keys ak 
                JOIN users u ON ak.user_id = u.id 
                WHERE ak.api_key = %s AND ak.is_active = true
            """, (api_key,))
        
        key_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not key_data:
            return None
            
        # Check if expired
        if key_data['expires_at'] and datetime.now() > key_data['expires_at']:
            return None
            
        return dict(key_data)
        
    except Exception as e:
        logger.error(f"Error verifying API key: {e}")
        return None

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        request = kwargs.get('request') or args[0]
        
        # Check for API key in header
        api_key = request.headers.get('X-API-Key')
        api_secret = request.headers.get('X-API-Secret')
        
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="API key required. Include X-API-Key header."
            )
        
        key_data = verify_api_key(api_key, api_secret)
        if not key_data:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired API key"
            )
        
        # Add to request state
        request.state.api_key_data = key_data
        
        # Log API usage
        await log_api_usage(request, key_data)
        
        return await f(*args, **kwargs)
    
    return decorated_function

async def log_api_usage(request: Request, key_data: dict):
    """Log API usage for analytics and rate limiting"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update last used and usage count
        cursor.execute("""
            UPDATE api_keys 
            SET last_used_at = CURRENT_TIMESTAMP, usage_count = usage_count + 1 
            WHERE id = %s
        """, (key_data['id'],))
        
        # Log detailed usage
        cursor.execute("""
            INSERT INTO api_usage_logs 
            (api_key_id, endpoint, method, ip_address, user_agent, query_parameters)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            key_data['id'],
            str(request.url.path),
            request.method,
            request.client.host if request.client else None,
            request.headers.get('user-agent', ''),
            json.dumps(dict(request.query_params))
        ))
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error logging API usage: {e}")

# Home route
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: dict = Depends(get_current_user_optional)):
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

# Authentication routes
@app.post("/api/auth/register")
async def register(user_data: UserCreate, request: Request):
    try:
        user = auth_manager.create_user(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )
        
        if user:
            access_token = auth_manager.create_access_token(
                data={"sub": str(user['id'])}
            )
            auth_manager.store_session(user['id'], access_token, request)
            await create_default_dashboard_settings(user['id'])
            
            return {
                "message": "User created successfully",
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user['id'],
                    "email": user['email'],
                    "username": user['username'],
                    "first_name": user['first_name'],
                    "last_name": user['last_name']
                }
            }
        else:
            raise HTTPException(status_code=400, detail="User creation failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/api/auth/login")
async def login(user_data: UserLogin, request: Request):
    try:
        user = auth_manager.authenticate_user(user_data.email, user_data.password)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
        
        access_token = auth_manager.create_access_token(
            data={"sub": str(user['id'])}
        )
        auth_manager.store_session(user['id'], access_token, request)
        
        return {
            "message": "Login successful",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user['id'],
                "email": user['email'],
                "username": user['username'],
                "first_name": user['first_name'],
                "last_name": user['last_name']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/api/auth/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    return {
        "id": user['id'],
        "email": user['email'],
        "username": user['username'],
        "first_name": user['first_name'],
        "last_name": user['last_name']
    }

# Enhanced Dashboard System
async def create_default_dashboard_settings(user_id: int):
    """Create default dashboard settings for a new user with enhanced schema"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000")
        default_panels = [
            ('chart1', 'Real-Time Price Overview', 'predefined', f'{grafana_url}/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=14&refresh=30s', 1, 2),
            ('chart2', 'System Available Capacity', 'predefined', f'{grafana_url}/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=7&refresh=30s', 2, 1),
            ('chart3', 'Emergency & Outage Status', 'predefined', f'{grafana_url}/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=1&refresh=30s', 3, 1),
            ('chart4', 'Reserve Capacity Overview', 'predefined', f'{grafana_url}/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=12&refresh=30s', 4, 2),
            ('chart5', 'Settlement Point Prices', 'predefined', f'{grafana_url}/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=13&refresh=30s', 5, 2)
        ]
        
        for panel_id, panel_name, panel_type, iframe_src, panel_order, grid_column in default_panels:
            cursor.execute("""
                INSERT INTO user_dashboard_settings 
                (user_id, panel_id, panel_name, panel_type, iframe_src, is_visible, panel_order, panel_grid_column)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, panel_id) DO NOTHING
            """, (user_id, panel_id, panel_name, panel_type, iframe_src, True, panel_order, grid_column))
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Created default dashboard settings for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error creating default dashboard settings: {e}")

@app.get("/api/dashboard/settings")
async def get_dashboard_settings(user: dict = Depends(get_current_user)):
    """Get all dashboard settings including AI-generated panels"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT panel_id, panel_name, panel_type, is_visible, panel_order, 
                   panel_width, panel_height, panel_grid_column, iframe_src,
                   ai_visualization_id, dashboard_uid
            FROM user_dashboard_settings 
            WHERE user_id = %s 
            ORDER BY panel_order
        """, (user['id'],))
        
        settings = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not settings:
            await create_default_dashboard_settings(user['id'])
            return await get_dashboard_settings(user)
        
        result = []
        for setting in settings:
            result.append(dict(setting))
        
        logger.info(f"📊 Retrieved {len(result)} dashboard settings for user {user['id']}")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching dashboard settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard settings")

@app.post("/api/dashboard/settings")
async def update_dashboard_settings(
    settings_update: DashboardSettingsUpdate,
    user: dict = Depends(get_current_user)
):
    """Update dashboard settings including AI-generated panels"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for panel in settings_update.panels:
            cursor.execute("""
                INSERT INTO user_dashboard_settings 
                (user_id, panel_id, panel_name, panel_type, is_visible, panel_order, 
                 panel_width, panel_height, panel_grid_column, iframe_src, 
                 ai_visualization_id, dashboard_uid)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, panel_id) 
                DO UPDATE SET
                    panel_name = EXCLUDED.panel_name,
                    panel_type = EXCLUDED.panel_type,
                    is_visible = EXCLUDED.is_visible,
                    panel_order = EXCLUDED.panel_order,
                    panel_width = EXCLUDED.panel_width,
                    panel_height = EXCLUDED.panel_height,
                    panel_grid_column = EXCLUDED.panel_grid_column,
                    iframe_src = EXCLUDED.iframe_src,
                    ai_visualization_id = EXCLUDED.ai_visualization_id,
                    dashboard_uid = EXCLUDED.dashboard_uid,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                user['id'], panel.panel_id, panel.panel_name, panel.panel_type,
                panel.is_visible, panel.panel_order, panel.panel_width, 
                panel.panel_height, panel.panel_grid_column, panel.iframe_src,
                panel.ai_visualization_id, panel.dashboard_uid
            ))
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Updated dashboard settings for user {user['id']}")
        return {"message": "Dashboard settings updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating dashboard settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update dashboard settings")

@app.post("/api/dashboard/reset")
async def reset_dashboard_settings(user: dict = Depends(get_current_user)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM user_dashboard_settings WHERE user_id = %s", (user['id'],))
        cursor.close()
        conn.close()
        
        await create_default_dashboard_settings(user['id'])
        
        return {"message": "Dashboard settings reset to default"}
        
    except Exception as e:
        logger.error(f"Error resetting dashboard settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset dashboard settings")

@app.get("/api/dashboard/available-panels")
async def get_available_panels(user: dict = Depends(get_current_user)):
    """Get all available panels (predefined + user's AI-generated) - FIXED VERSION"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get predefined panels with environment-based Grafana URL
        grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000")
        predefined_panels = [
            {
                'panel_id': 'chart1',
                'panel_name': 'Real-Time Price Overview',
                'panel_type': 'predefined',
                'iframe_src': f'{grafana_url}/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=14&refresh=30s',
                'grid_column': 2
            },
            {
                'panel_id': 'chart2',
                'panel_name': 'System Available Capacity',
                'panel_type': 'predefined',
                'iframe_src': f'{grafana_url}/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=7&refresh=30s',
                'grid_column': 1
            },
            {
                'panel_id': 'chart3',
                'panel_name': 'Emergency & Outage Status',
                'panel_type': 'predefined',
                'iframe_src': f'{grafana_url}/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=1&refresh=30s',
                'grid_column': 1
            },
            {
                'panel_id': 'chart4',
                'panel_name': 'Reserve Capacity Overview',
                'panel_type': 'predefined',
                'iframe_src': f'{grafana_url}/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=12&refresh=30s',
                'grid_column': 2
            },
            {
                'panel_id': 'chart5',
                'panel_name': 'Settlement Point Prices',
                'panel_type': 'predefined',
                'iframe_src': f'{grafana_url}/d-solo/bep90j9gjtb0gf/ercot?orgId=1&panelId=13&refresh=30s',
                'grid_column': 2
            }
        ]
        
        # FIXED: Get AI panels from dashboard settings instead of ai_visualizations table
        # This ensures we only show AI panels that are actually available for the dashboard
        cursor.execute("""
            SELECT uds.panel_id, uds.panel_name, uds.panel_type, uds.iframe_src, 
                   uds.ai_visualization_id, uds.dashboard_uid, uds.panel_grid_column,
                   av.created_at, av.request_text
            FROM user_dashboard_settings uds
            LEFT JOIN ai_visualizations av ON uds.ai_visualization_id = av.id
            WHERE uds.user_id = %s AND uds.panel_type = 'ai_generated'
            ORDER BY uds.created_at DESC
        """, (user['id'],))
        
        ai_dashboard_panels = cursor.fetchall()
        
        ai_panels = []
        for panel in ai_dashboard_panels:
            if panel['iframe_src']:  # Only include panels with valid iframe sources
                ai_panels.append({
                    'panel_id': panel['panel_id'],
                    'panel_name': panel['panel_name'],
                    'panel_type': 'ai_generated',
                    'iframe_src': panel['iframe_src'],
                    'ai_visualization_id': panel['ai_visualization_id'],
                    'dashboard_uid': panel['dashboard_uid'],
                    'grid_column': panel['panel_grid_column'] or 2,
                    'created_at': panel['created_at'].isoformat() if panel['created_at'] else None,
                    'request_text': panel['request_text']
                })
        
        cursor.close()
        conn.close()
        
        logger.info(f"📊 Found {len(ai_panels)} AI-generated panels for user {user['id']}")
        
        return {
            'predefined_panels': predefined_panels,
            'ai_generated_panels': ai_panels
        }
        
    except Exception as e:
        logger.error(f"Error fetching available panels: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch available panels")

# API Key management routes
@app.post("/api/keys", response_model=APIKeyResponse)
async def create_api_key(
    key_create: APIKeyCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new API key for the authenticated user"""
    try:
        api_key, api_secret, secret_hash = generate_api_credentials()
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            INSERT INTO api_keys (user_id, key_name, api_key, api_secret_hash)
            VALUES (%s, %s, %s, %s)
            RETURNING id, key_name, api_key, rate_limit_per_hour, rate_limit_per_day, created_at, expires_at
        """, (user['id'], key_create.key_name, api_key, secret_hash))
        
        key_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return APIKeyResponse(
            id=key_data['id'],
            key_name=key_data['key_name'],
            api_key=key_data['api_key'],
            api_secret=api_secret,  # Only returned once!
            rate_limit_per_hour=key_data['rate_limit_per_hour'],
            rate_limit_per_day=key_data['rate_limit_per_day'],
            created_at=key_data['created_at'].isoformat(),
            expires_at=key_data['expires_at'].isoformat() if key_data['expires_at'] else None
        )
        
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to create API key")

@app.get("/api/keys")
async def list_api_keys(user: dict = Depends(get_current_user)):
    """List all API keys for the authenticated user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, key_name, api_key, is_active, rate_limit_per_hour, rate_limit_per_day,
                   created_at, last_used_at, usage_count, expires_at
            FROM api_keys 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """, (user['id'],))
        
        keys = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Mask API keys (show only last 8 characters)
        for key in keys:
            key['api_key'] = f"...{key['api_key'][-8:]}"
            if key['created_at']:
                key['created_at'] = key['created_at'].isoformat()
            if key['last_used_at']:
                key['last_used_at'] = key['last_used_at'].isoformat()
            if key['expires_at']:
                key['expires_at'] = key['expires_at'].isoformat()
        
        return keys
        
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        raise HTTPException(status_code=500, detail="Failed to list API keys")

@app.delete("/api/keys/{key_id}")
async def delete_api_key(key_id: int, user: dict = Depends(get_current_user)):
    """Delete an API key"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM api_keys 
            WHERE id = %s AND user_id = %s
        """, (key_id, user['id']))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="API key not found")
        
        cursor.close()
        conn.close()
        
        return {"message": "API key deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete API key")

# API Documentation route
@app.get("/api/docs", response_class=HTMLResponse)
async def api_documentation(request: Request, user: dict = Depends(get_current_user_optional)):
    if not user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("api_docs.html", {"request": request, "user": user})

# Protected API endpoints for ERCOT data
@app.get("/api/v1/settlement-prices")
@require_api_key
async def get_settlement_prices(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    hub: Optional[str] = Query(None, description="Specific hub (e.g., 'houston', 'north', 'south', 'west')"),
    limit: int = Query(1000, description="Maximum number of records", le=10000)
):
    """Get ERCOT settlement point prices with optional filtering"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query based on parameters
        where_clauses = []
        params = []
        
        # Default to last 24 hours if no dates specified
        if not start_date and not end_date:
            where_clauses.append("timestamp >= NOW() - INTERVAL '24 hours'")
        else:
            if start_date:
                where_clauses.append("timestamp >= %s")
                params.append(start_date)
            if end_date:
                where_clauses.append("timestamp <= %s")
                params.append(end_date)
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Select columns based on hub filter
        if hub:
            hub_columns = {
                'houston': 'hb_houston, lz_houston',
                'north': 'hb_north, lz_north', 
                'south': 'hb_south, lz_south',
                'west': 'hb_west, lz_west',
                'busavg': 'hb_busavg',
                'hubavg': 'hb_hubavg'
            }
            columns = f"timestamp, oper_day, interval_ending, {hub_columns.get(hub, '*')}"
        else:
            columns = "*"
        
        query = f"""
            SELECT {columns}
            FROM ercot_settlement_prices 
            WHERE {where_clause}
            ORDER BY timestamp DESC 
            LIMIT %s
        """
        params.append(limit)
        
        cursor.execute(query, params)
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert timestamps to ISO format
        for row in data:
            if 'timestamp' in row and row['timestamp']:
                row['timestamp'] = row['timestamp'].isoformat()
            if 'oper_day' in row and row['oper_day']:
                row['oper_day'] = row['oper_day'].isoformat()
        
        return {
            "data": [dict(row) for row in data],
            "count": len(data),
            "filtered_by": {
                "start_date": start_date,
                "end_date": end_date,
                "hub": hub,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching settlement prices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch settlement prices")

@app.get("/api/v1/capacity-monitor")
@require_api_key
async def get_capacity_monitor(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    subcategory: Optional[str] = Query(None, description="Filter by subcategory"),
    limit: int = Query(1000, description="Maximum number of records", le=10000)
):
    """Get ERCOT capacity monitor data (ancillary services)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query
        where_clauses = []
        params = []
        
        # Default to last 24 hours if no dates specified
        if not start_date and not end_date:
            where_clauses.append("timestamp >= NOW() - INTERVAL '24 hours'")
        else:
            if start_date:
                where_clauses.append("timestamp >= %s")
                params.append(start_date)
            if end_date:
                where_clauses.append("timestamp <= %s")
                params.append(end_date)
        
        if category:
            where_clauses.append("category = %s")
            params.append(category)
            
        if subcategory:
            where_clauses.append("subcategory = %s")
            params.append(subcategory)
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
            SELECT timestamp, category, subcategory, value, unit
            FROM ercot_capacity_monitor 
            WHERE {where_clause}
            ORDER BY timestamp DESC 
            LIMIT %s
        """
        params.append(limit)
        
        cursor.execute(query, params)
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert timestamps
        for row in data:
            if row['timestamp']:
                row['timestamp'] = row['timestamp'].isoformat()
        
        return {
            "data": [dict(row) for row in data],
            "count": len(data),
            "filtered_by": {
                "start_date": start_date,
                "end_date": end_date,
                "category": category,
                "subcategory": subcategory,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching capacity monitor data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch capacity monitor data")

# Metadata endpoints
@app.get("/api/v1/settlement-prices/metadata")
@require_api_key
async def get_settlement_prices_metadata(request: Request):
    """Get metadata about settlement prices data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get date range
        cursor.execute("""
            SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest, COUNT(*) as total_records
            FROM ercot_settlement_prices
        """)
        date_info = cursor.fetchone()
        
        # Get available hubs (column names)
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'ercot_settlement_prices' 
            AND (column_name LIKE 'hb_%' OR column_name LIKE 'lz_%')
            ORDER BY column_name
        """)
        hubs = [row['column_name'] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return {
            "table": "ercot_settlement_prices",
            "description": "Real-time settlement point prices from ERCOT",
            "date_range": {
                "earliest": date_info['earliest'].isoformat() if date_info['earliest'] else None,
                "latest": date_info['latest'].isoformat() if date_info['latest'] else None,
                "total_records": date_info['total_records']
            },
            "available_hubs": hubs,
            "update_frequency": "Every 15 minutes",
            "data_retention": "Historical data available"
        }
        
    except Exception as e:
        logger.error(f"Error fetching metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch metadata")

@app.get("/api/v1/capacity-monitor/metadata")
@require_api_key
async def get_capacity_monitor_metadata(request: Request):
    """Get metadata about capacity monitor data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get date range
        cursor.execute("""
            SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest, COUNT(*) as total_records
            FROM ercot_capacity_monitor
        """)
        date_info = cursor.fetchone()
        
        # Get available categories and subcategories
        cursor.execute("""
            SELECT DISTINCT category, subcategory, unit
            FROM ercot_capacity_monitor 
            ORDER BY category, subcategory
        """)
        categories = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "table": "ercot_capacity_monitor",
            "description": "ERCOT capacity and ancillary services monitoring data",
            "date_range": {
                "earliest": date_info['earliest'].isoformat() if date_info['earliest'] else None,
                "latest": date_info['latest'].isoformat() if date_info['latest'] else None,
                "total_records": date_info['total_records']
            },
            "available_categories": [dict(cat) for cat in categories],
            "update_frequency": "Every minute",
            "data_retention": "Historical data available"
        }
        
    except Exception as e:
        logger.error(f"Error fetching metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch metadata")

# FIXED Enhanced AI Visualization routes
@app.post("/api/ai/visualizations")
async def create_ai_visualization_enhanced(
    viz_request: AIVisualizationRequest,
    user: dict = Depends(get_current_user)
):
    """FIXED Enhanced AI visualization creation with automatic dashboard integration"""
    logger.info(f"🤖 Starting AI visualization creation for user {user['id']}: '{viz_request.request_text}'")
    
    if AI_SYSTEM_AVAILABLE:
        try:
            # Get the AI processor
            processor = get_ai_processor()
            
            # Process the request
            logger.info(f"🔄 Processing AI request for user {user['id']}")
            result = await processor.process_user_request(
                user_id=user['id'],
                request_text=viz_request.request_text,
                visualization_type=viz_request.visualization_type
            )
            
            logger.info(f"📊 AI processing result for user {user['id']}: success={result.get('success')}, viz_id={result.get('visualization_id')}")
            
            if result['success'] and result.get('grafana_dashboard', {}).get('success'):
                viz_id = result['visualization_id']
                
                # FIXED: Check for existing panels to prevent duplicates
                existing_panel_id = await check_for_existing_ai_panel(user['id'], viz_id)
                
                if existing_panel_id:
                    logger.warning(f"⚠️ AI visualization {viz_id} already exists on dashboard as {existing_panel_id}")
                    return {
                        "message": "AI visualization already exists on your dashboard",
                        "visualization_id": viz_id,
                        "analysis": result['analysis'],
                        "data_preview": result['data_preview'],
                        "grafana_dashboard": result.get('grafana_dashboard'),
                        "ai_powered": True,
                        "added_to_dashboard": True
                    }
                
                # Validate Grafana dashboard data before adding
                grafana_info = result.get('grafana_dashboard', {})
                iframe_src = grafana_info.get('panel_embed_url') or grafana_info.get('embed_url', '')
                
                if not iframe_src:
                    logger.error(f"❌ No valid iframe URL found for visualization {viz_id}")
                    raise HTTPException(status_code=400, detail="AI visualization created but no valid dashboard URL generated")
                
                logger.info(f"✅ Adding AI visualization {viz_id} to dashboard with URL: {iframe_src}")
                
                # Add to dashboard only if it doesn't already exist and has valid data
                await add_ai_visualization_to_dashboard(user['id'], result)
                
                return {
                    "message": "AI visualization created and added to your dashboard",
                    "visualization_id": viz_id,
                    "analysis": result['analysis'],
                    "data_preview": result['data_preview'],
                    "grafana_dashboard": result.get('grafana_dashboard'),
                    "ai_powered": True,
                    "added_to_dashboard": True
                }
            elif result['success']:
                logger.warning(f"⚠️ AI visualization {result.get('visualization_id')} created but no Grafana dashboard")
                return {
                    "message": "AI analysis completed successfully",
                    "visualization_id": result['visualization_id'],
                    "analysis": result['analysis'],
                    "data_preview": result['data_preview'],
                    "ai_powered": True,
                    "added_to_dashboard": False
                }
            else:
                logger.error(f"❌ AI visualization creation failed: {result.get('message')}")
                raise HTTPException(status_code=400, detail=result['message'])
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Enhanced AI visualization creation error: {e}")
            # Fall back to basic method
            return await create_ai_visualization_fallback(viz_request, user)
    else:
        logger.warning("⚠️ AI system not available, using fallback method")
        # AI system not available, use basic method
        return await create_ai_visualization_fallback(viz_request, user)

async def check_for_existing_ai_panel(user_id: int, viz_id: int) -> Optional[str]:
    """Check if an AI visualization is already on the dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT panel_id FROM user_dashboard_settings 
            WHERE user_id = %s AND ai_visualization_id = %s
        """, (user_id, viz_id))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return result[0] if result else None
        
    except Exception as e:
        logger.error(f"Error checking for existing AI panel: {e}")
        return None

async def add_ai_visualization_to_dashboard(user_id: int, result: Dict[str, Any]):
    """FIXED Add AI visualization to user's dashboard settings with deduplication and validation"""
    try:
        viz_id = result['visualization_id']
        grafana_info = result['grafana_dashboard']
        analysis = result['analysis']
        
        # Validate required data
        if not grafana_info or not grafana_info.get('success'):
            logger.error(f"❌ Invalid Grafana info for visualization {viz_id}")
            return
            
        iframe_src = grafana_info.get('panel_embed_url') or grafana_info.get('embed_url', '')
        if not iframe_src:
            logger.error(f"❌ No iframe source URL for visualization {viz_id}")
            return
            
        dashboard_uid = grafana_info.get('dashboard_uid')
        if not dashboard_uid:
            logger.error(f"❌ No dashboard UID for visualization {viz_id}")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # FIXED: Double-check if this visualization is already on the dashboard
        cursor.execute("""
            SELECT panel_id, panel_name FROM user_dashboard_settings 
            WHERE user_id = %s AND ai_visualization_id = %s
        """, (user_id, viz_id))
        
        existing = cursor.fetchone()
        if existing:
            logger.warning(f"⚠️ AI visualization {viz_id} already exists on dashboard as {existing[0]} ({existing[1]})")
            cursor.close()
            conn.close()
            return
        
        # Get the next panel order
        cursor.execute("""
            SELECT COALESCE(MAX(panel_order), 0) + 1
            FROM user_dashboard_settings 
            WHERE user_id = %s
        """, (user_id,))
        next_order = cursor.fetchone()[0]
        
        # FIXED: Clean up panel name to avoid double "AI:" prefix
        title = analysis.get('title', 'Custom Visualization')
        if title.startswith('AI: '):
            panel_name = title
        else:
            panel_name = f"AI: {title}"
        
        panel_id = f"ai_viz_{viz_id}"
        
        logger.info(f"🔄 Adding AI visualization to dashboard:")
        logger.info(f"   - Panel ID: {panel_id}")
        logger.info(f"   - Panel Name: {panel_name}")
        logger.info(f"   - Iframe URL: {iframe_src}")
        logger.info(f"   - Dashboard UID: {dashboard_uid}")
        logger.info(f"   - Panel Order: {next_order}")
        
        # Add to dashboard settings with conflict resolution
        cursor.execute("""
            INSERT INTO user_dashboard_settings 
            (user_id, panel_id, panel_name, panel_type, is_visible, panel_order, 
             panel_grid_column, iframe_src, ai_visualization_id, dashboard_uid)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, panel_id) DO UPDATE SET
                panel_name = EXCLUDED.panel_name,
                iframe_src = EXCLUDED.iframe_src,
                dashboard_uid = EXCLUDED.dashboard_uid,
                updated_at = CURRENT_TIMESTAMP
        """, (
            user_id, panel_id, panel_name, 'ai_generated', True, next_order,
            2, iframe_src, viz_id, dashboard_uid  # Full width for AI panels
        ))
        
        rows_affected = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if rows_affected > 0:
            logger.info(f"✅ Successfully added AI visualization {viz_id} to dashboard for user {user_id}")
        else:
            logger.warning(f"⚠️ No rows affected when adding AI visualization {viz_id} to dashboard")
        
    except Exception as e:
        logger.error(f"❌ Error adding AI visualization to dashboard: {e}")
        # Don't raise the exception, just log it so the main process can continue

async def create_ai_visualization_fallback(viz_request: AIVisualizationRequest, user: dict):
    """Fallback method using basic storage"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            INSERT INTO ai_visualizations (user_id, request_text, visualization_type, status)
            VALUES (%s, %s, %s, %s)
            RETURNING id, request_text, visualization_type, status, created_at
        """, (user['id'], viz_request.request_text, viz_request.visualization_type, 'pending'))
        
        visualization = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if visualization['created_at']:
            visualization['created_at'] = visualization['created_at'].isoformat()
        
        return {
            "message": "AI visualization request created (basic mode)",
            "visualization": dict(visualization),
            "ai_powered": False,
            "added_to_dashboard": False
        }
        
    except Exception as e:
        logger.error(f"Fallback AI visualization creation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create AI visualization")

@app.get("/api/ai/visualizations")
async def get_user_visualizations(user: dict = Depends(get_current_user)):
    """Get all AI visualizations for the current user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, request_text, visualization_type, status, created_at, completed_at, error_message
            FROM ai_visualizations 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """, (user['id'],))
        
        visualizations = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for viz in visualizations:
            if viz['created_at']:
                viz['created_at'] = viz['created_at'].isoformat()
            if viz['completed_at']:
                viz['completed_at'] = viz['completed_at'].isoformat()
        
        return [dict(viz) for viz in visualizations]
        
    except Exception as e:
        logger.error(f"Error fetching visualizations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch visualizations")

@app.post("/api/ai/visualizations/langgraph")
async def create_ai_visualization_langgraph(viz_request: AIVisualizationRequest, user: dict = Depends(get_current_user)):
    """Create AI visualization using LangGraph workflow"""
    
    if not LANGGRAPH_AVAILABLE:
        raise HTTPException(status_code=503, detail="LangGraph AI system not available")
    
    logger.info(f"🚀 LangGraph AI visualization request from user {user['id']}: {viz_request.request_text}")
    
    try:
        # Process the visualization request using LangGraph
        result = await langgraph_visualizer.process_visualization_request(
            user_id=user['id'],
            request_text=viz_request.request_text,
            visualization_type=viz_request.visualization_type
        )
        
        if result['success']:
            logger.info(f"✅ LangGraph AI visualization completed successfully: {result['visualization_id']}")
            return {
                "message": "AI visualization created successfully using LangGraph",
                "visualization_id": result['visualization_id'],
                "dashboard_uid": result['dashboard_uid'],
                "iframe_url": result['iframe_url'],
                "title": result['title'],
                "sql_query": result['sql_query'],
                "workflow": "langgraph",
                "ai_powered": True,
                "added_to_dashboard": True
            }
        else:
            logger.error(f"❌ LangGraph AI visualization failed: {result['errors']}")
            return {
                "message": "AI visualization failed",
                "errors": result['errors'],
                "workflow": "langgraph",
                "ai_powered": True,
                "added_to_dashboard": False
            }
    
    except Exception as e:
        logger.error(f"❌ LangGraph AI visualization error: {e}")
        raise HTTPException(status_code=500, detail=f"LangGraph AI visualization failed: {str(e)}")

@app.get("/api/ai/test-auth")
async def test_auth(user: dict = Depends(get_current_user)):
    """Test endpoint to debug authentication"""
    return {
        "message": "Authentication working",
        "user_id": user['id'],
        "user_email": user['email']
    }

@app.get("/api/ai/debug/dashboard-entries")
async def debug_dashboard_entries(user: dict = Depends(get_current_user)):
    """Debug endpoint to check for duplicate or invalid dashboard entries"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get all AI-generated dashboard entries for this user
        cursor.execute("""
            SELECT uds.panel_id, uds.panel_name, uds.panel_type, uds.is_visible, 
                   uds.iframe_src, uds.ai_visualization_id, uds.dashboard_uid,
                   uds.created_at, uds.updated_at, av.request_text, av.status
            FROM user_dashboard_settings uds
            LEFT JOIN ai_visualizations av ON uds.ai_visualization_id = av.id
            WHERE uds.user_id = %s AND uds.panel_type = 'ai_generated'
            ORDER BY uds.created_at DESC
        """, (user['id'],))
        
        dashboard_entries = cursor.fetchall()
        
        # Check for duplicates by ai_visualization_id
        cursor.execute("""
            SELECT ai_visualization_id, COUNT(*) as count
            FROM user_dashboard_settings 
            WHERE user_id = %s AND panel_type = 'ai_generated' AND ai_visualization_id IS NOT NULL
            GROUP BY ai_visualization_id
            HAVING COUNT(*) > 1
        """, (user['id'],))
        
        duplicates = cursor.fetchall()
        
        # Check for entries with missing iframe_src
        cursor.execute("""
            SELECT panel_id, panel_name, ai_visualization_id
            FROM user_dashboard_settings 
            WHERE user_id = %s AND panel_type = 'ai_generated' 
            AND (iframe_src IS NULL OR iframe_src = '')
        """, (user['id'],))
        
        missing_urls = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Convert timestamps
        for entry in dashboard_entries:
            if entry['created_at']:
                entry['created_at'] = entry['created_at'].isoformat()
            if entry['updated_at']:
                entry['updated_at'] = entry['updated_at'].isoformat()
        
        return {
            "user_id": user['id'],
            "total_ai_dashboard_entries": len(dashboard_entries),
            "dashboard_entries": [dict(entry) for entry in dashboard_entries],
            "duplicates_by_viz_id": [dict(dup) for dup in duplicates],
            "entries_missing_urls": [dict(entry) for entry in missing_urls],
            "has_duplicates": len(duplicates) > 0,
            "has_missing_urls": len(missing_urls) > 0
        }
        
    except Exception as e:
        logger.error(f"Error in debug dashboard entries: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch debug info")

@app.post("/api/ai/debug/cleanup-duplicates")
async def cleanup_duplicate_dashboard_entries(user: dict = Depends(get_current_user)):
    """Clean up duplicate or invalid AI dashboard entries"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Remove entries with no iframe_src
        cursor.execute("""
            DELETE FROM user_dashboard_settings 
            WHERE user_id = %s AND panel_type = 'ai_generated' 
            AND (iframe_src IS NULL OR iframe_src = '')
        """, (user['id'],))
        
        removed_no_url = cursor.rowcount
        
        # For duplicates by ai_visualization_id, keep only the most recent one
        cursor.execute("""
            DELETE FROM user_dashboard_settings 
            WHERE user_id = %s AND panel_type = 'ai_generated'
            AND id NOT IN (
                SELECT DISTINCT ON (ai_visualization_id) id
                FROM user_dashboard_settings 
                WHERE user_id = %s AND panel_type = 'ai_generated'
                AND ai_visualization_id IS NOT NULL
                ORDER BY ai_visualization_id, created_at DESC
            )
            AND ai_visualization_id IS NOT NULL
        """, (user['id'], user['id']))
        
        removed_duplicates = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"🧹 Cleanup for user {user['id']}: removed {removed_no_url} entries with no URL, {removed_duplicates} duplicates")
        
        return {
            "message": "Cleanup completed",
            "removed_entries_no_url": removed_no_url,
            "removed_duplicate_entries": removed_duplicates,
            "total_removed": removed_no_url + removed_duplicates
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup duplicates: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup duplicates")

@app.delete("/api/ai/visualizations/clear")
async def clear_all_visualizations(user: dict = Depends(get_current_user)):
    """FIXED Clear all AI visualizations and remove from dashboard"""
    try:
        logger.info(f"🗑️ Clearing all visualizations for user {user['id']}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, remove AI panels from dashboard settings
        cursor.execute("""
            DELETE FROM user_dashboard_settings 
            WHERE user_id = %s AND panel_type = 'ai_generated'
        """, (user['id'],))
        
        dashboard_panels_deleted = cursor.rowcount
        
        # Then delete AI visualizations
        cursor.execute("""
            DELETE FROM ai_visualizations 
            WHERE user_id = %s
        """, (user['id'],))
        
        visualizations_deleted = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Deleted {visualizations_deleted} visualizations and {dashboard_panels_deleted} dashboard panels for user {user['id']}")
        
        return {
            "success": True,
            "message": f"Cleared {visualizations_deleted} visualizations and removed {dashboard_panels_deleted} dashboard panels",
            "visualizations_deleted": visualizations_deleted,
            "dashboard_panels_deleted": dashboard_panels_deleted
        }
        
    except Exception as e:
        logger.error(f"❌ Error clearing visualizations for user {user.get('id', 'unknown')}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear visualizations: {str(e)}")

# Original data API endpoints (unchanged)
@app.get("/api/data")
async def get_data():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM ercot_capacity_monitor ORDER BY timestamp DESC LIMIT 100")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for row in data:
            if 'timestamp' in row:
                row['timestamp'] = row['timestamp'].isoformat()
        
        return data
    except Exception as e:
        logger.error(f"Database query error: {e}")
        raise HTTPException(status_code=500, detail="Database query error")

@app.get("/api/ercot-data")
async def get_ercot_data():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT timestamp, category, subcategory, value, unit 
            FROM ercot_capacity_monitor 
            WHERE timestamp >= NOW() - INTERVAL '6 hours'
            ORDER BY timestamp DESC
        """)
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for row in data:
            if 'timestamp' in row:
                row['timestamp'] = row['timestamp'].isoformat()
        
        return data
    except Exception as e:
        logger.error(f"ERCOT data query error: {e}")
        raise HTTPException(status_code=500, detail="ERCOT data query error")

@app.get("/api/price-data")
async def get_price_data():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT timestamp, oper_day, interval_ending, hb_busavg, hb_houston, 
                   hb_hubavg, hb_north, lz_houston, lz_north, lz_south, lz_west
            FROM ercot_settlement_prices 
            WHERE timestamp >= NOW() - INTERVAL '48 hours'
            ORDER BY timestamp DESC
            LIMIT 1000
        """)
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for row in data:
            if 'timestamp' in row:
                row['timestamp'] = row['timestamp'].isoformat()
            if 'oper_day' in row:
                row['oper_day'] = row['oper_day'].isoformat()
        
        return data
    except Exception as e:
        logger.error(f"Price data query error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch price data")

@app.get("/health")
async def health():
    ai_status = "available" if AI_SYSTEM_AVAILABLE else "not_available"
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "ai_system": ai_status
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=80,
        reload=True
    )