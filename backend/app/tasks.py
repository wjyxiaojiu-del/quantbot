from celery import Celery
from celery.schedules import crontab
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "quantbot",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
    # 定时任务调度
    beat_schedule={
        "sync-all-daily": {
            "task": "app.tasks.sync_all_stocks_daily",
            "schedule": crontab(hour=16, minute=0, day_of_week="1-5"),  # 周一至周五 16:00
        },
        "sync-stock-list-weekly": {
            "task": "app.tasks.sync_stock_list_task",
            "schedule": crontab(hour=9, minute=0, day_of_week="1"),  # 每周一 9:00
        },
    },
)


@celery_app.task(bind=True)
def sync_stock_kline(self, symbol: str, period: str = "daily"):
    """异步同步单只股票 K 线"""
    from app.core.database import SessionLocal
    from app.services.data.sync_manager import DataSyncManager
    import asyncio

    db = SessionLocal()
    try:
        manager = DataSyncManager(db)
        result = asyncio.get_event_loop().run_until_complete(
            manager.sync_kline(symbol, period)
        )
        return result
    finally:
        db.close()


@celery_app.task
def sync_all_stocks_daily():
    """定时任务：每日收盘后同步全市场日 K"""
    from app.core.database import SessionLocal
    from app.services.data.sync_manager import DataSyncManager
    import asyncio

    db = SessionLocal()
    try:
        manager = DataSyncManager(db)
        symbols = manager.get_all_stock_symbols()
        # 分批提交子任务
        batch_size = 50
        submitted = 0
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            for symbol in batch:
                sync_stock_kline.delay(symbol)
                submitted += 1
        return {"total_stocks": len(symbols), "submitted": submitted}
    finally:
        db.close()


@celery_app.task
def sync_stock_list_task():
    """定时任务：同步股票列表"""
    from app.core.database import SessionLocal
    from app.services.data.sync_manager import DataSyncManager
    import asyncio

    db = SessionLocal()
    try:
        manager = DataSyncManager(db)
        count = asyncio.get_event_loop().run_until_complete(manager.sync_stock_list())
        return {"new_stocks": count}
    finally:
        db.close()
