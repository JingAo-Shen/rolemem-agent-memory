import marshmallow

def check_marshmallow_export():
    return "fields" in marshmallow.__all__
