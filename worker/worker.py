import os
import sys
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date
from apscheduler.schedulers.blocking import BlockingScheduler

# Add backend to Python path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
if os.path.exists(backend_path):
    sys.path.insert(0, backend_path)

try:
    from app.models import Base, Issue, IssueStatus, DailyStats
    from app.database import DATABASE_URL
except ImportError:
    # Fallback for Docker environment
    sys.path.append('/app/backend')
    from app.models import Base, Issue, IssueStatus, DailyStats
    from app.database import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

scheduler = BlockingScheduler()

@scheduler.scheduled_job('interval', minutes=30)
def aggregate_daily_stats():
    try:
        session = SessionLocal()
        today = date.today()
        for status in IssueStatus:
            count = session.query(func.count(Issue.id)).filter(
                Issue.status == status,
                func.date(Issue.created_at) == today
            ).scalar()
            stat = session.query(DailyStats).filter_by(date=today, status=status).first()
            if stat:
                stat.count = count
            else:
                stat = DailyStats(date=today, status=status, count=count)
                session.add(stat)
        session.commit()
        session.close()
        print(f"Aggregated daily stats for {today}")
    except Exception as e:
        print(f"Error aggregating stats: {e}")

if __name__ == "__main__":
    print("Starting worker...")
    scheduler.start() 