""" Handles database model and connection """
import sys
import subprocess
import src.config.consts as consts

from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import create_engine, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy import ForeignKeyConstraint, DateTime, Interval
from sqlalchemy.orm import sessionmaker, scoped_session, relationship

from src.config.states import *
from src.config.consts import DB_CONNECTION
from src.helpers.h3_utils import version_string_to_list

BigInt = Integer
Base = declarative_base()  # pylint: disable=invalid-name


def one_to_many(table, backref):
    """ Creates a one-to-many relationship """
    return relationship(table, back_populates=backref, lazy="dynamic", viewonly=True, sync_backref=False)


def many_to_one(table, backref):
    """ Creates a many-to-one relationship """
    return relationship(table, back_populates=backref, viewonly=True, sync_backref=False)


def force_encoded_string_output(func):
    """ encode __repr__ """
    if sys.version_info.major < 3:
        def _func(*args, **kwargs):
            """encode __repr__"""
            return func(*args, **kwargs).encode(sys.stdout.encoding or 'utf-8')
        return _func
    else:
        return func


class Query(Base):
    """Query Table"""
    # pylint: disable=invalid-name, too-few-public-methods
    __tablename__ = 'queries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    state = Column(Enum(QUERY_COLLECTED,
                        QUERY_FILTRED,
                        QUERY_SELECTED,
                        QUERY_DISCARDED,
                        name='query_states',
                        validate_strings=True), default=QUERY_COLLECTED)
    repo = Column(String)
    end_cursor = Column(String)
    has_next_page = Column(Boolean)

    primary_language = Column(String)
    disk_usage = Column(String)
    description = Column(String)

    is_mirror = Column(Boolean)

    languages = Column(Integer)
    contributors = Column(Integer)
    commits = Column(Integer)
    pull_requests = Column(Integer)
    branches = Column(Integer)
    watchers = Column(Integer)
    issues = Column(Integer)
    stargazers = Column(Integer)
    forks = Column(Integer)
    tags = Column(Integer)
    releases = Column(Integer)
    git_created_at = Column(DateTime)
    git_pushed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    repositories_objs = one_to_many("Repository", "query_obj")

    @force_encoded_string_output
    def __repr__(self):
        return u"<Query({})>".format(self.repo)


