from collections import Counter, OrderedDict
from src.db.database import CodeAnalysis, CellModule, CellFeature, CellName, MarkdownFeature

IGNORE_COLUMNS = {
    "id", "repository_id", "notebook_id", "cell_id", "index",
    "skip", "processed",
}

MARKDOWN_COLUMNS = [
    col.name for col in MarkdownFeature.__table__.columns
    if col.name not in IGNORE_COLUMNS
    if col.name != "language"
]

AST_COLUMNS = [
    col.name for col in CodeAnalysis.__table__.columns
    if col.name not in IGNORE_COLUMNS
    if col.name != "ast_others"
]

MODULE_LOCAL = {
    True: "local",
    False: "external",
    "any": "any",
}

MODULE_TYPES = {
    "any", "import_from", "import", "load_ext"
}

FEATURES = {
    "IPython/shadown_ref": "shadown_ref",
    "IPython/output_ref": "output_ref",
    "IPython/system": "system",
    "IPython/set_next_input": "set_next_input",
    "IPython/input_ref": "input_ref",
    "IPython/magic": "magic",
    "IPython/run_line_magic": "run_line_magic",
    "IPython/run_cell_magic": "run_cell_magic",
    "IPython/getoutput": "getoutput",
    "IPython/set_hook": "set_hook",
    "any": "any",
}

NAME_SCOPES = ["any", "nonlocal", "local", "class", "global", "main"]
NAME_CONTEXTS = ["any", "class", "import", "importfrom", "function", "param", "del", "load", "store"]


def calculate_markdown(session, notebook):
    agg_markdown = {col: 0 for col in MARKDOWN_COLUMNS}
    agg_markdown["cell_count"] = 0
    markdown_languages = Counter()
    query = (
        notebook.markdown_features_objs
        # .order_by(MarkdownFeature.index.asc())
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


def calculate_ast(session, file, file_type):
    agg_ast = {col: 0 for col in AST_COLUMNS}
    agg_ast["cell_count"] = 0
    ast_others = []

    if file_type == 'notebook':
        query = (
            file.code_analyses_objs
            # .order_by(CodeAnalysis.index.asc())
        )
    elif file_type == 'python_file':
        query = (
            file.python_analyzes_objs
            # .order_by(PythonAnalysis.id.asc())
        )
    else:
        return "invalid file type. Unable to aggregate it"

    for ast in query:
        agg_ast["cell_count"] += 1
        if ast.ast_others:
            ast_others.append(ast.ast_others)
        for column in AST_COLUMNS:
            agg_ast[column] += int(getattr(ast, column))
    agg_ast["ast_others"] = ",".join(ast_others)
    agg_ast["repository_id"] = file.repository_id
    agg_ast[f"{file_type}_id"] = file.id
    agg_ast["type"] = file_type
    return agg_ast


def calculate_modules(session, file, file_type):
    temp_agg = {
        (local + "_" + type_): OrderedDict()
        for _, local in MODULE_LOCAL.items()
        for type_ in MODULE_TYPES
    }
    temp_agg["index"] = OrderedDict()
    others = []

    def add_key(key, module):
        if key in temp_agg:
            temp_agg[key][module.module_name] = 1
        else:
            others.append("{}:{}".format(key, module.module_name))


    if file_type == 'notebook':
        query = (
            file.cell_modules_objs
            .order_by(CellModule.index.asc())
        )
    elif file_type == 'python_file':
        query = (
            file.python_file_modules_objs
            # .order_by(PythonModule.id.asc())
        )
    else:
        return "invalid file type. Unable to aggregate it"

    for module in query:
        if file_type == "notebook":
            temp_agg["index"][str(module.index)] = 1
        # local = module.local or (module.local_possibility > 0)
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
    agg[f"{file_type}_id"] = file.id
    agg["type"] = file_type
    return agg


def calculate_features(session, file, file_type):
    temp_agg = {
        col: OrderedDict()
        for col in FEATURES.values()
    }
    temp_agg["index"] = OrderedDict()
    others = []
    def add_feature(key, feature):
        if key in temp_agg:
            temp_agg[key][feature.feature_value] = 1
        else:
            others.append("{}:{}".format(key, feature.feature_value))



    if file_type == 'notebook':
        query = (
            file.cell_features_objs
            .order_by(CellFeature.index.asc())
        )
    elif file_type == 'python_file':
        query = (
            file.python_file_features_objs
            # .order_by(PythonModule.id.asc())
        )
    else:
        return "invalid file type. Unable to aggregate it"

    for feature in query:
        if file_type == "notebook":
            temp_agg["index"][str(feature.index)] = 1
        key = FEATURES.get(feature.feature_name, feature.feature_name)
        add_feature(key, feature)

        key = "any"
        add_feature(key, feature)
    agg = {}
    for attr, elements in temp_agg.items():
        agg[attr] = ",".join(elements)
        agg[attr + "_count"] = len(elements)

    agg["others"] = ",".join(others)
    agg["repository_id"] = file.repository_id
    agg[f"{file_type}_id"] = file.id
    agg["type"] = file_type
    return agg


def calculate_names(session, file, file_type):
    temp_agg = {
        (scope + "_" + context): Counter()
        for scope in NAME_SCOPES
        for context in NAME_CONTEXTS
    }
    index = OrderedDict()
    others = []
    def add_key(key, name):
        if key in temp_agg:
            temp_agg[key][name.name] += name.count
        else:
            others.append("{}:{}({})".format(key, name.name, name.count))

    if file_type == 'notebook':
        query = (
            file.cell_names_objs
            .order_by(CellName.index.asc())
        )
    elif file_type == 'python_file':
        query = (
            file.python_file_names_objs
            # .order_by(PythonAnalysis.id.asc())
        )
    else:
        return "invalid file type. Unable to aggregate it"


    for name in query:
        if file_type == "notebook":
            index[str(name.index)] = 1
        key = name.scope + "_" + name.context
        add_key(key, name)

        key = name.scope + "_any"
        add_key(key, name)

        key = "any_" + name.context
        add_key(key, name)

        key = "any_any"
        add_key(key, name)

    agg = {}
    agg["index"] = ",".join(index)
    agg["index_count"] = len(index)
    for attr, elements in temp_agg.items():
        mc = elements.most_common()
        agg[attr] = ",".join(str(name) for name, _ in mc)
        agg[attr + "_counts"] = ",".join(str(count) for _, count in mc)

    agg["others"] = ",".join(others)
    agg["repository_id"] = file.repository_id
    agg[f"{file_type}_id"] = file.id
    agg["type"] = file_type
    return agg