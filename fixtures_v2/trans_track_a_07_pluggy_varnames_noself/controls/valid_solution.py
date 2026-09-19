from pluggy._hooks import varnames

class CleanHookSpec:
    def my_hook(self, arg1, arg2):
        pass

def extract_spec_varnames(func=None):
    # Valid: modern hook spec with proper self parameter
    target = func or CleanHookSpec.my_hook
    return varnames(target, legacy_noself=False)
