from marshmallow.schema import Schema

def get_ip_field_type(ip_cls):
    return Schema.TYPE_MAPPING[ip_cls]
