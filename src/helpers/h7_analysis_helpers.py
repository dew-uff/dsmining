import os
import sys
src_path = os.path.dirname(os.path.abspath(''))
if src_path not in sys.path:
    sys.path.append(src_path)

import re
import csv
import math
import locale
import matplotlib

import numpy as np
import seaborn as sns
import pandas as pd
import dask.dataframe as dd
import src.config.consts as consts
import matplotlib.ticker as ticker

from contextlib import contextmanager
from IPython.display import display
from collections import namedtuple
from collections import Counter, defaultdict

from matplotlib import pyplot as plt
from dask.dataframe.core import Series as DaskSeries
from dask.array.core import Array as DaskArray
from dask.array import histogram as _dask_histogram
import matplotlib.colors as mcolors

Distribution = namedtuple("Distribution", "min q1 median q3 max")
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')


def formatar_inteiro(numero):
    return locale.format_string('%.0f', numero, grouping=True)


def formatar_decimal(numero, duas_casas=False):
    if duas_casas:
        return locale.format_string('%.2f', numero, grouping=True)
    return locale.format_string('%.1f', numero, grouping=True)


def count(dataframe, *attrs):
    counter = Counter()
    for attr in attrs:
        counter[attr] = len(dataframe[dataframe[attr] != 0])
    return counter


def pastel_colormap(size=5, reverse=False):
    colors = ['#FFCED1', '#FFFDD1', '#AEEAC6', '#CDE7F0', '#e3e3e3']

    cmapp = mcolors.ListedColormap(colors[:size])
    return cmapp


def tex_escape(text):
    """
        :param text: a plain text message
        :return: the message escaped to appear correctly in LaTeX.
    """
    conv = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
        '<': r'\textless{}',
        '>': r'\textgreater{}',
    }
    regex = re.compile('|'.join(re.escape(key) for key in sorted(conv.keys(),
                                                                 key=lambda item: - len(item))))
    return regex.sub(lambda match: conv[match.group()], text)


def relative_var(key, part, total, t1="{0:,}", t2="{0:.2%}"):
    relative_text = var(key, part / total, t2)
    part_text = var(key + "_total", part, t1)
    return "{} ({})".format(part_text, relative_text)


def var(key, value, template="{}"):
    result = template.format(value)
    latex_result = tex_escape(result)
    data = {}
    if os.path.exists("{}/variables.dat".format(consts.OUTPUTS_DIR)):
        with open("{}/variables.dat".format(consts.OUTPUTS_DIR), "r") as fil:
            for line in fil:
                line = line.strip()
                if line:
                    k, v = line.split(" = ")
                    data[k] = v
    data[key] = latex_result
    with open("{}/variables.dat".format(consts.OUTPUTS_DIR), "w") as fil:
        fil.writelines(
            "{} = {}\n".format(k, v)
            for k, v in data.items()
        )
    return result
            

def fetchgenerator(cursor, arraysize=1000):
    """An iterator that uses fetchmany to keep memory usage down"""
    while True:
        results = cursor.fetchmany(arraysize)
        if not results:
            break
        yield from results  # noqa
        
        
def dask_from_query(session, query, file):
    q = session.execute(query)
    with open(file, 'w') as outfile:
        outcsv = csv.writer(outfile)
        outcsv.writerow(x[0] for x in q.cursor.description)
        outcsv.writerows(fetchgenerator(q.cursor))
    return dd.read_csv(file)


def display_counts(
    df, width=20, show_values=False, plot=True, template="{0:,g}", template2="{0:,g}", cut=None, logy=True,
    color='b'
):
    counter = Counter()
    df.agg(lambda x: counter.update(x))
    del counter['']
    counts = pd.Series(counter).sort_values(ascending=False)
    counts = counts.compute() if isinstance(counts, DaskSeries) else counts
    if cut:
        counts = counts[cut]
    if isinstance(counts, pd.Series):
        counts = counts.to_frame()
    ax = counts.plot.bar(logy=logy, color=color)

    fig = ax.get_figure()
    fig.set_size_inches(width, 5, forward=True)
    if plot:
        plt.show()
        display(counts)
    else:
        return fig, ax, counts


