import fastapi.routing

def has_default_lifespan():
    return hasattr(fastapi.routing, "_DefaultLifespan")
