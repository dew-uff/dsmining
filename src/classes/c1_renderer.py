import mistune

# Map based on stopwords.fileids() and !ls $langdetect.PROFILES_DIRECTORY
LANG_MAP = {
    'ar': 'arabic',
    'az': 'azerbaijani',
    'da': 'danish',
    'nl': 'dutch',
    'en': 'english',
    'fi': 'finnish',
    'fr': 'french',
    'de': 'german',
    'el': 'greek',
    'hu': 'hungarian',
    'id': 'indonesian',
    'it': 'italian',
    'kk': 'kazakh',
    'ne': 'nepali',
    'no': 'norwegian',
    'pt': 'portuguese',
    'ro': 'romanian',
    'ru': 'russian',
    'es': 'spanish',
    'sv': 'swedish',
    'tr': 'turkish',
}


class CountRenderer(mistune.Renderer):

    def __init__(self, language, stopwords, using_stopwords):
        super(CountRenderer, self).__init__()
        self.stopwords = stopwords
        self.counter = {
            'language': language,
            'using_stopwords': using_stopwords,
            'len': 0,
            'lines': 0,
            'meaningful_lines': 0,
            'words': 0,
            'meaningful_words': 0,
            'stopwords': 0,
            'meaningful_stopwords': 0,

            'header': 0,
            'header_len': 0,
            'header_lines': 0,
            'header_words': 0,
            'header_stopwords': 0,

            'h1': 0,
            'h1_len': 0,
            'h1_lines': 0,
            'h1_words': 0,
            'h1_stopwords': 0,

            'h2': 0,
            'h2_len': 0,
            'h2_lines': 0,
            'h2_words': 0,
            'h2_stopwords': 0,

            'h3': 0,
            'h3_len': 0,
            'h3_lines': 0,
            'h3_words': 0,
            'h3_stopwords': 0,

            'h4': 0,
            'h4_len': 0,
            'h4_lines': 0,
            'h4_words': 0,
            'h4_stopwords': 0,

            'h5': 0,
            'h5_len': 0,
            'h5_lines': 0,
            'h5_words': 0,
            'h5_stopwords': 0,

            'h6': 0,
            'h6_len': 0,
            'h6_lines': 0,
            'h6_words': 0,
            'h6_stopwords': 0,

            'hrule': 0,

            'list': 0,
            'list_len': 0,
            'list_lines': 0,
            'list_items': 0,
            'list_words': 0,
            'list_stopwords': 0,

            'table': 0,
            'table_len': 0,
            'table_lines': 0,
            'table_rows': 0,
            'table_cells': 0,
            'table_words': 0,
            'table_stopwords': 0,

            'p': 0,
            'p_len': 0,
            'p_lines': 0,
            'p_words': 0,
            'p_stopwords': 0,

            'quote': 0,
            'quote_len': 0,
            'quote_lines': 0,
            'quote_words': 0,
            'quote_stopwords': 0,

            'code': 0,
            'code_len': 0,
            'code_lines': 0,
            'code_words': 0,
            'code_stopwords': 0,

            'image': 0,
            'image_len': 0,
            'image_words': 0,
            'image_stopwords': 0,

            'link': 0,
            'link_len': 0,
            'link_words': 0,
            'link_stopwords': 0,

            'autolink': 0,
            'autolink_len': 0,
            'autolink_words': 0,
            'autolink_stopwords': 0,

            'codespan': 0,
            'codespan_len': 0,
            'codespan_words': 0,
            'codespan_stopwords': 0,

            'emphasis': 0,
            'emphasis_len': 0,
            'emphasis_words': 0,
            'emphasis_stopwords': 0,

            'double_emphasis': 0,
            'double_emphasis_len': 0,
            'double_emphasis_words': 0,
            'double_emphasis_stopwords': 0,

            'strikethrough': 0,
            'strikethrough_len': 0,
            'strikethrough_words': 0,
            'strikethrough_stopwords': 0,

            'html': 0,
            'html_len': 0,
            'html_lines': 0,

            'math': 0,
            'math_len': 0,
            'math_words': 0,
            'math_stopwords': 0,

            'block_math': 0,
            'block_math_len': 0,
            'block_math_lines': 0,
            'block_math_words': 0,
            'block_math_stopwords': 0,

            'latex': 0,
            'latex_len': 0,
            'latex_lines': 0,
            'latex_words': 0,
            'latex_stopwords': 0,
        }

    def count_lines(self, category, value):
        counter = self.counter
        stopwords = self.stopwords
        counter[category] += 1
        words = value.split()
        #print(words)
        len_words = len(words)
        len_stopwords = sum(1 for word in words if word in stopwords)
        counter['meaningful_words'] += len_words
        counter['meaningful_stopwords'] += len_stopwords
        counter[category + '_words'] += len_words
        counter[category + '_stopwords'] += len_stopwords
        counter[category + '_len'] += len(value)
        counter[category + '_lines'] += len(value.split('\n'))

    def count_span(self, category, value):
        counter = self.counter
        stopwords = self.stopwords
        counter[category] += 1
        words = value.split()
        len_words = len(words)
        len_stopwords = sum(1 for word in words if word in stopwords)
        counter[category + '_words'] += len_words
        counter[category + '_stopwords'] += len_stopwords
        counter[category + '_len'] += len(value)

    def count_1(self, category, value):
        counter = self.counter
        counter[category] += 1
        counter[category + '_len'] += len(value)

    def block_code(self, code, language=None):
        self.count_lines('code', code)
        return code

    def block_quote(self, text):
        self.count_lines('quote', text)
        return text

    def block_html(self, text):
        self.count_1('html', text)
        self.counter['html_lines'] += len(text.split('\n'))
        return text

    def header(self, text, level, raw=None):
        self.count_span('header', text)
        self.count_lines('h{}'.format(level), text)
        self.counter['header_lines'] += len(text.split('\n'))
        return text

    def hrule(self):
        self.counter['hrule'] += 1
        return '---'

    def list(self, body, ordered=True):
        self.count_lines('list', body)
        return body

    def list_item(self, content):
        self.counter['list_items'] += 1
        return content + '\n'

    def paragraph(self, text):
        self.count_lines('p', text)
        return text

    def table(self, header, body):
        self.count_lines('table', header + body)
        return header + body

    def table_row(self, content):
        self.counter['table_rows'] += 1
        return content + '\n'

    def table_cell(self, content, **flags):
        self.counter['table_cells'] += 1
        return content + ' '

    def autolink(self, link, is_email=False):
        self.count_1('autolink', link)
        self.counter['autolink_words'] += 1
        return 'L' * len(link)

    def codespan(self, text):
        self.count_span('codespan', text)
        return text

    def double_emphasis(self, text):
        self.count_span('double_emphasis', text)
        return text

    def emphasis(self, text):
        self.count_span('emphasis', text)
        return text

    def image(self, src, title, alt_text):
        self.count_1('image', src)
        self.count_span('image', title or '')
        self.count_span('image', alt_text or '')
        self.counter['image'] -= 2
        self.counter['image_words'] += 1
        return 'S' * len(src) + 'T' * len(title or '') + 'A' * len(alt_text or '')

    # linebreak
    # newline

    def link(self, link, title, content):
        self.count_1('link', link)
        self.count_span('link', title or '')
        self.count_span('link', content or '')
        self.counter['link'] -= 2
        self.counter['link_words'] += 1
        return 'L' * len(link) + 'T' * len(title or '') + 'C' * len(content or '')

    def strikethrough(self, text):
        self.count_span('strikethrough', text)
        return text

    # text

    def inline_html(self, text):
        self.count_1('html', text)
        return 'A' * len(text)

    def block_math(self, text):
        self.count_lines('block_math', text or '')
        return text

    def latex_environment(self, name, text):
        self.count_lines('latex', text or '')
        self.count_span('latex', name or '')
        self.counter['latex'] -= 1
        return text

    def inline_math(self, text):
        self.count_span('math', text or '')
        return text