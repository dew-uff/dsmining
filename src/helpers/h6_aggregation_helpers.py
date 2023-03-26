from collections import Counter, OrderedDict
from src.db.database import CellModule, CellMarkdownFeature, PythonFileModule
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
    agg[f"{file_type}_id"] = file.id
    agg["type"] = file_type
    return agg


def load_repository(session, file, repository_id):
    if repository_id != file.repository_id:
        try:
            session.commit()
        except Exception as err:
            vprint(0, 'Failed to save modules from repository {} due to {}'.format(
                repository_id, err
            ))

        vprint(0, 'Processing repository: {}'.format(repository_id))
        return file.repository_id

    return repository_id
