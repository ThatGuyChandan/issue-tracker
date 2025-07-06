from prometheus_client import Counter, generate_latest
from fastapi import APIRouter, Response

issue_created_counter = Counter('issue_created_total', 'Total number of issues created')

metrics_router = APIRouter()

@metrics_router.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain") 