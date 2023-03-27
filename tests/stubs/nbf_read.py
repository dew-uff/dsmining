from tests.stubs.notebook_dict import get_notebook_node


def stub_nbf_read(ofile, nbf):  # noqa: F841
    return get_notebook_node()


def stub_nbf_readOSError(ofile, nbf):  # noqa: F841
    raise OSError()


def stub_nbf_readException(ofile, nbf):  # noqa: F841
    raise ValueError()


def stub_IndentationError(arg1, arg2):  # noqa: F841
    raise IndentationError()
