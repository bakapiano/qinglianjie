from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qinglianjie.settings')

app = Celery('qinglianjie')

# celery  -A qinglianjie  worker -l debug
# celery  -A qinglianjie  worker -l debug -Q user_worker

# 
# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.timezone = "Asia/Shanghai"

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "auto_report": {
        "task": "api.tasks.report_daily",
        "schedule": crontab(hour=7, minute=0),
    },
    "auto_collect": {
        "task": "api.tasks.collect_scores",
        "schedule": crontab(hour=7, minute=30),
    },
    "auto_count_courses": {
        "task": "api.tasks.count_courses",
        "schedule": crontab(hour=12, minute=0),
    },
    "auto_get_xk_info": {
        "task": "api.tasks.get_xk_info",
        "schedule": crontab(hour=8, minute=0),
    }
}

app.conf.task_routes = {
    'api.tasks.query_scores': {'queue': 'user_worker'},
    'api.tasks.query_time_table': {'queue': 'user_worker'},
}


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))