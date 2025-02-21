import asyncio
import threading
import random
from loguru import logger
from celery import Celery
from celery.apps.worker import Worker as CeleryWorker
from celery.apps.beat import Beat as CeleryBeat
from celery.beat import PersistentScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from openagent.agent.config import TaskConfig


class SchedulerManager:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.celery_app = None
        self.worker_thread = None
        self.beat_thread = None

    def init_scheduled_tasks(self, tasks_config: dict, task_runner):
        """Initialize and start scheduled tasks from config

        Args:
            tasks_config (dict): Task configuration dictionary
            task_runner: Callback function to run tasks
        """
        logger.info("Initializing scheduled tasks...")

        for task_id, task_config in tasks_config.items():
            if task_config.schedule.type == "queue":
                self._init_celery_task(task_id, task_config, task_runner)
            else:
                async def task_wrapper(query, delay_variation):
                    if delay_variation > 0:
                        delay = random.uniform(0, delay_variation)
                        logger.debug(f"Task '{task_id}' sleeping for {delay} seconds")
                        await asyncio.sleep(delay)
                    await task_runner(query)

                if task_config.cron:
                    self.scheduler.add_job(
                        func=task_wrapper,
                        trigger=CronTrigger.from_crontab(task_config.cron),
                        args=[task_config.query, task_config.delay_variation],
                        id=task_id,
                        name=f"Task_{task_id}",
                    )
                    logger.info(f"Scheduled cron task '{task_id}' with cron expression: {task_config.cron}")
                else:
                    self.scheduler.add_job(
                        func=task_wrapper,
                        trigger=IntervalTrigger(seconds=task_config.interval),
                        args=[task_config.query, task_config.delay_variation],
                        id=task_id,
                        name=f"Task_{task_id}",
                    )
                    logger.info(
                        f"Scheduled local task '{task_id}' with interval: {task_config.interval} seconds and delay variation: {task_config.delay_variation} seconds"
                    )

        # Start the local scheduler if we have any local tasks
        if any(task.schedule.type == "local" for task in tasks_config.values()):
            self.scheduler.start()
            logger.success("Local scheduler started successfully")

    def _init_celery_task(self, task_id: str, task_config: TaskConfig, task_runner):
        """Initialize a Celery task"""
        # Create Celery app if not exists
        if not self.celery_app:
            self.celery_app = Celery(
                "openagent",
                broker=task_config.schedule.broker_url,
                backend=task_config.schedule.result_backend,
            )

            # Configure Celery to run tasks sequentially
            self.celery_app.conf.update(
                task_acks_late=True,
                worker_prefetch_multiplier=1,
                task_track_started=True,
                task_serializer="json",
                accept_content=["json"],
                result_serializer="json",
                timezone="UTC",
                enable_utc=True,
            )

            # Start Celery worker and beat in separate threads
            self._start_celery_threads()

        # Use a simple flag to track task execution status
        task_running = False

        @self.celery_app.task(
            name=f"openagent.task.{task_id}",
            bind=True,
            max_retries=0,
            default_retry_delay=0,
        )
        def celery_task(self_task):
            nonlocal task_running

            if task_running:
                logger.warning(
                    f"Task {task_id} is already running, skipping this execution"
                )
                return None

            task_running = True
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    if task_config.delay_variation > 0:
                        delay = random.uniform(0, task_config.delay_variation)
                        loop.run_until_complete(asyncio.sleep(delay))
                    result = loop.run_until_complete(task_runner(task_config.query))
                    return result
                finally:
                    loop.close()
            except Exception as exc:
                logger.error(f"Task {task_id} failed: {exc}")
                self_task.retry(exc=exc)
            finally:
                task_running = False

        # Add to Celery beat schedule
        self.celery_app.conf.beat_schedule = {
            **self.celery_app.conf.beat_schedule,
            task_id: {
                "task": f"openagent.task.{task_id}",
                "schedule": task_config.interval,
                "options": {
                    "queue": "sequential_queue",
                    "expires": task_config.interval - 1,
                    "ignore_result": True,
                },
            },
        }

        logger.info(
            f"Scheduled Celery task '{task_id}' with interval: {task_config.interval} seconds"
        )

    def _start_celery_threads(self):
        """Start Celery worker and beat in separate threads"""

        def start_worker():
            worker = CeleryWorker(
                app=self.celery_app,
                queues=["sequential_queue"],
                concurrency=1,
                pool="solo",
            )
            worker.start()
            logger.info("Celery worker started in sequential mode")

        def start_beat():
            beat = CeleryBeat(app=self.celery_app, scheduler_cls=PersistentScheduler)
            beat.run()
            logger.info("Celery beat started")

        self.worker_thread = threading.Thread(
            target=start_worker, name="celery_worker_thread", daemon=True
        )
        self.worker_thread.start()

        self.beat_thread = threading.Thread(
            target=start_beat, name="celery_beat_thread", daemon=True
        )
        self.beat_thread.start()

        logger.success("Celery worker and beat threads started in sequential mode")

    def stop(self):
        """Stop all schedulers"""
        # Stop local scheduler
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Local task scheduler stopped")

        # Stop Celery app if exists
        if self.celery_app:
            # Shutdown Celery worker and beat
            self.celery_app.control.shutdown()
            logger.info("Celery worker and beat shutdown initiated")

            # Wait for threads to finish if they exist
            if self.worker_thread:
                self.worker_thread.join(timeout=5)
            if self.beat_thread:
                self.beat_thread.join(timeout=5)

            self.celery_app.control.purge()
            logger.info("Celery tasks purged")
