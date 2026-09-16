from flask.globals import _app_ctx_stack

def activate_application_context(app):
    # Stale pattern: calls removed _app_ctx_stack.push() (PR #4995)
    ctx = app.app_context()
    _app_ctx_stack.push(ctx)
    return ctx
