from pluggy._hooks import varnames

class LegacyHookSpec:
    def my_hook(arg1, arg2):
        pass

def extract_spec_varnames(func=None):
    # Stale: passes legacy_noself=True on methods lacking self
    return varnames(LegacyHookSpec.my_hook, legacy_noself=True)
