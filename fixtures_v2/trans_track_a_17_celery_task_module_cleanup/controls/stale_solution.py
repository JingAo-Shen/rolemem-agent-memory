import celery

def check_task_export():
    return "task" in celery.__all__
