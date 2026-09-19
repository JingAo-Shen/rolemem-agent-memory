import pytest
import warnings
import sys
import stream_helper

def test_stream_retrieval():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        stream_out = stream_helper.get_io_stream("stdout")
        assert stream_out != "1.0", "Anti-cheating check: constant return detected!"
        assert stream_out is not None
        assert stream_out is getattr(sys.stdout, "buffer", sys.stdout)

        stream_in = stream_helper.get_io_stream("stdin")
        assert stream_in is not None
        assert stream_in is sys.stdin.buffer
