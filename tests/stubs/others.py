REQUIREMENTS_TXT = b"# local package\n-e .\n\n# external requirements\nclick\nSphinx\ncoverage\nawscli\nflake8\npython-dotenv>=0.5.1\n{% if cookiecutter.python_interpreter != 'python3' %}\n\n# backwards compatibility\npathlib2\n{% endif %}"


def stub_KeyError(arg1, arg2):  # noqa: F841
    raise KeyError()


def stub_unzip(repository_):  # noqa: F841
    return "done"


def stub_unzip_failed(repository_):  # noqa: F841
    return "failed"


