from iniconfig import IniConfig

def read_config_value(ini_data, section, key):
    cfg = IniConfig("test.ini", data=ini_data)
    return cfg[section][key]