class Repository(Base):
    """Repository Table"""
    # pylint: disable=invalid-name
    __tablename__ = 'repositories'
    __table_args__ = (
        ForeignKeyConstraint(
            ['extraction_id'],
            ['extractions.id']
        ),
        ForeignKeyConstraint(
            ['query_id'],
            ['queries.id']
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(Integer)
    state = Column(Enum(REP_FILTERED,
                        REP_LOADED,
                        REP_FAILED_TO_CLONE,
                        REP_N_EXTRACTED,
                        REP_N_ERROR,
                        REP_PF_EXTRACTED,
                        REP_REQ_FILE_EXTRACTED,
                        REP_FINISHED,
                        REP_UNAVAILABLE_FILES,
                        REP_STOPPED,
                        REP_EMPTY,
                        name='repository_states',
                        validate_strings=True), default=REP_FILTERED)

    domain = Column(String)
    repository = Column(String)
    extraction_id = Column(Integer)
    primary_language = Column(String)
    disk_usage = Column(String)
    is_mirror = Column(Boolean)
    git_created_at = Column(DateTime)
    git_pushed_at = Column(DateTime)

    languages = Column(Integer)
    contributors = Column(Integer)
    commits = Column(Integer)
    pull_requests = Column(Integer)
    branches = Column(Integer)
    watchers = Column(Integer)
    issues = Column(Integer)
    stargazers = Column(Integer)
    forks = Column(Integer)
    description = Column(String)
    tags = Column(Integer)
    releases = Column(Integer)

    hash_dir1 = Column(String)
    hash_dir2 = Column(String)
    commit = Column(String)

    processed = Column(Integer, default=0)
    notebooks_count = Column(Integer)
    python_files_count = Column(Integer)
    setups_count = Column(Integer)
    requirements_count = Column(Integer)
    pipfiles_count = Column(Integer)
    pipfile_locks_count = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    commits_objs = one_to_many("Commit", "repository_obj")
    python_files_objs = one_to_many("PythonFile", "repository_obj")
    python_file_modules_objs = one_to_many("PythonFileModule", "repository_obj")
    python_file_data_ios_objs = one_to_many("PythonFileDataIO", "repository_obj")
    requirement_files_objs = one_to_many("RequirementFile", "repository_obj")

    notebooks_objs = one_to_many("Notebook", "repository_obj")
    cell_objs = one_to_many("Cell", "repository_obj")
    cell_markdown_features_objs = one_to_many("CellMarkdownFeature", "repository_obj")
    cell_modules_objs = one_to_many("CellModule", "repository_obj")
    cell_data_ios_objs = one_to_many("CellDataIO", "repository_obj")

    notebook_markdowns_objs = one_to_many("NotebookMarkdown", "repository_obj")
    modules_objs = one_to_many("Module", "repository_obj")

    extraction_obj = many_to_one("Extraction", "repositories_objs")
    query_obj = many_to_one("Query", "repositories_objs")

    @property
    def path(self):
        """Return notebook path"""
        if self.hash_dir1 and self.hash_dir2:
            return (
                    consts.Path(consts.SELECTED_REPOS_DIR) / "content" /
                    self.hash_dir1 / self.hash_dir2
            )

    @property
    def dir_path(self):
        """Return notebook path"""
        if self.hash_dir1:
            return (
                    consts.Path(consts.SELECTED_REPOS_DIR) / "content" / self.hash_dir1
            )

    @property
    def zip_path(self):
        """Return notebook path"""
        return consts.Path(str(self.path) + ".tar.bz2")

    def compress(self, target=None, return_cmd=False):
        """Compress repository"""
        if not self.path.exists():
            return False
        if target is None:
            target = self.zip_path
        elif isinstance(target, str):
            target = consts.Path(target)
        cmd = [
            "tar", "-cf", str(target),
            "--use-compress-program={}".format(consts.COMPRESSION),
            "-C", str(target.parent), str(self.hash_dir2)
        ]
        if return_cmd:
            return cmd
        return subprocess.call(cmd) == 0

    def uncompress(self, target=None, return_cmd=False):
        """Uncompress repository"""
        if not self.zip_path.exists():
            return False
        target = target or self.zip_path.parent
        cmd = [
            "tar", "-xjf", str(self.zip_path),
            "-C", str(target)
        ]
        if return_cmd:
            return cmd
        return subprocess.call(cmd) == 0

    def get_commit(self, cwd=None):
        """Get commit from uncompressed repository"""
        cwd = cwd or self.path
        if isinstance(cwd, str):
            cwd = consts.Path(cwd)
        if not cwd.exists():
            return None
        try:
            return subprocess.check_output([
                "git", "rev-parse", "HEAD"
            ], cwd=str(cwd)).decode("utf-8").strip()
        except subprocess.CalledProcessError:
            return "Failed"

    @force_encoded_string_output
    def __repr__(self):
        return u"<Repository({}:{})>".format(self.id, self.repository)


class Commit(Base):
    """Commits Table"""
    # pylint: disable=invalid-name
    __tablename__ = 'commits'
    __table_args__ = (
        ForeignKeyConstraint(
            ['repository_id'],
            ['repositories.id']
        ),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    repository_id = Column(Integer)
    type = Column(String)
    hash = Column(String)
    date = Column(DateTime(timezone=True))
    author = Column(String)
    message = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    repository_obj = many_to_one("Repository", "commits_objs")


class Notebook(Base):
    """Notebook Table"""
    # pylint: disable=invalid-name
    __tablename__ = 'notebooks'
    __table_args__ = (
        ForeignKeyConstraint(
            ['repository_id'],
            ['repositories.id']
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    repository_id = Column(Integer)
    state = Column(Enum(NB_LOADED,
                        NB_LOAD_ERROR,
                        NB_LOAD_FORMAT_ERROR,
                        NB_LOAD_SYNTAX_ERROR,
                        NB_LOAD_TIMEOUT,
                        NB_STOPPED,
                        NB_GENERIC_LOAD_ERROR,
                        NB_AGGREGATED,
                        NB_AGGREGATE_ERROR,
                        NB_INVALID,
                        NB_SYNTAX_ERROR,
                        NB_AGGR_MARKDOWN,
                        name='notebook_states',
                        validate_strings=True), default=NB_LOADED)
    name = Column(String)
    nbformat = Column(String)
    kernel = Column(String)
    language = Column(String)
    language_version = Column(String)
    max_execution_count = Column(Integer)
    total_cells = Column(Integer)
    code_cells = Column(Integer)
    code_cells_with_output = Column(Integer)
    markdown_cells = Column(Integer)
    raw_cells = Column(Integer)
    unknown_cell_formats = Column(Integer)
    empty_cells = Column(Integer)
    processed = Column(Integer, default=0)
    skip = Column(Integer, default=0)

    repository_obj = many_to_one("Repository", "notebooks_objs")
    cell_objs = one_to_many("Cell", "notebook_obj")
    cell_markdown_features_objs = one_to_many("CellMarkdownFeature", "notebook_obj")
    cell_modules_objs = one_to_many("CellModule", "notebook_obj")
    cell_data_ios_objs = one_to_many("CellDataIO", "notebook_obj")
    notebook_markdowns_objs = one_to_many("NotebookMarkdown", "notebook_obj")
    modules_objs = one_to_many("Module", "notebook_obj")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    @property
    def path(self):
        """Return notebook path"""
        return self.repository_obj.path / self.name

    @property
    def py_version(self):
        """Return python version of notebook"""
        note_version = self.language_version or "0"
        if note_version == "unknown":
            note_version = ".".join(map(str, sys.version_info[:3]))
        return version_string_to_list(note_version)

    @property
    def compatible_version(self):
        """Check if the running python version is compatible to the notebook"""
        note_version = self.py_version
        py_version = sys.version_info
        if note_version[0] != py_version[0]:
            return False
        if len(note_version) > 1 and note_version[1] > py_version[1]:
            return False
        return True

    @force_encoded_string_output
    def __repr__(self):
        return u"<Notebook({0.repository_id}/{0.id})>".format(self)


class Cell(Base):
    """ Cell Table """
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'cells'
    __table_args__ = (
        ForeignKeyConstraint(
            ['notebook_id'],
            ['notebooks.id']
        ),
        ForeignKeyConstraint(
            ['repository_id'],
            ['repositories.id']
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    repository_id = Column(Integer)
    notebook_id = Column(Integer)
    state = Column(Enum(CELL_LOADED, CELL_UNKNOWN_VERSION, CELL_SYNTAX_ERROR,
                        CELL_PROCESSED, CELL_PROCESS_ERROR, CELL_PROCESS_TIMEOUT,
                        name='cell_states',
                        validate_strings=True), default=CELL_LOADED)
    index = Column(Integer)
    cell_type = Column(String)
    execution_count = Column(String)
    lines = Column(Integer)
    output_formats = Column(String)
    source = Column(String)
    python = Column(Boolean)
    processed = Column(Integer, default=0)
    skip = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    repository_obj = many_to_one("Repository", "cell_objs")
    notebook_obj = many_to_one("Notebook", "cell_objs")
    cell_markdown_features_objs = one_to_many("CellMarkdownFeature", "cell_obj")
    cell_modules_objs = one_to_many("CellModule", "cell_obj")
    cell_data_ios_objs = one_to_many("CellDataIO", "cell_obj")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<Cell({0.repository_id}/{0.notebook_id}/{0.id}[{0.index}])>"
        ).format(self)


class PythonFile(Base):
    """Pyhton File Table"""
    # pylint: disable=invalid-name
    __tablename__ = 'python_files'
    __table_args__ = (
        ForeignKeyConstraint(
            ['repository_id'],
            ['repositories.id']
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    repository_id = Column(Integer)
    state = Column(Enum(PF_LOADED, PF_EMPTY, PF_L_ERROR,
                        PF_PROCESSED, PF_PROCESS_ERROR, PF_PROCESS_TIMEOUT,
                        PF_SYNTAX_ERROR, PF_AGGREGATED,
                        name='python_files_states',
                        validate_strings=True), default=PF_LOADED)
    name = Column(String)
    source = Column(String)
    total_lines = Column(Integer)
    processed = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    repository_obj = many_to_one("Repository", "python_files_objs")

    python_file_modules_objs = one_to_many("PythonFileModule", "python_file_obj")
    python_file_data_ios_objs = one_to_many("PythonFileDataIO", "python_file_obj")

    modules_objs = one_to_many("Module", "python_file_obj")

    @property
    def path(self):
        """Return python file path"""
        return self.repository_obj.path / self.name

    @force_encoded_string_output
    def __repr__(self):
        return u"<PythonFile({0.repository_id}/{0.id}:{0.name})>".format(
            self
        )


class RequirementFile(Base):
    """Requirement File Table"""
    # pylint: disable=invalid-name
    __tablename__ = 'requirement_files'
    __table_args__ = (
        ForeignKeyConstraint(
            ['repository_id'],
            ['repositories.id']
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    repository_id = Column(Integer)
    state = Column(Enum(REQ_FILE_LOADED, REQ_FILE_L_ERROR, REQ_FILE_EMPTY,
                        name='requirement_file_states',
                        validate_strings=True), default=REQ_FILE_LOADED)
    name = Column(String)
    reqformat = Column(String)  # setup.py, requirements.py, Pipfile, Pipfile.lock
    content = Column(String)
    processed = Column(Integer, default=0)
    skip = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    repository_obj = many_to_one("Repository", "requirement_files_objs")

    @property
    def path(self):
        """Return requirement file path"""
        return self.repository_obj.path / self.name

    @force_encoded_string_output
    def __repr__(self):
        return u"<RequirementFile({0.repository_id}/{0.id}:{0.name})>".format(
            self
        )


class CellMarkdownFeature(Base):
    """Cell Markdown Features Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'cell_markdown_features'
    __table_args__ = (
        ForeignKeyConstraint(
            ['cell_id'],
            ['cells.id']
        ),
        ForeignKeyConstraint(
            ['notebook_id'],
            ['notebooks.id']
        ),
        ForeignKeyConstraint(
            ['repository_id'],
            ['repositories.id']
        ),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    repository_id = Column(Integer)
    notebook_id = Column(Integer)
    cell_id = Column(Integer)
    index = Column(Integer)

    language = Column(String)
    using_stopwords = Column(Boolean)
    len = Column(Integer)
    lines = Column(Integer)
    meaningful_lines = Column(Integer)
    words = Column(Integer)
    meaningful_words = Column(Integer)
    stopwords = Column(Integer)
    meaningful_stopwords = Column(Integer)

    header = Column(Integer)
    header_len = Column(Integer)
    header_lines = Column(Integer)
    header_words = Column(Integer)
    header_stopwords = Column(Integer)

    h1 = Column(Integer)
    h1_len = Column(Integer)
    h1_lines = Column(Integer)
    h1_words = Column(Integer)
    h1_stopwords = Column(Integer)

    h2 = Column(Integer)
    h2_len = Column(Integer)
    h2_lines = Column(Integer)
    h2_words = Column(Integer)
    h2_stopwords = Column(Integer)

    h3 = Column(Integer)
    h3_len = Column(Integer)
    h3_lines = Column(Integer)
    h3_words = Column(Integer)
    h3_stopwords = Column(Integer)

    h4 = Column(Integer)
    h4_len = Column(Integer)
    h4_lines = Column(Integer)
    h4_words = Column(Integer)
    h4_stopwords = Column(Integer)

    h5 = Column(Integer)
    h5_len = Column(Integer)
    h5_lines = Column(Integer)
    h5_words = Column(Integer)
    h5_stopwords = Column(Integer)

    h6 = Column(Integer)
    h6_len = Column(Integer)
    h6_lines = Column(Integer)
    h6_words = Column(Integer)
    h6_stopwords = Column(Integer)

    hrule = Column(Integer)

    list = Column(Integer)
    list_len = Column(Integer)
    list_lines = Column(Integer)
    list_items = Column(Integer)
    list_words = Column(Integer)
    list_stopwords = Column(Integer)

    table = Column(Integer)
    table_len = Column(Integer)
    table_lines = Column(Integer)
    table_rows = Column(Integer)
    table_cells = Column(Integer)
    table_words = Column(Integer)
    table_stopwords = Column(Integer)

    p = Column(Integer)
    p_len = Column(Integer)
    p_lines = Column(Integer)
    p_words = Column(Integer)
    p_stopwords = Column(Integer)

    quote = Column(Integer)
    quote_len = Column(Integer)
    quote_lines = Column(Integer)
    quote_words = Column(Integer)
    quote_stopwords = Column(Integer)

    code = Column(Integer)
    code_len = Column(Integer)
    code_lines = Column(Integer)
    code_words = Column(Integer)
    code_stopwords = Column(Integer)

    image = Column(Integer)
    image_len = Column(Integer)
    image_words = Column(Integer)
    image_stopwords = Column(Integer)

    link = Column(Integer)
    link_len = Column(Integer)
    link_words = Column(Integer)
    link_stopwords = Column(Integer)

    autolink = Column(Integer)
    autolink_len = Column(Integer)
    autolink_words = Column(Integer)
    autolink_stopwords = Column(Integer)

    codespan = Column(Integer)
    codespan_len = Column(Integer)
    codespan_words = Column(Integer)
    codespan_stopwords = Column(Integer)

    emphasis = Column(Integer)
    emphasis_len = Column(Integer)
    emphasis_words = Column(Integer)
    emphasis_stopwords = Column(Integer)

    double_emphasis = Column(Integer)
    double_emphasis_len = Column(Integer)
    double_emphasis_words = Column(Integer)
    double_emphasis_stopwords = Column(Integer)

    strikethrough = Column(Integer)
    strikethrough_len = Column(Integer)
    strikethrough_words = Column(Integer)
    strikethrough_stopwords = Column(Integer)

    html = Column(Integer)
    html_len = Column(Integer)
    html_lines = Column(Integer)

    math = Column(Integer)
    math_len = Column(Integer)
    math_words = Column(Integer)
    math_stopwords = Column(Integer)

    block_math = Column(Integer)
    block_math_len = Column(Integer)
    block_math_lines = Column(Integer)
    block_math_words = Column(Integer)
    block_math_stopwords = Column(Integer)

    latex = Column(Integer)
    latex_len = Column(Integer)
    latex_lines = Column(Integer)
    latex_words = Column(Integer)
    latex_stopwords = Column(Integer)
    skip = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    cell_obj = many_to_one("Cell", "cell_markdown_features_objs")
    notebook_obj = many_to_one("Notebook", "cell_markdown_features_objs")
    repository_obj = many_to_one("Repository", "cell_markdown_features_objs")

    @force_encoded_string_output
    def __repr__(self):
        cell = self.cell_obj
        notebook = cell.notebook_obj
        return (
            u"<CellMarkdownFeature({2.repository_id}/{2.id}/{1.id}[{1.index}]/{0.id})>"
            .format(self, cell, notebook)
        )


class CellModule(Base):
    """Cell Modules Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'cell_modules'
    __table_args__ = (
        ForeignKeyConstraint(
            ['cell_id'],
            ['cells.id']
        ),
        ForeignKeyConstraint(
            ['notebook_id'],
            ['notebooks.id']
        ),
        ForeignKeyConstraint(
            ['repository_id'],
            ['repositories.id']
        ),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    repository_id = Column(Integer)
    notebook_id = Column(Integer)
    cell_id = Column(Integer)
    index = Column(Integer)

    line = Column(Integer)
    import_type = Column(String)
    module_name = Column(String)
    local = Column(Boolean)
    skip = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    cell_obj = many_to_one("Cell", "cell_modules_objs")
    notebook_obj = many_to_one("Notebook", "cell_modules_objs")
    repository_obj = many_to_one("Repository", "cell_modules_objs")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<Module({0.repository_id}/{0.notebook_id}/"
            u"{0.cell_id}[{0.index}]/{0.id}:{0.import_type})>"
        ).format(self)


class CellDataIO(Base):
    """Cell Data IO Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'cell_data_ios'
    __table_args__ = (
        ForeignKeyConstraint(
            ['cell_id'],
            ['cells.id']
        ),
        ForeignKeyConstraint(
            ['notebook_id'],
            ['notebooks.id']
        ),
        ForeignKeyConstraint(
            ['repository_id'],
            ['repositories.id']
        ),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    repository_id = Column(Integer)
    notebook_id = Column(Integer)
    cell_id = Column(Integer)
    index = Column(Integer)

    line = Column(Integer)
    type = Column(String)
    caller = Column(String)
    function_name = Column(String)
    function_type = Column(String)
    source = Column(String)
    source_type = Column(String)
    skip = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    cell_obj = many_to_one("Cell", "cell_data_ios_objs")
    notebook_obj = many_to_one("Notebook", "cell_data_ios_objs")
    repository_obj = many_to_one("Repository", "cell_data_ios_objs")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<Module({0.repository_id}/{0.notebook_id}/"
            u"{0.cell_id}[{0.index}]/{0.id}:{0.function_name})>"
        ).format(self)


class PythonFileModule(Base):
    """Python Modules Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'python_file_modules'
    __table_args__ = (
        ForeignKeyConstraint(
            ['python_file_id'],
            ['python_files.id']
        ),
        ForeignKeyConstraint(
            ['repository_id'],
            ['repositories.id']
        ),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    repository_id = Column(Integer)
    python_file_id = Column(Integer)

    line = Column(Integer)
    import_type = Column(String)
    module_name = Column(String)
    local = Column(Boolean)
    skip = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    python_file_obj = many_to_one("PythonFile", "python_file_modules_objs")
    repository_obj = many_to_one("Repository", "python_file_modules_objs")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<Module({0.repository_id}/{0.python_file_id}/"
            u"{0.id}:{0.import_type})>"
        ).format(self)


class PythonFileDataIO(Base):
    """Python Data Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'python_file_data_ios'
    __table_args__ = (
        ForeignKeyConstraint(
            ['python_file_id'],
            ['python_files.id']
        ),
        ForeignKeyConstraint(
            ['repository_id'],
            ['repositories.id']
        ),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    repository_id = Column(Integer)
    python_file_id = Column(Integer)

    line = Column(Integer)
    type = Column(String)
    caller = Column(String)
    function_name = Column(String)
    function_type = Column(String)
    source = Column(String)
    source_type = Column(String)
    skip = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    python_file_obj = many_to_one("PythonFile", "python_file_data_ios_objs")
    repository_obj = many_to_one("Repository", "python_file_data_ios_objs")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<Data({0.repository_id}/{0.python_file_id}/"
            u"{0.id}:{0.function_name})>"
        ).format(self)


class Extraction(Base):
    """Repository Files Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'extractions'

    id = Column(Integer, autoincrement=True, primary_key=True)
    state = Column(Enum(EXTRACTED_SUCCESS,
                        EXTRACTED_ERROR,
                        name='extraction_states',
                        validate_strings=True)
                   )

    start = Column(DateTime)
    end = Column(DateTime)
    runtime = Column(Interval)
    repositores = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    repositories_objs = one_to_many("Repository", "extraction_obj")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<Extraction({0.id})>"
        ).format(self)


class NotebookMarkdown(Base):
    """Notebook Markdown Features Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'notebook_markdowns'
    __table_args__ = (
        ForeignKeyConstraint(
            ['notebook_id'],
            ['notebooks.id']
        ),
        ForeignKeyConstraint(
            ['repository_id'],
            ['repositories.id']
        ),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    repository_id = Column(Integer)
    notebook_id = Column(Integer)

    cell_count = Column(Integer)
    main_language = Column(String)
    languages = Column(String)
    languages_counts = Column(String)

    using_stopwords = Column(Integer)

    len = Column(Integer)
    lines = Column(Integer)
    meaningful_lines = Column(Integer)
    words = Column(Integer)
    meaningful_words = Column(Integer)
    stopwords = Column(Integer)
    meaningful_stopwords = Column(Integer)

    header = Column(Integer)
    header_len = Column(Integer)
    header_lines = Column(Integer)
    header_words = Column(Integer)
    header_stopwords = Column(Integer)

    h1 = Column(Integer)
    h1_len = Column(Integer)
    h1_lines = Column(Integer)
    h1_words = Column(Integer)
    h1_stopwords = Column(Integer)

    h2 = Column(Integer)
    h2_len = Column(Integer)
    h2_lines = Column(Integer)
    h2_words = Column(Integer)
    h2_stopwords = Column(Integer)

    h3 = Column(Integer)
    h3_len = Column(Integer)
    h3_lines = Column(Integer)
    h3_words = Column(Integer)
    h3_stopwords = Column(Integer)

    h4 = Column(Integer)
    h4_len = Column(Integer)
    h4_lines = Column(Integer)
    h4_words = Column(Integer)
    h4_stopwords = Column(Integer)

    h5 = Column(Integer)
    h5_len = Column(Integer)
    h5_lines = Column(Integer)
    h5_words = Column(Integer)
    h5_stopwords = Column(Integer)

    h6 = Column(Integer)
    h6_len = Column(Integer)
    h6_lines = Column(Integer)
    h6_words = Column(Integer)
    h6_stopwords = Column(Integer)

    hrule = Column(Integer)

    list = Column(Integer)
    list_len = Column(Integer)
    list_lines = Column(Integer)
    list_items = Column(Integer)
    list_words = Column(Integer)
    list_stopwords = Column(Integer)

    table = Column(Integer)
    table_len = Column(Integer)
    table_lines = Column(Integer)
    table_rows = Column(Integer)
    table_cells = Column(Integer)
    table_words = Column(Integer)
    table_stopwords = Column(Integer)

    p = Column(Integer)
    p_len = Column(Integer)
    p_lines = Column(Integer)
    p_words = Column(Integer)
    p_stopwords = Column(Integer)

    quote = Column(Integer)
    quote_len = Column(Integer)
    quote_lines = Column(Integer)
    quote_words = Column(Integer)
    quote_stopwords = Column(Integer)

    code = Column(Integer)
    code_len = Column(Integer)
    code_lines = Column(Integer)
    code_words = Column(Integer)
    code_stopwords = Column(Integer)

    image = Column(Integer)
    image_len = Column(Integer)
    image_words = Column(Integer)
    image_stopwords = Column(Integer)

    link = Column(Integer)
    link_len = Column(Integer)
    link_words = Column(Integer)
    link_stopwords = Column(Integer)

    autolink = Column(Integer)
    autolink_len = Column(Integer)
    autolink_words = Column(Integer)
    autolink_stopwords = Column(Integer)

    codespan = Column(Integer)
    codespan_len = Column(Integer)
    codespan_words = Column(Integer)
    codespan_stopwords = Column(Integer)

    emphasis = Column(Integer)
    emphasis_len = Column(Integer)
    emphasis_words = Column(Integer)
    emphasis_stopwords = Column(Integer)

    double_emphasis = Column(Integer)
    double_emphasis_len = Column(Integer)
    double_emphasis_words = Column(Integer)
    double_emphasis_stopwords = Column(Integer)

    strikethrough = Column(Integer)
    strikethrough_len = Column(Integer)
    strikethrough_words = Column(Integer)
    strikethrough_stopwords = Column(Integer)

    html = Column(Integer)
    html_len = Column(Integer)
    html_lines = Column(Integer)

    math = Column(Integer)
    math_len = Column(Integer)
    math_words = Column(Integer)
    math_stopwords = Column(Integer)

    block_math = Column(Integer)
    block_math_len = Column(Integer)
    block_math_lines = Column(Integer)
    block_math_words = Column(Integer)
    block_math_stopwords = Column(Integer)

    latex = Column(Integer)
    latex_len = Column(Integer)
    latex_lines = Column(Integer)
    latex_words = Column(Integer)
    latex_stopwords = Column(Integer)
    skip = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    notebook_obj = many_to_one("Notebook", "notebook_markdowns_objs")
    repository_obj = many_to_one("Repository", "notebook_markdowns_objs")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<NotebookMarkdown({0.repository_id}/{0.notebook_id}/{0.id})>"
            .format(self)
        )


class Module(Base):
    """Modules Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'modules'
    __table_args__ = (
        ForeignKeyConstraint(
            ['notebook_id'],
            ['notebooks.id']
        ),
        ForeignKeyConstraint(
            ['python_file_id'],
            ['python_files.id']
        ),
        ForeignKeyConstraint(
            ['repository_id'],
            ['repositories.id']
        ),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    repository_id = Column(Integer)
    type = Column(String)
    notebook_id = Column(Integer)
    python_file_id = Column(Integer)

    index = Column(String)
    index_count = Column(Integer)

    any_any = Column(String)
    any_any_count = Column(Integer)
    local_any = Column(String)
    local_any_count = Column(Integer)
    external_any = Column(String)
    external_any_count = Column(Integer)

    any_import_from = Column(String)
    any_import_from_count = Column(Integer)
    local_import_from = Column(String)
    local_import_from_count = Column(Integer)
    external_import_from = Column(String)
    external_import_from_count = Column(Integer)

    any_import = Column(String)
    any_import_count = Column(Integer)
    local_import = Column(String)
    local_import_count = Column(Integer)
    external_import = Column(String)
    external_import_count = Column(Integer)

    any_load_ext = Column(String)
    any_load_ext_count = Column(Integer)
    local_load_ext = Column(String)
    local_load_ext_count = Column(Integer)
    external_load_ext = Column(String)
    external_load_ext_count = Column(Integer)

    others = Column(String)

    skip = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    notebook_obj = many_to_one("Notebook", "modules_objs")
    python_file_obj = many_to_one("PythonFile", "modules_objs")
    repository_obj = many_to_one("Repository", "modules_objs")

    @force_encoded_string_output
    def __repr__(self):
        if self.type == 'notebook':
            return (
                u"<Module({0.repository_id}/{0.notebook_id}/{0.id})>"
            ).format(self)
        elif self.type == 'python_file':
            return (
                u"<Module({0.repository_id}/{0.python_file_id}/{0.id})>"
            ).format(self)


@contextmanager
def connect(echo=False):
    """Creates a context with an open SQLAlchemy session."""
    engine = create_engine(DB_CONNECTION, convert_unicode=True, echo=echo)
    Base.metadata.create_all(engine)
    connection = engine.connect()
    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))
    yield db_session
    db_session.close()  # pylint: disable=E1101
    connection.close()
