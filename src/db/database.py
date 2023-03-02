"""Handles database model and connection"""
import sys
import src.config as config
import subprocess

from src.config import DB_CONNECTION
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Interval
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
from sqlalchemy import ForeignKeyConstraint
from src.helpers.h1_utils import version_string_to_list

BigInt = Integer
Base = declarative_base()  # pylint: disable=invalid-name


def one_to_many(table, backref):
    """Create one to many relationship"""
    return relationship(table, back_populates=backref, lazy="dynamic", viewonly=True, sync_backref=False)


def many_to_one(table, backref):
    """Create many to one relationship"""
    return relationship(table, back_populates=backref, viewonly=True, sync_backref=False)


def force_encoded_string_output(func):
    """encode __repr__"""
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
    name = Column(String)
    query = Column(String)
    first_date = Column(DateTime)
    last_date = Column(DateTime)
    delta = Column(Interval)
    count = Column(Integer)

    @force_encoded_string_output
    def __repr__(self):
        return u"<Query({})>".format(self.query)


class Repository(Base):
    """Repository Table"""
    # pylint: disable=invalid-name
    __tablename__ = 'repositories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String)
    repository = Column(String)
    hash_dir1 = Column(String)
    hash_dir2 = Column(String)
    commit = Column(String)
    processed = Column(Integer, default=0)

    commits_objs = one_to_many("Commit", "repository_obj")

    notebooks_count = Column(Integer)
    python_files_count = Column(Integer)
    setups_count = Column(Integer)
    requirements_count = Column(Integer)
    pipfiles_count = Column(Integer)
    pipfile_locks_count = Column(Integer)


    python_files_objs = one_to_many("PythonFile", "repository_obj")
    python_analyzes_objs = one_to_many("PythonAnalysis", "repository_obj")
    python_file_modules_objs = one_to_many("PythonFileModule", "repository_obj")
    python_file_features_objs = one_to_many("PythonFileFeature", "repository_obj")
    python_file_names_objs = one_to_many("PythonFileName", "repository_obj")


    requirement_files_objs = one_to_many("RequirementFile", "repository_obj")

    notebooks_objs = one_to_many("Notebook", "repository_obj")
    cell_objs = one_to_many("Cell", "repository_obj")
    markdown_features_objs = one_to_many("MarkdownFeature", "repository_obj")
    code_analyses_objs = one_to_many("CodeAnalysis", "repository_obj")
    cell_modules_objs = one_to_many("CellModule", "repository_obj")
    cell_features_objs = one_to_many("CellFeature", "repository_obj")
    cell_names_objs = one_to_many("CellName", "repository_obj")

    files_objs = one_to_many("RepositoryFile", "repository_obj")

    notebook_markdowns_objs = one_to_many("NotebookMarkdown", "repository_obj")
    asts_objs = one_to_many("AST", "repository_obj")
    modules_objs = one_to_many("Module", "repository_obj")
    features_objs = one_to_many("Feature", "repository_obj")
    names_objs = one_to_many("Name", "repository_obj")

    @property
    def path(self):
        """Return notebook path"""
        return (
                config.Path(config.SELECTED_REPOS_DIR) / "content" /
                self.hash_dir1 / self.hash_dir2
        )

    @property
    def zip_path(self):
        """Return notebook path"""
        return config.Path(str(self.path) + ".tar.bz2")

    def compress(self, target=None, return_cmd=False):
        """Compress repository"""
        if not self.path.exists():
            return False
        if target is None:
            target = self.zip_path
        elif isinstance(target, str):
            target = config.Path(target)
        cmd = [
            "tar", "-cf", str(target),
            "--use-compress-program={}".format(config.COMPRESSION),
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
            cwd = config.Path(cwd)
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
    hash = Column(String)
    date = Column(DateTime(timezone=True))
    author = Column(String)
    message = Column(String)

    repository_obj = many_to_one("Repository", "commits_objs")


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
    name = Column(String)
    source = Column(String)
    total_lines = Column(Integer)
    processed = Column(Integer, default=0)


    repository_obj = many_to_one("Repository", "python_files_objs")
    python_analyzes_objs = one_to_many("PythonAnalysis", "python_file_obj")

    python_file_modules_objs = one_to_many("PythonFileModule", "python_file_obj")
    python_file_features_objs = one_to_many("PythonFileFeature", "python_file_obj")
    python_file_names_objs = one_to_many("PythonFileName", "python_file_obj")

    asts_objs = one_to_many("AST", "python_file_obj")
    modules_objs = one_to_many("Module", "python_file_obj")
    features_objs = one_to_many("Feature", "python_file_obj")
    names_objs = one_to_many("Name", "python_file_obj")

    @property
    def path(self):
        """Return python file path"""
        return self.repository_obj.path / self.name

    @force_encoded_string_output
    def __repr__(self):
        return u"<PythonFile({0.repository_id}/{0.id}:{0.name})>".format(
            self
        )


class PythonAnalysis(Base):
    """Python Analysis Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'python_analyzes'
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

    # Custom
    import_star = Column(Integer)

    functions_with_decorators = Column(Integer)
    classes_with_decorators = Column(Integer)
    classes_with_bases = Column(Integer)

    delname = Column(Integer)
    delattr = Column(Integer)
    delitem = Column(Integer)
    assignname = Column(Integer)
    assignattr = Column(Integer)
    assignitem = Column(Integer)

    ipython = Column(Integer)
    ipython_superset = Column(Integer)

    # Scope
    class_importfrom = Column(Integer)
    global_importfrom = Column(Integer)
    nonlocal_importfrom = Column(Integer)
    local_importfrom = Column(Integer)
    total_importfrom = Column(Integer)

    class_import = Column(Integer)
    global_import = Column(Integer)
    nonlocal_import = Column(Integer)
    local_import = Column(Integer)
    total_import = Column(Integer)

    class_assign = Column(Integer)
    global_assign = Column(Integer)
    nonlocal_assign = Column(Integer)
    local_assign = Column(Integer)
    total_assign = Column(Integer)

    class_delete = Column(Integer)
    global_delete = Column(Integer)
    nonlocal_delete = Column(Integer)
    local_delete = Column(Integer)
    total_delete = Column(Integer)

    class_functiondef = Column(Integer)
    global_functiondef = Column(Integer)
    nonlocal_functiondef = Column(Integer)
    local_functiondef = Column(Integer)
    total_functiondef = Column(Integer)

    class_classdef = Column(Integer)
    global_classdef = Column(Integer)
    nonlocal_classdef = Column(Integer)
    local_classdef = Column(Integer)
    total_classdef = Column(Integer)

    # AST
    # mod
    ast_module = Column(Integer)  # max
    ast_interactive = Column(Integer)  # zero
    ast_expression = Column(Integer)  # zero
    ast_suite = Column(Integer)  # zero

    #stmt
    ast_statements = Column(Integer)

    ast_functiondef = Column(Integer)
    ast_asyncfunctiondef = Column(Integer)
    ast_classdef = Column(Integer)
    ast_return = Column(Integer)

    ast_delete = Column(Integer)
    ast_assign = Column(Integer)
    ast_augassign = Column(Integer)
    ast_annassign = Column(Integer)

    ast_print = Column(Integer)

    ast_for = Column(Integer)
    ast_asyncfor = Column(Integer)
    ast_while = Column(Integer)
    ast_if = Column(Integer)
    ast_with = Column(Integer)
    ast_asyncwith = Column(Integer)

    ast_raise = Column(Integer)
    ast_try = Column(Integer)
    ast_tryexcept = Column(Integer)
    ast_tryfinally = Column(Integer)
    ast_assert = Column(Integer)

    ast_import = Column(Integer)
    ast_importfrom = Column(Integer)
    ast_exec = Column(Integer)
    ast_global = Column(Integer)
    ast_nonlocal = Column(Integer)
    ast_expr = Column(Integer)
    ast_pass = Column(Integer)
    ast_break = Column(Integer)
    ast_continue = Column(Integer)

    # expr
    ast_expressions = Column(Integer)

    ast_boolop = Column(Integer)
    ast_binop = Column(Integer)
    ast_unaryop = Column(Integer)
    ast_lambda = Column(Integer)
    ast_ifexp = Column(Integer)
    ast_dict = Column(Integer)
    ast_set = Column(Integer)
    ast_listcomp = Column(Integer)
    ast_setcomp = Column(Integer)
    ast_dictcomp = Column(Integer)
    ast_generatorexp = Column(Integer)

    ast_await = Column(Integer)
    ast_yield = Column(Integer)
    ast_yieldfrom = Column(Integer)

    ast_compare = Column(Integer)
    ast_call = Column(Integer)
    ast_num = Column(Integer)
    ast_str = Column(Integer)
    ast_formattedvalue = Column(Integer)
    ast_joinedstr = Column(Integer)
    ast_bytes = Column(Integer)
    ast_nameconstant = Column(Integer)
    ast_ellipsis = Column(Integer)
    ast_constant = Column(Integer)

    ast_attribute = Column(Integer)
    ast_subscript = Column(Integer)
    ast_starred = Column(Integer)
    ast_name = Column(Integer)
    ast_list = Column(Integer)
    ast_tuple = Column(Integer)

    # expr_contex
    ast_load = Column(Integer)
    ast_store = Column(Integer)
    ast_del = Column(Integer)
    ast_augload = Column(Integer)
    ast_augstore = Column(Integer)
    ast_param = Column(Integer)

    # slice
    ast_slice = Column(Integer)
    ast_index = Column(Integer)

    # boolop
    ast_and = Column(Integer)
    ast_or = Column(Integer)

    # operator
    ast_add = Column(Integer)
    ast_sub = Column(Integer)
    ast_mult = Column(Integer)
    ast_matmult = Column(Integer)
    ast_div = Column(Integer)
    ast_mod = Column(Integer)
    ast_pow = Column(Integer)
    ast_lshift = Column(Integer)
    ast_rshift = Column(Integer)
    ast_bitor = Column(Integer)
    ast_bitxor = Column(Integer)
    ast_bitand = Column(Integer)
    ast_floordiv = Column(Integer)

    # unaryop
    ast_invert = Column(Integer)
    ast_not = Column(Integer)
    ast_uadd = Column(Integer)
    ast_usub = Column(Integer)

    # cmpop
    ast_eq = Column(Integer)
    ast_noteq = Column(Integer)
    ast_lt = Column(Integer)
    ast_lte = Column(Integer)
    ast_gt = Column(Integer)
    ast_gte = Column(Integer)
    ast_is = Column(Integer)
    ast_isnot = Column(Integer)
    ast_in = Column(Integer)
    ast_notin = Column(Integer)

    # others
    ast_comprehension = Column(Integer)
    ast_excepthandler = Column(Integer)
    ast_arguments = Column(Integer)
    ast_arg = Column(Integer)
    ast_keyword = Column(Integer)
    ast_alias = Column(Integer)
    ast_withitem = Column(Integer)

    # New nodes?
    ast_others = Column(String)

    processed = Column(Integer)
    skip = Column(Integer, default=0)

    ast_extslice = Column(Integer, default=0)
    ast_repr = Column(Integer, default=0)

    python_file_obj = many_to_one("PythonFile", "python_analyzes_objs")
    repository_obj = many_to_one("Repository", "python_analyzes_objs")

    python_file_modules_objs = one_to_many("PythonFileModule", "analysis_obj")
    python_file_features_objs = one_to_many("PythonFileFeature", "analysis_obj")
    python_file_names_objs = one_to_many("PythonFileName", "analysis_obj")


    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<PythonAnalysis({0.repository_id}/{0.python_file_id}/{0.id})>"
            .format(self)
        )


class PythonFileModule(Base):
    """Python Modules Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'python_file_modules'
    __table_args__ = (
        ForeignKeyConstraint(
            ['analysis_id'],
            ['python_analyzes.id']
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
    python_file_id = Column(Integer)
    analysis_id = Column(Integer)

    line = Column(Integer)
    import_type = Column(String)
    module_name = Column(String)
    local = Column(Boolean)
    skip = Column(Integer, default=0)

    python_file_obj = many_to_one("PythonFile", "python_file_modules_objs")
    repository_obj = many_to_one("Repository", "python_file_modules_objs")
    analysis_obj = many_to_one("PythonAnalysis", "python_file_modules_objs")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<Module({0.repository_id}/{0.python_file_id}/"
            u"{0.analysis_id}/{0.id}:{0.import_type})>"
        ).format(self)


class PythonFileFeature(Base):
    """Python File Features Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'python_file_features'
    __table_args__ = (
        ForeignKeyConstraint(
            ['analysis_id'],
            ['python_analyzes.id']
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
    python_file_id = Column(Integer)
    analysis_id = Column(Integer)

    line = Column(Integer)
    column = Column(Integer)
    feature_name = Column(String)
    feature_value = Column(String)
    skip = Column(Integer, default=0)

    python_file_obj = many_to_one("PythonFile", "python_file_features_objs")
    repository_obj = many_to_one("Repository", "python_file_features_objs")
    analysis_obj = many_to_one("PythonAnalysis", "python_file_features_objs")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<Feature({0.repository_id}/{0.notebook_id}/"
            u"{0.analysis_id}/{0.id}:{0.feature_name})>"
        ).format(self)


class PythonFileName(Base):
    """Pyhton File Names Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'python_file_names'
    __table_args__ = (
        ForeignKeyConstraint(
            ['analysis_id'],
            ['python_analyzes.id']
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
    python_file_id = Column(Integer)
    analysis_id = Column(Integer)

    scope = Column(String)
    context = Column(String)
    name = Column(String)
    count = Column(Integer)

    skip = Column(Integer, default=0)


    python_file_obj = many_to_one("PythonFile", "python_file_names_objs")
    repository_obj = many_to_one("Repository", "python_file_names_objs")
    analysis_obj = many_to_one("PythonAnalysis", "python_file_names_objs")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<Module({0.repository_id}/{0.python_file_id}/"
            u"{0.analysis_id}/{0.id}:{0.name})>"
        ).format(self)


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
    markdown_features_objs = one_to_many("MarkdownFeature", "notebook_obj")
    code_analyses_objs = one_to_many("CodeAnalysis", "notebook_obj")
    cell_modules_objs = one_to_many("CellModule", "notebook_obj")
    cell_features_objs = one_to_many("CellFeature", "notebook_obj")
    cell_names_objs = one_to_many("CellName", "notebook_obj")
    notebook_markdowns_objs = one_to_many("NotebookMarkdown", "notebook_obj")
    asts_objs = one_to_many("AST", "notebook_obj")
    modules_objs = one_to_many("Module", "notebook_obj")
    features_objs = one_to_many("Feature", "notebook_obj")
    names_objs = one_to_many("Name", "notebook_obj")


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
    """Cell Table"""
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
    index = Column(Integer)
    cell_type = Column(String)
    execution_count = Column(String)
    lines = Column(Integer)
    output_formats = Column(String)
    source = Column(String)
    python = Column(Boolean)
    processed = Column(Integer, default=0)
    skip = Column(Integer, default=0)

    repository_obj = many_to_one("Repository", "cell_objs")
    notebook_obj = many_to_one("Notebook", "cell_objs")
    markdown_features_objs = one_to_many("MarkdownFeature", "cell_obj")
    code_analyses_objs = one_to_many("CodeAnalysis", "cell_obj")
    cell_modules_objs = one_to_many("CellModule", "cell_obj")
    cell_features_objs = one_to_many("CellFeature", "cell_obj")
    cell_names_objs = one_to_many("CellName", "cell_obj")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<Cell({0.repository_id}/{0.notebook_id}/{0.id}[{0.index}])>"
        ).format(self)


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
    name = Column(String)
    reqformat = Column(String) # setup.py, requirements.py, Pipfile, Pipfile.lock
    content = Column(String)
    processed = Column(Integer, default=0)
    skip = Column(Integer, default=0)

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


class MarkdownFeature(Base):
    """Markdown Features Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'markdown_features'
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

    cell_obj = many_to_one("Cell", "markdown_features_objs")
    notebook_obj = many_to_one("Notebook", "markdown_features_objs")
    repository_obj = many_to_one("Repository", "markdown_features_objs")

    @force_encoded_string_output
    def __repr__(self):
        cell = self.cell_obj
        notebook = cell.notebook_obj
        return (
            u"<MarkdownFeature({2.repository_id}/{2.id}/{1.id}[{1.index}]/{0.id})>"
            .format(self, cell, notebook)
        )


class CodeAnalysis(Base):
    """Code Analysis Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'code_analyses'
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

    # Custom
    import_star = Column(Integer)

    functions_with_decorators = Column(Integer)
    classes_with_decorators = Column(Integer)
    classes_with_bases = Column(Integer)

    delname = Column(Integer)
    delattr = Column(Integer)
    delitem = Column(Integer)
    assignname = Column(Integer)
    assignattr = Column(Integer)
    assignitem = Column(Integer)

    ipython = Column(Integer)
    ipython_superset = Column(Integer)

    # Scope
    class_importfrom = Column(Integer)
    global_importfrom = Column(Integer)
    nonlocal_importfrom = Column(Integer)
    local_importfrom = Column(Integer)
    total_importfrom = Column(Integer)

    class_import = Column(Integer)
    global_import = Column(Integer)
    nonlocal_import = Column(Integer)
    local_import = Column(Integer)
    total_import = Column(Integer)

    class_assign = Column(Integer)
    global_assign = Column(Integer)
    nonlocal_assign = Column(Integer)
    local_assign = Column(Integer)
    total_assign = Column(Integer)

    class_delete = Column(Integer)
    global_delete = Column(Integer)
    nonlocal_delete = Column(Integer)
    local_delete = Column(Integer)
    total_delete = Column(Integer)

    class_functiondef = Column(Integer)
    global_functiondef = Column(Integer)
    nonlocal_functiondef = Column(Integer)
    local_functiondef = Column(Integer)
    total_functiondef = Column(Integer)

    class_classdef = Column(Integer)
    global_classdef = Column(Integer)
    nonlocal_classdef = Column(Integer)
    local_classdef = Column(Integer)
    total_classdef = Column(Integer)

    # AST
    # mod
    ast_module = Column(Integer)  # max
    ast_interactive = Column(Integer)  # zero
    ast_expression = Column(Integer)  # zero
    ast_suite = Column(Integer)  # zero

    #stmt
    ast_statements = Column(Integer)

    ast_functiondef = Column(Integer)
    ast_asyncfunctiondef = Column(Integer)
    ast_classdef = Column(Integer)
    ast_return = Column(Integer)

    ast_delete = Column(Integer)
    ast_assign = Column(Integer)
    ast_augassign = Column(Integer)
    ast_annassign = Column(Integer)

    ast_print = Column(Integer)

    ast_for = Column(Integer)
    ast_asyncfor = Column(Integer)
    ast_while = Column(Integer)
    ast_if = Column(Integer)
    ast_with = Column(Integer)
    ast_asyncwith = Column(Integer)

    ast_raise = Column(Integer)
    ast_try = Column(Integer)
    ast_tryexcept = Column(Integer)
    ast_tryfinally = Column(Integer)
    ast_assert = Column(Integer)

    ast_import = Column(Integer)
    ast_importfrom = Column(Integer)
    ast_exec = Column(Integer)
    ast_global = Column(Integer)
    ast_nonlocal = Column(Integer)
    ast_expr = Column(Integer)
    ast_pass = Column(Integer)
    ast_break = Column(Integer)
    ast_continue = Column(Integer)

    # expr
    ast_expressions = Column(Integer)

    ast_boolop = Column(Integer)
    ast_binop = Column(Integer)
    ast_unaryop = Column(Integer)
    ast_lambda = Column(Integer)
    ast_ifexp = Column(Integer)
    ast_dict = Column(Integer)
    ast_set = Column(Integer)
    ast_listcomp = Column(Integer)
    ast_setcomp = Column(Integer)
    ast_dictcomp = Column(Integer)
    ast_generatorexp = Column(Integer)

    ast_await = Column(Integer)
    ast_yield = Column(Integer)
    ast_yieldfrom = Column(Integer)

    ast_compare = Column(Integer)
    ast_call = Column(Integer)
    ast_num = Column(Integer)
    ast_str = Column(Integer)
    ast_formattedvalue = Column(Integer)
    ast_joinedstr = Column(Integer)
    ast_bytes = Column(Integer)
    ast_nameconstant = Column(Integer)
    ast_ellipsis = Column(Integer)
    ast_constant = Column(Integer)

    ast_attribute = Column(Integer)
    ast_subscript = Column(Integer)
    ast_starred = Column(Integer)
    ast_name = Column(Integer)
    ast_list = Column(Integer)
    ast_tuple = Column(Integer)

    # expr_contex
    ast_load = Column(Integer)
    ast_store = Column(Integer)
    ast_del = Column(Integer)
    ast_augload = Column(Integer)
    ast_augstore = Column(Integer)
    ast_param = Column(Integer)

    # slice
    ast_slice = Column(Integer)
    ast_index = Column(Integer)

    # boolop
    ast_and = Column(Integer)
    ast_or = Column(Integer)

    # operator
    ast_add = Column(Integer)
    ast_sub = Column(Integer)
    ast_mult = Column(Integer)
    ast_matmult = Column(Integer)
    ast_div = Column(Integer)
    ast_mod = Column(Integer)
    ast_pow = Column(Integer)
    ast_lshift = Column(Integer)
    ast_rshift = Column(Integer)
    ast_bitor = Column(Integer)
    ast_bitxor = Column(Integer)
    ast_bitand = Column(Integer)
    ast_floordiv = Column(Integer)

    # unaryop
    ast_invert = Column(Integer)
    ast_not = Column(Integer)
    ast_uadd = Column(Integer)
    ast_usub = Column(Integer)

    # cmpop
    ast_eq = Column(Integer)
    ast_noteq = Column(Integer)
    ast_lt = Column(Integer)
    ast_lte = Column(Integer)
    ast_gt = Column(Integer)
    ast_gte = Column(Integer)
    ast_is = Column(Integer)
    ast_isnot = Column(Integer)
    ast_in = Column(Integer)
    ast_notin = Column(Integer)

    # others
    ast_comprehension = Column(Integer)
    ast_excepthandler = Column(Integer)
    ast_arguments = Column(Integer)
    ast_arg = Column(Integer)
    ast_keyword = Column(Integer)
    ast_alias = Column(Integer)
    ast_withitem = Column(Integer)

    # New nodes?
    ast_others = Column(String)

    processed = Column(Integer)
    skip = Column(Integer, default=0)

    ast_extslice = Column(Integer, default=0)
    ast_repr = Column(Integer, default=0)

    cell_obj = many_to_one("Cell", "code_analyses_objs")
    notebook_obj = many_to_one("Notebook", "code_analyses_objs")
    repository_obj = many_to_one("Repository", "code_analyses_objs")
    cell_modules_objs = one_to_many("CellModule", "analysis_obj")
    cell_features_objs = one_to_many("CellFeature", "analysis_obj")
    cell_names_objs = one_to_many("CellName", "analysis_obj")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<CodeAnalysis({0.repository_id}/{0.notebook_id}/{0.cell_id}[{0.index}]/{0.id})>"
            .format(self)
        )


class CellModule(Base):
    """Cell Modules Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'cell_modules'
    __table_args__ = (
        ForeignKeyConstraint(
            ['analysis_id'],
            ['code_analyses.id']
        ),
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
    analysis_id = Column(Integer)

    line = Column(Integer)
    import_type = Column(String)
    module_name = Column(String)
    local = Column(Boolean)
    skip = Column(Integer, default=0)


    cell_obj = many_to_one("Cell", "cell_modules_objs")
    notebook_obj = many_to_one("Notebook", "cell_modules_objs")
    repository_obj = many_to_one("Repository", "cell_modules_objs")
    analysis_obj = many_to_one("CodeAnalysis", "cell_modules_objs")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<Module({0.repository_id}/{0.notebook_id}/"
            u"{0.cell_id}[{0.index}]/{0.analysis_id}/{0.id}:{0.import_type})>"
        ).format(self)


class CellFeature(Base):
    """Cell Features Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'cell_features'
    __table_args__ = (
        ForeignKeyConstraint(
            ['analysis_id'],
            ['code_analyses.id']
        ),
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
    analysis_id = Column(Integer)

    line = Column(Integer)
    column = Column(Integer)
    feature_name = Column(String)
    feature_value = Column(String)
    skip = Column(Integer, default=0)

    cell_obj = many_to_one("Cell", "cell_features_objs")
    notebook_obj = many_to_one("Notebook", "cell_features_objs")
    repository_obj = many_to_one("Repository", "cell_features_objs")
    analysis_obj = many_to_one("CodeAnalysis", "cell_features_objs")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<Feature({0.repository_id}/{0.notebook_id}/"
            u"{0.cell_id}[{0.index}]/{0.analysis_id}/{0.id}:{0.feature_name})>"
        ).format(self)


class CellName(Base):
    """Cell Names Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'cell_names'
    __table_args__ = (
        ForeignKeyConstraint(
            ['analysis_id'],
            ['code_analyses.id']
        ),
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
    analysis_id = Column(Integer)

    scope = Column(String)
    context = Column(String)
    name = Column(String)
    count = Column(Integer)

    skip = Column(Integer, default=0)

    cell_obj = many_to_one("Cell", "cell_names_objs")
    notebook_obj = many_to_one("Notebook", "cell_names_objs")
    repository_obj = many_to_one("Repository", "cell_names_objs")
    analysis_obj = many_to_one("CodeAnalysis", "cell_names_objs")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<Module({0.repository_id}/{0.notebook_id}/"
            u"{0.cell_id}[{0.index}]/{0.analysis_id}/{0.id}:{0.name})>"
        ).format(self)


class RepositoryFile(Base):
    """Repository Files Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'repository_files'
    __table_args__ = (
        ForeignKeyConstraint(
            ['repository_id'],
            ['repositories.id']
        ),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    repository_id = Column(Integer)
    path = Column(String)
    size = Column(BigInt)
    skip = Column(Integer, default=0)
    had_surrogates = Column(Boolean, default=False)

    repository_obj = many_to_one("Repository", "files_objs")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<File({0.repository_id}/{0.id})>"
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

    notebook_obj = many_to_one("Notebook", "notebook_markdowns_objs")
    repository_obj = many_to_one("Repository", "notebook_markdowns_objs")

    @force_encoded_string_output
    def __repr__(self):
        return (
            u"<NotebookMarkdown({0.repository_id}/{0.notebook_id}/{0.id})>"
            .format(self)
        )


class AST(Base):
    """ AST Analysis Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'asts'
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

    cell_count = Column(Integer)

    # Custom
    import_star = Column(Integer)

    functions_with_decorators = Column(Integer)
    classes_with_decorators = Column(Integer)
    classes_with_bases = Column(Integer)

    delname = Column(Integer)
    delattr = Column(Integer)
    delitem = Column(Integer)
    assignname = Column(Integer)
    assignattr = Column(Integer)
    assignitem = Column(Integer)

    ipython = Column(Integer)
    ipython_superset = Column(Integer)

    # Scope
    class_importfrom = Column(Integer)
    global_importfrom = Column(Integer)
    nonlocal_importfrom = Column(Integer)
    local_importfrom = Column(Integer)
    total_importfrom = Column(Integer)

    class_import = Column(Integer)
    global_import = Column(Integer)
    nonlocal_import = Column(Integer)
    local_import = Column(Integer)
    total_import = Column(Integer)

    class_assign = Column(Integer)
    global_assign = Column(Integer)
    nonlocal_assign = Column(Integer)
    local_assign = Column(Integer)
    total_assign = Column(Integer)

    class_delete = Column(Integer)
    global_delete = Column(Integer)
    nonlocal_delete = Column(Integer)
    local_delete = Column(Integer)
    total_delete = Column(Integer)

    class_functiondef = Column(Integer)
    global_functiondef = Column(Integer)
    nonlocal_functiondef = Column(Integer)
    local_functiondef = Column(Integer)
    total_functiondef = Column(Integer)

    class_classdef = Column(Integer)
    global_classdef = Column(Integer)
    nonlocal_classdef = Column(Integer)
    local_classdef = Column(Integer)
    total_classdef = Column(Integer)

    # AST
    # mod
    ast_module = Column(Integer)  # max
    ast_interactive = Column(Integer)  # zero
    ast_expression = Column(Integer)  # zero
    ast_suite = Column(Integer)  # zero

    #stmt
    ast_statements = Column(Integer)

    ast_functiondef = Column(Integer)
    ast_asyncfunctiondef = Column(Integer)
    ast_classdef = Column(Integer)
    ast_return = Column(Integer)

    ast_delete = Column(Integer)
    ast_assign = Column(Integer)
    ast_augassign = Column(Integer)
    ast_annassign = Column(Integer)

    ast_print = Column(Integer)

    ast_for = Column(Integer)
    ast_asyncfor = Column(Integer)
    ast_while = Column(Integer)
    ast_if = Column(Integer)
    ast_with = Column(Integer)
    ast_asyncwith = Column(Integer)

    ast_raise = Column(Integer)
    ast_try = Column(Integer)
    ast_tryexcept = Column(Integer)
    ast_tryfinally = Column(Integer)
    ast_assert = Column(Integer)

    ast_import = Column(Integer)
    ast_importfrom = Column(Integer)
    ast_exec = Column(Integer)
    ast_global = Column(Integer)
    ast_nonlocal = Column(Integer)
    ast_expr = Column(Integer)
    ast_pass = Column(Integer)
    ast_break = Column(Integer)
    ast_continue = Column(Integer)

    # expr
    ast_expressions = Column(Integer)

    ast_boolop = Column(Integer)
    ast_binop = Column(Integer)
    ast_unaryop = Column(Integer)
    ast_lambda = Column(Integer)
    ast_ifexp = Column(Integer)
    ast_dict = Column(Integer)
    ast_set = Column(Integer)
    ast_listcomp = Column(Integer)
    ast_setcomp = Column(Integer)
    ast_dictcomp = Column(Integer)
    ast_generatorexp = Column(Integer)

    ast_await = Column(Integer)
    ast_yield = Column(Integer)
    ast_yieldfrom = Column(Integer)

    ast_compare = Column(Integer)
    ast_call = Column(Integer)
    ast_num = Column(Integer)
    ast_str = Column(Integer)
    ast_formattedvalue = Column(Integer)
    ast_joinedstr = Column(Integer)
    ast_bytes = Column(Integer)
    ast_nameconstant = Column(Integer)
    ast_ellipsis = Column(Integer)
    ast_constant = Column(Integer)

    ast_attribute = Column(Integer)
    ast_subscript = Column(Integer)
    ast_starred = Column(Integer)
    ast_name = Column(Integer)
    ast_list = Column(Integer)
    ast_tuple = Column(Integer)

    # expr_contex
    ast_load = Column(Integer)
    ast_store = Column(Integer)
    ast_del = Column(Integer)
    ast_augload = Column(Integer)
    ast_augstore = Column(Integer)
    ast_param = Column(Integer)

    # slice
    ast_slice = Column(Integer)
    ast_index = Column(Integer)

    # boolop
    ast_and = Column(Integer)
    ast_or = Column(Integer)

    # operator
    ast_add = Column(Integer)
    ast_sub = Column(Integer)
    ast_mult = Column(Integer)
    ast_matmult = Column(Integer)
    ast_div = Column(Integer)
    ast_mod = Column(Integer)
    ast_pow = Column(Integer)
    ast_lshift = Column(Integer)
    ast_rshift = Column(Integer)
    ast_bitor = Column(Integer)
    ast_bitxor = Column(Integer)
    ast_bitand = Column(Integer)
    ast_floordiv = Column(Integer)

    # unaryop
    ast_invert = Column(Integer)
    ast_not = Column(Integer)
    ast_uadd = Column(Integer)
    ast_usub = Column(Integer)

    # cmpop
    ast_eq = Column(Integer)
    ast_noteq = Column(Integer)
    ast_lt = Column(Integer)
    ast_lte = Column(Integer)
    ast_gt = Column(Integer)
    ast_gte = Column(Integer)
    ast_is = Column(Integer)
    ast_isnot = Column(Integer)
    ast_in = Column(Integer)
    ast_notin = Column(Integer)

    # others
    ast_comprehension = Column(Integer)
    ast_excepthandler = Column(Integer)
    ast_arguments = Column(Integer)
    ast_arg = Column(Integer)
    ast_keyword = Column(Integer)
    ast_alias = Column(Integer)
    ast_withitem = Column(Integer)

    # New nodes?
    ast_others = Column(String)

    skip = Column(Integer, default=0)

    ast_extslice = Column(Integer, default=0)
    ast_repr = Column(Integer, default=0)

    notebook_obj = many_to_one("Notebook", "asts_objs")
    python_file_obj = many_to_one("PythonFile", "asts_objs")
    repository_obj = many_to_one("Repository", "asts_objs")

    @force_encoded_string_output
    def __repr__(self):
        if self.type == 'notebook':
            return (
                u"<AST({0.repository_id}/{0.notebook_id}/{0.id})>"
            ).format(self)
        elif self.type == 'python_file':
            return (
                u"<AST({0.repository_id}/{0.python_file_id}/{0.id})>"
            ).format(self)


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


class Feature(Base):
    """Features Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'features'
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

    any = Column(String)
    any_count = Column(Integer)

    shadown_ref = Column(String)
    shadown_ref_count = Column(Integer)
    output_ref = Column(String)
    output_ref_count = Column(Integer)
    system = Column(String)
    system_count = Column(Integer)
    set_next_input = Column(String)
    set_next_input_count = Column(Integer)
    input_ref = Column(String)
    input_ref_count = Column(Integer)
    magic = Column(String)
    magic_count = Column(Integer)
    run_line_magic = Column(String)
    run_line_magic_count = Column(Integer)
    run_cell_magic = Column(String)
    run_cell_magic_count = Column(Integer)
    getoutput = Column(String)
    getoutput_count = Column(Integer)
    set_hook = Column(String)
    set_hook_count = Column(Integer)

    others = Column(String)

    skip = Column(Integer, default=0)

    notebook_obj = many_to_one("Notebook", "features_objs")
    python_file_obj = many_to_one("PythonFile", "features_objs")
    repository_obj = many_to_one("Repository", "features_objs")

    @force_encoded_string_output
    def __repr__(self):
        if self.type == 'notebook':
            return (
                u"<Feature({0.repository_id}/{0.notebook_id}/{0.id})>"
            ).format(self)
        elif self.type == 'python_file':
            return (
                u"<Feature({0.repository_id}/{0.python_file_id}/{0.id})>"
            ).format(self)


class Name(Base):
    """Names Table"""
    # pylint: disable=too-few-public-methods, invalid-name
    __tablename__ = 'names'
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
    any_any_counts = Column(String)
    any_class = Column(String)
    any_class_counts = Column(String)
    any_import = Column(String)
    any_import_counts = Column(String)
    any_importfrom = Column(String)
    any_importfrom_counts = Column(String)
    any_function = Column(String)
    any_function_counts = Column(String)
    any_param = Column(String)
    any_param_counts = Column(String)
    any_del = Column(String)
    any_del_counts = Column(String)
    any_load = Column(String)
    any_load_counts = Column(String)
    any_store = Column(String)
    any_store_counts = Column(String)

    nonlocal_any = Column(String)
    nonlocal_any_counts = Column(String)
    nonlocal_class = Column(String)
    nonlocal_class_counts = Column(String)
    nonlocal_import = Column(String)
    nonlocal_import_counts = Column(String)
    nonlocal_importfrom = Column(String)
    nonlocal_importfrom_counts = Column(String)
    nonlocal_function = Column(String)
    nonlocal_function_counts = Column(String)
    nonlocal_param = Column(String)
    nonlocal_param_counts = Column(String)
    nonlocal_del = Column(String)
    nonlocal_del_counts = Column(String)
    nonlocal_load = Column(String)
    nonlocal_load_counts = Column(String)
    nonlocal_store = Column(String)
    nonlocal_store_counts = Column(String)

    local_any = Column(String)
    local_any_counts = Column(String)
    local_class = Column(String)
    local_class_counts = Column(String)
    local_import = Column(String)
    local_import_counts = Column(String)
    local_importfrom = Column(String)
    local_importfrom_counts = Column(String)
    local_function = Column(String)
    local_function_counts = Column(String)
    local_param = Column(String)
    local_param_counts = Column(String)
    local_del = Column(String)
    local_del_counts = Column(String)
    local_load = Column(String)
    local_load_counts = Column(String)
    local_store = Column(String)
    local_store_counts = Column(String)

    class_any = Column(String)
    class_any_counts = Column(String)
    class_class = Column(String)
    class_class_counts = Column(String)
    class_import = Column(String)
    class_import_counts = Column(String)
    class_importfrom = Column(String)
    class_importfrom_counts = Column(String)
    class_function = Column(String)
    class_function_counts = Column(String)
    class_param = Column(String)
    class_param_counts = Column(String)
    class_del = Column(String)
    class_del_counts = Column(String)
    class_load = Column(String)
    class_load_counts = Column(String)
    class_store = Column(String)
    class_store_counts = Column(String)

    global_any = Column(String)
    global_any_counts = Column(String)
    global_class = Column(String)
    global_class_counts = Column(String)
    global_import = Column(String)
    global_import_counts = Column(String)
    global_importfrom = Column(String)
    global_importfrom_counts = Column(String)
    global_function = Column(String)
    global_function_counts = Column(String)
    global_param = Column(String)
    global_param_counts = Column(String)
    global_del = Column(String)
    global_del_counts = Column(String)
    global_load = Column(String)
    global_load_counts = Column(String)
    global_store = Column(String)
    global_store_counts = Column(String)

    main_any = Column(String)
    main_any_counts = Column(String)
    main_class = Column(String)
    main_class_counts = Column(String)
    main_import = Column(String)
    main_import_counts = Column(String)
    main_importfrom = Column(String)
    main_importfrom_counts = Column(String)
    main_function = Column(String)
    main_function_counts = Column(String)
    main_param = Column(String)
    main_param_counts = Column(String)
    main_del = Column(String)
    main_del_counts = Column(String)
    main_load = Column(String)
    main_load_counts = Column(String)
    main_store = Column(String)
    main_store_counts = Column(String)

    others = Column(String)

    skip = Column(Integer, default=0)

    notebook_obj = many_to_one("Notebook", "names_objs")
    python_file_obj = many_to_one("PythonFile", "names_objs")
    repository_obj = many_to_one("Repository", "names_objs")

    @force_encoded_string_output
    def __repr__(self):
        if self.type == 'notebook':
            return (
                u"<Name({0.repository_id}/{0.notebook_id}/{0.id})>"
            ).format(self)
        elif self.type == 'python_file':
            return (
                u"<Name({0.repository_id}/{0.python_file_id}/{0.id})>"
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