def violinplot(column, tick, lim):
    ax = sns.violinplot(x=column)
    fig = ax.get_figure()
    fig.set_size_inches(30, 5)
    plt.xlim(lim)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(tick))

    return Distribution(column.min(), column.quantile(0.25), column.median(), column.quantile(0.75), column.max())


def histogram(column, bins, tick, lim, ax=None):
    histfn = _dask_histogram if isinstance(column, DaskArray) else np.histogram
    hist, bins = histfn(column, bins=bins, range=lim)
    x = 0.5 * (bins[1:] + bins[:-1])
    width = np.diff(bins)
    ax = ax or plt.gca()
    fig = ax.get_figure()
    fig.set_size_inches(30, 5)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(tick))
    ax.bar(x, hist, width);  # noqa


dask_histogram = histogram


def numpy_distribution(column):
    return Distribution(
        column.min(),
        np.percentile(column, 25),
        np.median(column),
        np.percentile(column, 75),
        column.max()
    )


def counter_hist(counter, label="key", **kwargs):
    common = counter.most_common()
    arr = pd.DataFrame([c for n, c in common], index=[n for n, c in common], columns=[label])
    display_counts(arr, **kwargs)


def count(dataframe, *attrs):
    counter = Counter()
    for attr in attrs:
        counter[attr] = len(dataframe[dataframe[attr] != 0])
    return counter


def getitem(container, index, default=None):
    try:
        return container[index]
    except IndexError:
        return default


def describe_processed(series, statuses):
    result = Counter()
    for key, value in series.iteritems(): # noqa

        if key < 0:
            print("Skipping: {}: {}".format(key, value))
            continue
        bits = [pos for pos, value in enumerate(bin(key)[2:][::-1]) if int(value)]
        if not bits:
            stat = statuses.get(0, "<undefined>")
            if stat == "<undefined>":
                print("Undefined: {}: {}".format(0, value))
            result[stat] += value
        else:
            for bit in bits:
                stat = statuses.get(2 ** bit, "<undefined>")
                if stat == "<undefined>":
                    print("Undefined: {}: {}".format(2 ** bit, value))
                result[stat] += value
    return pd.Series(result)


def distribution_with_boxplot(column, first, last, step,
                              ylabel, xlabel, draw_values=True,
                              bins=None, template_x="{:g}"):
    bins = bins if bins else last - first
    computed = column.compute() if isinstance(column, DaskSeries) else column
    distribution = numpy_distribution(computed)

    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    dask_histogram(column.values, bins, step, (first, last), ax=ax1)
    ax1.xaxis.tick_bottom()
    ax1.set_ylabel(ylabel)
    ax1.get_yaxis().set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda x, p: "{0:,g}".format(x)))

    bp = ax2.boxplot(computed, showfliers=False, vert=False, widths=[.5])
    ax2.yaxis.set_ticks_position('none')
    ax2.set_yticklabels([""])
    ax2.set_xlabel(xlabel)

    if draw_values:
        draw = defaultdict(list)
        for key, value in zip(distribution._fields, distribution):
            draw[float(value)].append(key)
        draw[bp['caps'][0].get_xdata()[0]].append("Q1 - 1.5*IQR")
        draw[bp['caps'][1].get_xdata()[0]].append("Q3 + 1.5*IQR")
        draw_list = []
        position = 0.6
        for value, keys in draw.items():
            if first <= value <= last:
                text = template_x.format(value)
                ax2.annotate(text, (value, position), ha="center")
                position = 0.6 if position > 1.0 else 1.3
            else:
                draw_list.append("{0}: {1}".format(", ".join(keys), template_x.format(value)))

        ax2.annotate("\n".join(draw_list), (last, 1), ha="right")

    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    return distribution


@contextmanager
def savefig(name, width=8, height=6):
    plt.rc('axes', titlesize=16) 
    plt.rc('axes', labelsize=16) 
    plt.rc('font', size=14)
    yield
    fig = plt.gcf()
    fig.set_size_inches(width, height)
    # fig.savefig("{}/outputs/svg/{}.svg".format(consts.OUTPUTS_DIR, name), bbox_inches='tight')
    # fig.savefig("{}/outputs/pdf/{}.pdf".format(consts.OUTPUTS_DIR, name), bbox_inches='tight')
    fig.savefig("{}/outputs/png/{}.png".format(consts.OUTPUTS_DIR, name), bbox_inches='tight')


