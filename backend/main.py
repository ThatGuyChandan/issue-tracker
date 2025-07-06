from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import router as api_router
from app.realtime import router as realtime_router
from app.logging_config import logger
from app.metrics import metrics_router
logger.info("Issues & Insights Tracker API starting up")
import uvicorn
app = FastAPI(title="Issues & Insights Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(metrics_router)
# Mount WebSocket app
# app.mount("/notification", socket_app)
app.include_router(realtime_router)
@app.get("/health")
def health():
    return {"status": "ok"} 


    # try:
    #     while True:
    #         data = await websocket.receive_text()
    #         await manager.send_personal_message(f"You said: {data}", websocket)
    #         await manager.broadcast(f"Client #{websocket.client.host} says: {data}")
    # except WebSocketDisconnect:
    #     manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)