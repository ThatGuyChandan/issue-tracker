from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from .models import IssueSeverity, IssueStatus, UserRole

class UserBase(BaseModel):
    email: str
    role: UserRole

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class IssueBase(BaseModel):
    title: str
    description: str
    severity: IssueSeverity = IssueSeverity.LOW
    status: IssueStatus = IssueStatus.OPEN

class IssueCreate(IssueBase):
    pass

class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[IssueSeverity] = None
    status: Optional[IssueStatus] = None

class Issue(IssueBase):
    id: int
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    reporter_id: int

    class Config:
        from_attributes = True

class DailyStatsOut(BaseModel):
    date: str
    total_issues: int
    open_issues: int
    closed_issues: int 