def get_task_base(celery_pkg):
    import celery.task
    return celery.task.Task
