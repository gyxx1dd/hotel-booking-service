from celery import shared_task

@shared_task
def test_task(x, y):
    return x + y
