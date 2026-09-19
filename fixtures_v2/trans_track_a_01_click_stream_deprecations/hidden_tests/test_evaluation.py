import pytest
import warnings
import stream_helper

def test_stream_retrieval():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        stream = stream_helper.get_io_stream("stdout")
        assert stream is not None
        assert hasattr(stream, "write") or hasattr(stream, "read")