@contextmanager
def cell_distribution(filename, width, height, select, bins, cell_type_bins_arrays, colors=None, relative=True):
    bar_l = [i for i in range(bins + 1)]
    total = 0
    if relative:
        total = sum((cell_type_bins_arrays[key] for key in select),  np.zeros(bins + 1))
    with savefig(filename, width, height):
        bottom = np.zeros(bins + 1)
        ax = plt.gca()
        for key in select:
            column = cell_type_bins_arrays[key]
            if relative:
                column = column / total * 100
            kwargs = {}
            if colors and key in colors:
                kwargs["color"] = colors[key]
                ax.bar(bar_l, column, bottom=bottom, label=key, alpha=0.9, width=1, **kwargs)
            bottom += column
        fig = ax.get_figure()
        fig.set_size_inches(width, height)
        ax.set_yticklabels([])
        ax.set_xticks([0, bins / 2, bins])
        ax.set_xlim(0, bins)
        plt.xticks(fontsize=14)
        ax.set_xticklabels(["Beginning", "Middle", "End"])
        ax.set_ylabel("% of Cells" if relative else "# of Cells", fontsize=16)
        yield ax
        ax.xaxis.set_ticks_position('none') 
        ax.yaxis.set_ticks_position('none') 
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)


def get_python_version(python_notebooks):
    python_notebooks = python_notebooks.assign(minor_version=lambda x: x.language_version.str[:3])
    python_notebooks = python_notebooks.assign(major_version=lambda x: x.language_version.str[:1])
    python_version = python_notebooks.minor_version.value_counts(dropna=False) \
        .rename_axis('Versions').to_frame("Notebooks")

    pv = python_version[:7].reset_index(level=0)
    others = pd.DataFrame(data={
        'Versions': ['Other Versions'],
        'Notebooks': [python_version['Notebooks'][7:].sum()]
    })

    pv2 = pd.concat([pv, others]).reset_index(drop=True) \
        .sort_values(by='Notebooks', ascending=False)

    unknown = pv2.query("Versions=='unk'")
    if not unknown.empty:
        index = unknown.index[0]
        pv2.at[index, "Versions"] = 'Unknown'

    return pv2


def get_toplevel_modules(modules, columns):
    # columns = [
    #     "any_any", "local_any", "external_any",
    #     "any_import_from", "local_import_from", "external_import_from",
    #     "any_import", "local_import", "external_import",
    #     "any_load_ext", "local_load_ext", "external_load_ext",
    # ]

    for column in columns:
        print("Processin column {}...".format(column))
        modules[column] = modules[column].apply(lambda c: {a for a in c.split(",") if a})
        modules["toplevel_" + column] = modules[column].apply(lambda imports: {
            getitem(x.split("."), 0, x) for x in imports
        })
        modules["toplevel_" + column + "_count"] = modules["toplevel_" + column].apply(len)

    return modules


def calculate_intervals(current_repository_commits):
    previous = None
    repository_intervals = []
    for i, commit in current_repository_commits.iterrows():
        if not previous:
            previous = commit.date
        else:
            duration = commit.date - previous
            repository_intervals.append(duration)
            previous = commit.date
    intervals = pd.DataFrame(repository_intervals, columns=["timedelta"])

    return intervals


def calculate_frequencies(repositories_with_commits, commits):
    frequency = []
    frequency_in_days = []

    for index, repository in repositories_with_commits.iterrows():
        print(repository.repository_id)
        if repository.commits > 1:
            repository_id = repository.repository_id
            current_repository_commits = commits[commits.repository_id == repository_id].sort_values(by="date")
            intervals = calculate_intervals(current_repository_commits)
            mean = intervals.timedelta.mean()
            frequency.append(mean)
            frequency_in_days.append(mean.days)
        else:
            frequency.append(None)
            frequency_in_days.append(None)
    repositories_with_commits['frequency_timedelta'] = frequency
    repositories_with_commits['frequency_in_days'] = frequency_in_days
    return repositories_with_commits


