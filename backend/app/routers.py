from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Form
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import logging
from .deps import get_db, get_current_user
from .models import User, Issue, UserRole, IssueSeverity, IssueStatus
from .schemas import UserCreate, UserLogin, IssueCreate, IssueUpdate, Issue as IssueSchema, DailyStatsOut
from .auth import create_access_token, get_password_hash, verify_password
from .realtime import manager

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/auth/register", response_model=dict)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create access token
    access_token = create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({
        "sub": str(user.id), 
        "role": user.role,
        "email": user.email
    })
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=dict)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role
    }

@router.get("/issues", response_model=List[IssueSchema])
def get_issues(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Role-based filtering
    if current_user.role == UserRole.REPORTER:
        return db.query(Issue).filter(Issue.reporter_id == current_user.id).all()
    else:
        return db.query(Issue).all()

@router.post("/issues", response_model=IssueSchema)
async def create_issue(
    issue: IssueCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_issue = Issue(
        title=issue.title,
        description=issue.description,
        severity=issue.severity,
        status=issue.status,
        reporter_id=current_user.id
    )
    db.add(db_issue)
    db.commit()
    db.refresh(db_issue)
    
    # Send real-time notification
    notification_data = {
        "type": "issue_created",
        "issue_id": db_issue.id,
        "title": db_issue.title,
        "reporter_email": current_user.email,
        "reporter_role": current_user.role,
        "severity": db_issue.severity,
        "status": db_issue.status
    }
    
    # Notify maintainers and admins when reporter creates issue
    if current_user.role == UserRole.REPORTER:
        await manager.notify_maintainers_and_admins(notification_data)
    # Also notify all users when admin/maintainer creates issue
    elif current_user.role in [UserRole.ADMIN, UserRole.MAINTAINER]:
        await manager.notify_all_users(notification_data)
    
    return db_issue

@router.put("/issues/{issue_id}", response_model=IssueSchema)
async def update_issue(
    issue_id: int,
    issue_update: IssueUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not db_issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Role-based permissions
    if current_user.role == UserRole.REPORTER:
        if db_issue.reporter_id != current_user.id:
            raise HTTPException(status_code=403, detail="Can only edit your own issues")
        # Reporters can only edit title, description, severity
        if issue_update.status is not None:
            raise HTTPException(status_code=403, detail="Reporters cannot change issue status")
    
    # Update fields
    update_data = issue_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_issue, field, value)
    
    db_issue.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_issue)
    
    # Send real-time notification
    notification_data = {
        "type": "issue_updated",
        "issue_id": db_issue.id,
        "title": db_issue.title,
        "updated_by_email": current_user.email,
        "updated_by_role": current_user.role,
        "severity": db_issue.severity,
        "status": db_issue.status,
        "reporter_id": db_issue.reporter_id
    }
    
    # Notify based on who updated the issue
    if current_user.role in [UserRole.ADMIN, UserRole.MAINTAINER]:
        # ADMIN/MAINTAINER updated issue → Notify the reporter and all maintainers/admins
        if db_issue.reporter_id != current_user.id:
            await manager.notify_reporter(notification_data, str(db_issue.reporter_id))
        await manager.notify_maintainers_and_admins(notification_data)
    elif current_user.role == UserRole.REPORTER:
        # REPORTER updated their own issue → Notify MAINTAINER and ADMIN
        await manager.notify_maintainers_and_admins(notification_data)
    
    return db_issue

@router.delete("/issues/{issue_id}")
async def delete_issue(
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not db_issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Only admins can delete issues
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can delete issues")
    
    # Send real-time notification before deletion
    notification_data = {
        "type": "issue_deleted",
        "issue_id": db_issue.id,
        "title": db_issue.title,
        "deleted_by_email": current_user.email,
        "reporter_id": db_issue.reporter_id
    }
    
    # Notify the reporter and all maintainers/admins
    if db_issue.reporter_id != current_user.id:
        await manager.notify_reporter(notification_data, str(db_issue.reporter_id))
    await manager.notify_maintainers_and_admins(notification_data)
    
    db.delete(db_issue)
    db.commit()
    
    return {"message": "Issue deleted successfully"}

@router.get("/stats/dashboard", response_model=List[DailyStatsOut])
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # This is a placeholder - implement actual stats logic
    return []

@router.get("/debug/connections")
def get_connected_users(current_user: User = Depends(get_current_user)):
    """Debug endpoint to see connected users (admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    return manager.get_connected_users_info()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    user_id = websocket.query_params.get("userid")
    user_role = websocket.query_params.get("role")
    user_email = websocket.query_params.get("email")
    
    if not user_id:
        await websocket.close()
        return

    await manager.connect(websocket, user_id, user_role, user_email)
    
    try:
        while True:
            # Keep connection alive with ping/pong
            data = await websocket.receive_text()
            # Optional: handle any client messages here
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id) 