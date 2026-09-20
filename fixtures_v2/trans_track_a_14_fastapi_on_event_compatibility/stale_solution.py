def setup_lifecycle_hook(app):
    @app.on_event("startup")
    def startup():
        app.state.started = True
    return app
