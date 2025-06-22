# auth_utils.py
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class AuthManager:
    def __init__(self):
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM
        
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(
            host=os.environ.get('DB_HOST', 'dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com'),
            database=os.environ.get('DB_NAME', 'analytics'),
            user=os.environ.get('DB_USER', 'dbuser'),
            password=os.environ.get('DB_PASSWORD', 'Superman1262!')
        )
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, email, username, password_hash, first_name, last_name, 
                       is_active, is_verified, created_at, last_login
                FROM users 
                WHERE email = %s AND is_active = true
            """, (email,))
            
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return dict(user) if user else None
            
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, email, username, first_name, last_name, 
                       is_active, is_verified, created_at, last_login
                FROM users 
                WHERE id = %s AND is_active = true
            """, (user_id,))
            
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return dict(user) if user else None
            
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def create_user(self, email: str, username: str, password: str, 
                   first_name: str = None, last_name: str = None) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        try:
            # Check if user already exists
            if self.get_user_by_email(email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Hash password
            password_hash = self.get_password_hash(password)
            
            # Insert user
            cursor.execute("""
                INSERT INTO users (email, username, password_hash, first_name, last_name)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, email, username, first_name, last_name, is_active, is_verified, created_at
            """, (email, username, password_hash, first_name, last_name))
            
            user = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()
            
            return dict(user) if user else None
            
        except psycopg2.IntegrityError as e:
            if "username" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User creation failed"
            )
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed"
            )
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password"""
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        if not self.verify_password(password, user['password_hash']):
            return None
        
        # Update last login
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                (user['id'],)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
        
        return user
    
    def store_session(self, user_id: int, token: str, request: Request) -> None:
        """Store user session"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Hash token for storage
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            # Get client info
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent", "")
            
            # Calculate expiry
            expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            
            cursor.execute("""
                INSERT INTO user_sessions (user_id, token_hash, expires_at, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, token_hash, expires_at, ip_address, user_agent))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing session: {e}")

# Global auth manager instance
auth_manager = AuthManager()

# Dependency to get current user
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user"""
    token = credentials.credentials
    payload = auth_manager.verify_token(token)
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    user = auth_manager.get_user_by_id(int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

# Optional dependency for routes that work with or without auth
def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None
