from dotenv import load_dotenv
load_dotenv()


from celery import Celery
from celery.schedules import crontab
from . import create_app

# Create the Flask app once for Celery to use
flask_app = create_app()

# Create Celery instance bound to Redis broker/backend
celery = Celery(
    flask_app.import_name,
    broker=flask_app.config['CELERY_BROKER_URL'],
    backend=flask_app.config['CELERY_RESULT_BACKEND'],
)

# Celery config
celery.conf.timezone = 'Asia/Kolkata'
celery.conf.enable_utc = False

class FlaskContextTask(celery.Task):
    """Run Celery tasks inside Flask application context."""
    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)


celery.Task = FlaskContextTask

# Beat schedule: daily reminders + monthly reports
celery.conf.beat_schedule = {
    'send-daily-reminders': {
        'task': 'app.tasks.send_daily_reminders',
        'schedule': crontab(hour=18, minute=0),  # every day at 18:00
    },
    'send-monthly-reports': {
        'task': 'app.tasks.send_monthly_reports',
        'schedule': crontab(hour=9, minute=0, day_of_month='1'),  # 1st of every month at 09:00
    },
}

# Ensure tasks module is imported so @celery.task decorators register
from . import tasks  # noqa: F401
