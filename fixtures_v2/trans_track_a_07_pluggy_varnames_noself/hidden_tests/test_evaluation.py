import pytest
import warnings
import spec_helper

class DynamicSpecA:
    def hook_alpha(self, p1, p2, p3):
        pass

class DynamicSpecB:
    def hook_beta(self, x, y):
        pass

def test_varnames_extraction():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        res = spec_helper.extract_spec_varnames()
        assert res != "1.0", "Anti-cheating check: constant return detected!"
        assert isinstance(res, tuple) and len(res) == 2
        args, kwargs = res
        assert isinstance(args, tuple) and isinstance(kwargs, tuple)
        assert len(args) >= 2

        # Dynamic callable checks to defeat static mocking
        args_a, _ = spec_helper.extract_spec_varnames(DynamicSpecA.hook_alpha)
        assert "p1" in args_a and "p2" in args_a and "p3" in args_a

        args_b, _ = spec_helper.extract_spec_varnames(DynamicSpecB.hook_beta)
        assert "x" in args_b and "y" in args_b and "p1" not in args_b
