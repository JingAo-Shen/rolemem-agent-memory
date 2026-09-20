import celery

def check_task_export():
    return "Task" in celery.__all__