def create_repositories_piechart(repository_attribute, attribute_name,
                                 bins=None, labels=None):
    if bins is None:
        bins = [-1, 0, 1, 2, 5, 10, 20, 50, 100, 50000]
    if labels is None:
        labels = ["0","1", "2", "3-5", "6-10", "11-20", "21-50", "51-100", "> 100"]

    attribute = pd.cut(repository_attribute["{}".format(attribute_name)], bins=bins).value_counts() \
        .rename_axis('repositories').to_frame(attribute_name).reset_index(level=0).sort_values(by='repositories')
    attribute["labels"] = labels
    attribute = attribute[attribute["{}".format(attribute_name)] > 0]
    fig, ax = plt.subplots(figsize=(15, 4))
    attribute.plot \
        .pie(ax=ax, y="{}".format(attribute_name),
             title="Number of {} per Repository".format(attribute_name.capitalize()),
             labels=attribute.labels, ylabel="{}".format(attribute_name.capitalize()), cmap="cool",
             autopct=(lambda prct_value: '{:.1f}%\n{:.0f}'
                      .format(prct_value, (len(repository_attribute) * prct_value / 100))
                      )).get_legend().remove()
    ax.yaxis.set_label_coords(-0.1, 0.5)
    return fig, ax

def check_test(y, name):
    return y == name or y.startswith(name) and y[len(name)] == '.'

def is_test(y):
    """Modules related to test, mocks, and fixtures.
    Select Unittet, Mock tools, Fuzz Testing tools, Acceptance testing tools
    from https://wiki.python.org/moin/PythonTestingToolsTaxonomy

    Unit test, """
    return (
            "test" in y
            or "TEST" in y
            or "Test" in y
            or "mock" in y
            or "MOCK" in y
            or "Mock" in y
            or "fixture" in y
            or "FIXTURE" in y
            or "Fixture" in y
            # or check_test(y, 'unittest')
            # or check_test(y, 'doctest')
            # or check_test(y, 'pytest')
            or check_test(y, 'nose')
            # or check_test(y, 'testify')
            or check_test(y, 'twisted.trial')
            # or check_test(y, 'testify')
            or check_test(y, 'subunit')
            # or check_test(y, 'testresources')
            or check_test(y, 'reahl.tofu')
            # or check_test(y, 'testtools')
            or check_test(y, 'sancho')
            # or check_test(y, 'zope.testing')
            or check_test(y, 'pry')
            or check_test(y, 'pythoscope')
            # or check_test(y, 'testlib')
            # or check_test(y, 'pytest')
            # or check_test(y, 'utils.dutest')

            # or check_test(y, 'testoob')
            # or check_test(y, 'TimedTest') # pyUnitPerf
            # or check_test(y, 'LoadTest') # pyUnitPerf
            or check_test(y, 'peckcheck')
            # or check_test(y, 'testosterone')
            # or check_test(y, 'qunittest')

            # Mock tools
            or check_test(y, 'ludibrio')
            # or check_test(y, 'mock')
            # or check_test(y, 'pymock')
            # or check_test(y, 'unittest.mock')
            # or check_test(y, 'pmock')
            # or check_test(y, 'minimock')
            # or check_test(y, 'svnmock')
            # or check_test(y, 'mocker')
            or check_test(y, 'reahl.stubble')
            or check_test(y, 'mox')
            # or check_test(y, 'mocktest')
            or check_test(y, 'fudge')
            # or check_test(y, 'mockito')
            # or check_test(y, 'capturemock')
            or check_test(y, 'doublex')
            or check_test(y, 'aspectlib')

            # Fuzz Testing
            or check_test(y, 'hypothesis')
            or check_test(y, 'pester')
            # peach - executable only
            or check_test(y, 'antiparser')
            or check_test(y, 'taof')
            or check_test(y, 'fusil')

            # web testing tools - ignored

            # acceptance/business logic testing
            or check_test(y, 'behave')
            or check_test(y, 'fit')
            # texttext - executable only
            or check_test(y, 'lettuce')
        # FitLoader - unavailable
        # robot framework

        # gui testing toolls - ignored

    )