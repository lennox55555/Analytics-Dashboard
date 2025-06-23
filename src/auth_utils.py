# auth_utils.py
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db_connection import get_db_connection
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

# Security configuration with validation
try:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        logger.warning("SECRET_KEY environment variable not set. Using default (INSECURE for production!)")
        SECRET_KEY = "your-secret-key-change-this-in-production"
    elif SECRET_KEY == "your-secret-key-change-this-in-production":
        logger.critical("Using default SECRET_KEY in production! This is a security risk!")
    elif len(SECRET_KEY) < 32:
        logger.warning(f"SECRET_KEY is too short ({len(SECRET_KEY)} chars). Recommended: 32+ characters")
except Exception as e:
    logger.error(f"Error reading SECRET_KEY: {e}")
    SECRET_KEY = "your-secret-key-change-this-in-production"

ALGORITHM = "HS256"

try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours default
    if ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
        logger.warning("Invalid ACCESS_TOKEN_EXPIRE_MINUTES, using default 24 hours")
        ACCESS_TOKEN_EXPIRE_MINUTES = 1440
except (ValueError, TypeError) as e:
    logger.error(f"Error parsing ACCESS_TOKEN_EXPIRE_MINUTES: {e}. Using default 24 hours")
    ACCESS_TOKEN_EXPIRE_MINUTES = 1440

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class AuthManager:
    def __init__(self):
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM
        
    def get_db_connection(self):
        """Get database connection using shared module"""
        return get_db_connection()
    
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
        """Verify and decode JWT token with enhanced error handling"""
        if not token or not isinstance(token, str):
            logger.warning("Invalid token format provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format"
            )
            
        if len(token) > 2048:  # Reasonable token length limit
            logger.warning("Token too long, possible attack")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Validate payload structure
            if not isinstance(payload, dict):
                logger.warning("Invalid token payload structure")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
                
            # Check for required fields
            if 'sub' not in payload:
                logger.warning("Token missing required 'sub' field")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
                
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.info("Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            logger.warning("Invalid token signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature"
            )
        except jwt.DecodeError:
            logger.warning("Token decode error")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not decode token"
            )
        except jwt.JWTError as e:
            logger.error(f"JWT error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email with comprehensive error handling"""
        if not email or not isinstance(email, str):
            logger.warning(f"Invalid email provided: {email}")
            return None
            
        # Basic email validation
        if '@' not in email or len(email) > 255:
            logger.warning(f"Invalid email format: {email}")
            return None
            
        conn = None
        cursor = None
        
        try:
            conn = self.get_db_connection()
            if not conn:
                logger.error("Failed to get database connection in get_user_by_email")
                return None
                
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, email, username, password_hash, first_name, last_name, 
                       is_active, is_verified, created_at, last_login
                FROM users 
                WHERE email = %s AND is_active = true
            """, (email.lower().strip(),))  # Normalize email
            
            user = cursor.fetchone()
            
            if user:
                return dict(user)
            else:
                logger.debug(f"No active user found with email: {email}")
                return None
                
        except psycopg2.Error as e:
            logger.error(f"Database error getting user by email: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting user by email: {e}")
            return None
        finally:
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
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID with comprehensive error handling"""
        if not user_id or not isinstance(user_id, int) or user_id <= 0:
            logger.warning(f"Invalid user_id provided: {user_id}")
            return None
            
        conn = None
        cursor = None
        
        try:
            conn = self.get_db_connection()
            if not conn:
                logger.error("Failed to get database connection in get_user_by_id")
                return None
                
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, email, username, first_name, last_name, 
                       is_active, is_verified, created_at, last_login
                FROM users 
                WHERE id = %s AND is_active = true
            """, (user_id,))
            
            user = cursor.fetchone()
            
            if user:
                return dict(user)
            else:
                logger.debug(f"No active user found with ID: {user_id}")
                return None
                
        except psycopg2.Error as e:
            logger.error(f"Database error getting user by ID: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting user by ID: {e}")
            return None
        finally:
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
