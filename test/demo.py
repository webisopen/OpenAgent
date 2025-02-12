from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import time

# 定义一个简单的任务函数
def my_task():
    print("任务执行中！当前时间：", time.strftime("%Y-%m-%d %H:%M:%S"))

# 创建 BackgroundScheduler 实例
scheduler = BackgroundScheduler()

# 使用 CronTrigger 设置每 15 秒执行一次任务
# 注意：直接指定 second='*/15'，而不是使用 from_crontab
scheduler.add_job(my_task, CronTrigger(second='*/15'), id="task_every_15s")

# 启动调度器
scheduler.start()

print("调度器已启动，按 Ctrl+C 停止程序。")

try:
    # 模拟主程序运行
    while True:
        time.sleep(1)
except (KeyboardInterrupt, SystemExit):
    # 关闭调度器
    scheduler.shutdown()
    print("调度器已关闭。")