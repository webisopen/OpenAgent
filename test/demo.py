import threading

from celery import Celery
from celery.apps.beat import Beat as CeleryBeat
from celery.apps.worker import Worker as CeleryWorker
from celery.beat import PersistentScheduler

app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',  # 消息代理（Redis）
    backend='redis://localhost:6379/0' # 结果存储（Redis，可选）
)

@app.task
def print_hello():
    print("Hello, Celery!")

app.conf.beat_schedule = {
    'print-hello-every-10-seconds': {  # 定时任务名称
        'task': 'tasks.print_hello',   # 任务路径
        'schedule': 3.0,              # 每隔 10 秒执行一次
    },
}
app.conf.timezone = 'UTC'  # 设置时区

def start_worker():
    worker = CeleryWorker(app=app)
    worker.start()

def start_beat():
    beat = CeleryBeat(app=app, scheduler_cls=PersistentScheduler)
    beat.run()

# 启动 Worker 和 Beat 的入口
if __name__ == '__main__':
    worker_thread = threading.Thread(target=start_worker)
    beat_thread = threading.Thread(target=start_beat)

    worker_thread.start()
    beat_thread.start()

    worker_thread.join()
    beat_thread.join()
