def configure_error_policy(app, exc_class):
    # Stale pattern: overrides should_ignore_error on Flask instance (PR #5899)
    app.should_ignore_error = lambda err: isinstance(err, exc_class)
