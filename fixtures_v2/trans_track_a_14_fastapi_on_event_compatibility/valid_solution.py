from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    app.state.started = True
    yield
    app.state.started = False

def setup_lifecycle_hook(app):
    app.router.lifespan_context = lifespan
    return app
