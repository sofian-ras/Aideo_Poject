from fastapi import Depends
from app.core.database import get_db_session

DB_SESSION_DEPENDENCY = Depends(get_db_session)