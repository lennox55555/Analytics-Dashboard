import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
from starlette.middleware.cors import CORSMiddleware
import uvicorn
import ssl
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Analytics Dashboard")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database connection function
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
        raise HTTPException(status_code=500, detail="Database connection error")

# Home route
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# API endpoints
@app.get("/api/data")
async def get_data():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM apple_stock LIMIT 100")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return data
    except Exception as e:
        logger.error(f"Database query error: {e}")
        raise HTTPException(status_code=500, detail="Database query error")

# Proxy all Grafana requests
@app.get("/grafana{path:path}")
@app.post("/grafana{path:path}")
@app.put("/grafana{path:path}")
@app.delete("/grafana{path:path}")
async def proxy_grafana(request: Request, path: str):
    grafana_url = f"http://grafana:3000{path}"
    
    # Forward the request to Grafana
    try:
        method = request.method
        headers = dict(request.headers)
        params = dict(request.query_params)
        
        # Remove host header to avoid conflicts
        if "host" in headers:
            del headers["host"]
            
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(grafana_url, headers=headers, params=params)
            elif method == "POST":
                body = await request.body()
                response = await client.post(grafana_url, headers=headers, params=params, content=body)
            elif method == "PUT":
                body = await request.body()
                response = await client.put(grafana_url, headers=headers, params=params, content=body)
            elif method == "DELETE":
                response = await client.delete(grafana_url, headers=headers, params=params)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
                
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        logger.error(f"Grafana proxy error: {e}")
        raise HTTPException(status_code=500, detail="Grafana proxy error")

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    # SSL Configuration
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(
        certfile=os.getenv("SSL_CERT_FILE", "cert.pem"),
        keyfile=os.getenv("SSL_KEY_FILE", "key.pem")
    )
    
    # Start the server
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=443 if os.getenv("USE_HTTPS", "false").lower() == "true" else 80,
        ssl_certfile=os.getenv("SSL_CERT_FILE", "cert.pem") if os.getenv("USE_HTTPS", "false").lower() == "true" else None,
        ssl_keyfile=os.getenv("SSL_KEY_FILE", "key.pem") if os.getenv("USE_HTTPS", "false").lower() == "true" else None,
        reload=True
    )