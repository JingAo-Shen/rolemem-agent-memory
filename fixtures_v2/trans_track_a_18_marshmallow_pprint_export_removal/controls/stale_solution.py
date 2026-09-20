import marshmallow

def check_marshmallow_export():
    return "pprint" in marshmallow.__all__
