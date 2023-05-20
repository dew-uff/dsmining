import os
import sys
src_path = os.path.dirname(os.path.abspath(''))
if src_path not in sys.path:
    sys.path.append(src_path)

from collections import Counter, OrderedDict
from src.db.database import CellModule, CellMarkdownFeature, PythonFileModule, CellDataIO, PythonFileDataIO, DataIO
from src.helpers.h3_utils import vprint

IGNORE_COLUMNS = {
    "id", "repository_id", "notebook_id", "cell_id", "index",
    "skip", "processed", 'state', 'created_at', 'updated_at'
}

MARKDOWN_COLUMNS = [
    col.name for col in CellMarkdownFeature.__table__.columns
    if col.name not in IGNORE_COLUMNS
    if col.name != "language"
]

MODULE_LOCAL = {
    True: "local",
    False: "external",
    "any": "any",
}

MODULE_TYPES = {
    "any", "import_from", "import", "load_ext"
}
modes = [
    "r", "w", "x", "a",
    "rb", "wb", "xb", "ab",
    "rt", "wt", "xt", "at",
    "r+", "w+", "x+", "a+",
    "rb+", "wb+", "xb+", "ab+",
    "rt+", "wt+", "xt+", "at+",
]

input_modes = ["r", "rb", "rt", "rb+", "rt+"]
output_modes = [
    "w", "x", "a",
    "wb", "xb", "ab",
    "wt", "xt", "at",
    "w+", "x+", "a+",
    "wb+", "xb+", "ab+",
    "wt+", "xt+", "at+",
]

input_functions_names = ["read", "open", "input", "load"]
output_functions_names = ["write", "save", "output"]


def get_open_type(mode):
    if any(word in mode for word in input_modes):
        return "input"
    elif any(word in mode for word in output_modes):
        return "output"
    else:
        return "unknown"


def infer_source(source):
    web = ["http://", "https://", "www.", ".com", ".gov"]# noqa
    if "@" in source:
        return "email", None, None
    elif any(word in source for word in web):
        return "website", None, None
    else:
        file_name, extension = source.rsplit(".", 1)
        return "file", file_name, extension


def infer_data_io_type(data_io):
    if data_io.mode:
        return get_open_type(data_io.mode)
    else:
        if any(word in data_io.function_name for word in input_functions_names):
            return "input"
        elif any(word in data_io.function_name for word in output_functions_names):
            return "output"
        else:
            return "unknown"


def calculate_markdown(notebook):
    agg_markdown = {col: 0 for col in MARKDOWN_COLUMNS}
    agg_markdown["cell_count"] = 0
    markdown_languages = Counter()
    query = (
        notebook.cell_markdown_features_objs
        .order_by(CellMarkdownFeature.index.asc())
    )
    for feature in query:
        agg_markdown["cell_count"] += 1
        markdown_languages[feature.language] += 1
        for column in MARKDOWN_COLUMNS:
            agg_markdown[column] += int(getattr(feature, column))

    mc_languages = markdown_languages.most_common()
    agg_markdown["main_language"] = mc_languages[0][0] if mc_languages else "none"
    agg_markdown["languages"] = ",".join(str(lang) for lang, _ in mc_languages)
    agg_markdown["languages_counts"] = ",".join(str(count) for _, count in mc_languages)
    agg_markdown["repository_id"] = notebook.repository_id
    agg_markdown["notebook_id"] = notebook.id
    return agg_markdown


def calculate_modules(file, file_type):
    temp_agg = {
        (local + "_" + type_): OrderedDict()
        for _, local in MODULE_LOCAL.items()
        for type_ in MODULE_TYPES
    }
    temp_agg["index"] = OrderedDict()
    others = []

    def add_key(key_, module_):
        if key_ in temp_agg:
            temp_agg[key_][module_.module_name] = 1
        else:
            others.append("{}:{}".format(key_, module_.module_name))

    if file_type == 'notebook':
        query = (file.cell_modules_objs.order_by(CellModule.index.asc()))
    elif file_type == 'python_file':
        query = (file.python_file_modules_objs.order_by(PythonFileModule.id.asc()))
    else:
        return "invalid file type. Unable to aggregate it"

    for module in query:
        if file_type == "notebook":
            temp_agg["index"][str(module.index)] = 1
        local = module.local

        key = MODULE_LOCAL[local] + "_" + module.import_type
        add_key(key, module)

        key = MODULE_LOCAL[local] + "_any"
        add_key(key, module)

        key = "any_" + module.import_type
        add_key(key, module)

        key = "any_any"
        add_key(key, module)

    agg = {}
    for attr, elements in temp_agg.items():
        agg[attr] = ",".join(elements)
        agg[attr + "_count"] = len(elements)

    agg["others"] = ",".join(others)
    agg["repository_id"] = file.repository_id
    agg["{}_id".format(file_type)] = file.id
    agg["type"] = file_type
    return agg


def calculate_data_ios(file, file_type):
    query = []
    notebook_id, python_file_id, index = None, None, None
    check_index = False

    if file_type == 'notebook':
        query = (file.cell_data_ios_objs.order_by(CellDataIO.index.asc()))
        notebook_id = file.id
        check_index = True
    elif file_type == 'python_file':
        query = (file.python_file_data_ios_objs.order_by(PythonFileDataIO.id.asc()))
        python_file_id = file.id

    dtiorows = []
    for data_io in query:
        index = None
        infered_function_type = infer_data_io_type(data_io)
        infered_source_type, infered_file, infered_file_extension = infer_source(data_io.source)

        if check_index:
            index = data_io.index

        row = DataIO(
            repository_id=file.repository_id,
            notebook_id=notebook_id,
            python_file_id=python_file_id,
            type=file_type,
            index=index,
            line=data_io.line,
            infered_type=infered_function_type,
            caller=data_io.caller,
            function_name=data_io.function_name,
            function_type=data_io.function_type,
            source=data_io.source,
            infered_source_type=infered_source_type,
            infered_file=infered_file,
            infered_file_extension=infered_file_extension

        )

        dtiorows.append(row)
    return dtiorows


def load_repository(session, file, repository_id):
    if repository_id != file.repository_id:
        repository_id = file.repository_id
        try:
            session.commit()
        except Exception as err:
            vprint(0, 'Failed to save agreggations from repository {} due to {}'.format(
                repository_id, err
            ))

        vprint(0, 'Processing repository: {}'.format(repository_id))
        return file.repository_id

    return repository_id
