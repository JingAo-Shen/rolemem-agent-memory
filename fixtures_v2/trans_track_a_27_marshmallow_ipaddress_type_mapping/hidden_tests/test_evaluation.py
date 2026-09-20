import pytest
import ipaddress
from marshmallow import fields
import ip_schema_helper

def test_ip_field():
    f_cls = ip_schema_helper.get_ip_field_type(ipaddress.IPv4Address)
    assert f_cls is fields.IPv4
    assert f_cls is not fields.String
