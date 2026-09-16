def activate_application_context(app):
    # Valid pattern: calls ctx.push() directly
    ctx = app.app_context()
    ctx.push()
    return ctx
