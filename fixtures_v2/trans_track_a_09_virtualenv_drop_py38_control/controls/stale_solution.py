from virtualenv.create.via_global_ref.builtin.cpython.cpython3 import CPython3Posix

def requires_pyvenv_patch(info) -> bool:
    # Stale: calls removed classmethod
    return CPython3Posix.pyvenv_launch_patch_active(info)
