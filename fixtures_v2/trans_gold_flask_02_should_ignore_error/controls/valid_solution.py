def configure_error_policy(app, exc_class):
    # Valid pattern: registers teardown handler or errorhandler
    @app.teardown_request
    def handle_teardown(exc):
        pass
