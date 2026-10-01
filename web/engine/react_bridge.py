"""Browser presentation adapter. Financial modules are bundled byte-for-byte.

No Streamlit server, no credentials, no remote Python execution. This adapter
only produces a declarative tree for React and a list of intended mutations.
Those mutations must be confirmed by the authenticated data transport before
the next rendered result is shown. Unknown APIs fail explicitly.
"""
import base64
import copy
import datetime
import io
import json
import sys
import types
import uuid
from decimal import Decimal


class ControlFlow(BaseException):
    pass


class State(dict):
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


state = State()
tree = []
stack = [tree]
contexts = ['root']
event = None
mutations = []
tables = {}
counts = {}
user = None
document_texts = {}


def inspect_document(request):
    from pypdf import PdfReader
    from sanitarie_documenti import suggerisci_importo
    data = base64.b64decode(request['base64'])
    if not data or len(data) > 8 * 1024 * 1024:
        raise ValueError('Documento vuoto o oltre 8 MB.')
    reader = PdfReader(io.BytesIO(data), strict=False)
    limit = 3 if request.get('medical') else 4
    if reader.is_encrypted or not 1 <= len(reader.pages) <= limit:
        raise ValueError(f'PDF protetto o con più di {limit} pagine.')
    text = '\n'.join(page.extract_text() or '' for page in reader.pages)
    needs_ocr = suggerisci_importo(text) is None if request.get('medical') else not text.strip()
    return {'text':text, 'pages':len(reader.pages), 'needs_ocr':bool(needs_ocr)}


def clear_session():
    global document_texts, tables, user, mutations, tree
    state.clear()
    document_texts = {}
    tables = {}
    user = None
    mutations = []
    tree = []
    return {}


def register_document_texts(inputs):
    """Replace only local document readers; original amount parsers remain intact."""
    from hashlib import sha256
    global document_texts
    document_texts = {}
    def visit(value):
        if isinstance(value, dict):
            if 'base64' in value and ('document_text' in value or 'document_error' in value):
                document_texts[sha256(base64.b64decode(value['base64'])).hexdigest()] = value
            else:
                for child in value.values():
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(inputs)
    def text_for(data):
        value = document_texts.get(sha256(data).hexdigest())
        if value is None:
            raise ValueError('Documento non preparato: selezionalo nuovamente.')
        if value.get('document_error'):
            raise ValueError(value['document_error'])
        return value['document_text']
    import fatture_provvigioni as invoices
    import sanitarie_documenti as medical
    if not hasattr(invoices, '_browser_original_analyze'):
        invoices._browser_original_analyze = invoices.analizza_fattura
    def analyze(name, data):
        if name.lower().endswith('.xml'):
            return invoices._browser_original_analyze(name, data)
        if not data or len(data) > invoices.MAX_BYTES:
            raise ValueError('File vuoto o superiore a 8 MB.')
        if name.lower().rsplit('.',1)[-1] not in ('pdf','png','jpg','jpeg'):
            raise ValueError('Formato non supportato: PDF, XML, JPG o PNG.')
        return (*invoices.suggerisci_netto(text_for(data)), '')
    invoices.analizza_fattura = analyze
    medical._leggi_documento = lambda name, data: text_for(data)


def encode(value):
    if isinstance(value, (Decimal, datetime.date, datetime.datetime)):
        return str(value)
    if isinstance(value, bytes):
        return {'base64': base64.b64encode(value).decode()}
    if hasattr(value, 'records'):
        return value.records
    raise TypeError(f'Unsupported presentation value: {type(value).__name__}')


class Frame:
    def __init__(self, node=None, context=None):
        self.node = node
        self.context = context or (node or {}).get('id', 'root')
        self.open = True

    def __enter__(self):
        stack.append(self.node['children'] if self.node is not None else tree)
        contexts.append(self.context)
        return self

    def __exit__(self, *args):
        stack.pop()
        contexts.pop()

    def __getattr__(self, name):
        def call(*args, **kwargs):
            with self:
                return getattr(st, name)(*args, **kwargs)
        return call


def node(kind, label=None, **props):
    ident = f'{contexts[-1]}:{kind}:{label}'
    counts[ident] = counts.get(ident, 0) + 1
    result = {'kind': kind, 'id': f'{ident}:{counts[ident]}', 'label': label,
              **props, 'children': []}
    stack[-1].append(result)
    return result


def display(kind):
    def call(value='', *args, **kwargs):
        return node(kind, str(value), value=value)
    return call


def widget(kind):
    def call(label, *args, key=None, value=None, options=None, index=0, **kwargs):
        if kind in ('selectbox', 'radio'):
            opts = list(options if options is not None else (args[0] if args else []))
            default = opts[index] if opts and index is not None else None
        else:
            opts = None
            default = value if value is not None else (False if kind == 'checkbox' else '' if kind in ('text_input','file_uploader') else 0)
        ident = str(key) if key is not None else f'{contexts[-1]}:{kind}:{label}'
        if ident not in state:
            state[ident] = default
        current = state[ident]
        if opts is not None and current not in opts:
            current = default
            state[ident] = default
        formatter = kwargs.get('format_func', str)
        props = {k: v for k, v in kwargs.items() if k in ('disabled','help','placeholder','min_value','max_value','step','type','accept_multiple_files')}
        node(kind, label, key=ident, value=current, options=opts,
             option_labels=[str(formatter(v)) for v in opts] if opts is not None else None, **props)
        if kind == 'date_input' and isinstance(current, str):
            return datetime.date.fromisoformat(current)
        if kind == 'file_uploader':
            if not current:
                return [] if kwargs.get('accept_multiple_files') else None
            def file(v):
                result = io.BytesIO(base64.b64decode(v['base64']))
                result.name = v['name']
                result.size = len(result.getvalue())
                return result
            return [file(v) for v in current] if isinstance(current, list) else file(current)
        return current
    return call


def button(label, *args, key=None, disabled=False, **kwargs):
    ident = str(key) if key is not None else f'{contexts[-1]}:button:{label}'
    node('button', label, key=ident, disabled=disabled)
    return event == ident and not disabled


def group(kind):
    def call(label='', *args, **kwargs):
        return Frame(node(kind, str(label)), f'{contexts[-1]}/{kind}:{label}')
    return call


def tabs(labels, key=None, **kwargs):
    selected = state.get(key or 'tabs', labels[0])
    frames = []
    node('tabs', key=key or 'tabs', options=list(labels), value=selected)
    for label in labels:
        frame = Frame(node('tab', label, hidden=selected != label), f'tab:{label}')
        frame.open = selected == label
        frames.append(frame)
    return frames


def columns(spec, **kwargs):
    count = spec if isinstance(spec, int) else len(spec)
    frame = Frame(node('columns'))
    with frame:
        return [Frame(node('column', str(i))) for i in range(count)]


def dataframe(data, **kwargs):
    return node('table', records=data.records if hasattr(data, 'records') else data)


def metric(label, value, *args, **kwargs):
    return node('metric', label, value=value)


def download_button(label, data, file_name='download.csv', mime='text/csv', **kwargs):
    node('download', label, data=data.encode() if isinstance(data, str) else data,
         file_name=file_name, mime=mime)
    return False


st = types.ModuleType('streamlit')
st.session_state = state
for name in ('title','subheader','caption','info','error','warning','success','write','markdown','code'):
    setattr(st, name, display(name))
for name in ('text_input','number_input','date_input','checkbox','selectbox','radio','file_uploader'):
    setattr(st, name, widget(name))
for name in ('form','expander','container','spinner','popover'):
    setattr(st, name, group(name))
st.button = st.form_submit_button = button
st.tabs = tabs
st.columns = columns
st.dataframe = st.table = dataframe
st.metric = metric
st.download_button = download_button
st.link_button = lambda label, url, **kw: node('link', label, url=url)
st.empty = lambda: Frame(node('placeholder'))
st.divider = lambda: node('divider')
st.set_page_config = lambda **kw: None
st.rerun = st.stop = lambda: (_ for _ in ()).throw(ControlFlow())
st.sidebar = Frame({'children': []}, 'sidebar')
sys.modules['streamlit'] = st

# The original sidebar uses only DataFrame(...).set_index(...), with no
# numerical pandas operations. Keep that presentation operation lightweight.
class DataFrame:
    def __init__(self, records, **kwargs):
        self.records = records
    def set_index(self, name):
        return self
pandas = types.ModuleType('pandas')
pandas.DataFrame = DataFrame
sys.modules['pandas'] = pandas


class Query:
    def __init__(self, table):
        self.table = table
        self.filters = []
        self.operation = 'select'
        self.payload = None
        self.fields = '*'
        self.start = 0
        self.end = None
        self.sort = None
    def select(self, fields='*', **kwargs):
        self.fields = fields
        return self
    def eq(self, name, value):
        self.filters.append([name, value])
        return self
    def order(self, name, desc=False):
        self.sort = (name, desc)
        return self
    def limit(self, value):
        self.end = value
        return self
    def range(self, start, end):
        self.start, self.end = start, end + 1
        return self
    def insert(self, payload):
        self.operation, self.payload = 'insert', payload
        return self
    def update(self, payload):
        self.operation, self.payload = 'update', payload
        return self
    def delete(self):
        self.operation = 'delete'
        return self
    def execute(self):
        if self.table not in tables:
            raise ValueError(f'Table not available: {self.table}')
        rows = tables[self.table]
        matching = [r for r in rows if all(str(r.get(k)) == str(v) for k,v in self.filters)]
        if self.operation != 'select':
            planned = {'table': self.table, 'operation': self.operation,
                       'payload': copy.deepcopy(self.payload), 'filters': copy.deepcopy(self.filters)}
            mutations.append(planned)
            if self.operation == 'insert':
                incoming = self.payload if isinstance(self.payload,list) else [self.payload]
                matching = [{'id':str(uuid.uuid4()),'user_id':user['id'],**r} for r in incoming]
                rows.extend(matching)
            elif self.operation == 'update':
                for row in matching:
                    row.update(self.payload)
            elif self.operation == 'delete':
                tables[self.table] = [r for r in rows if r not in matching]
            planned['result_ids'] = [r['id'] for r in matching]
            planned['expected_rows'] = len(matching)
        if self.sort:
            matching.sort(key=lambda r: str(r.get(self.sort[0], '')), reverse=self.sort[1])
        total = len(matching)
        result = matching[self.start:self.end]
        if self.fields != '*':
            result = [{k:r.get(k) for k in self.fields.split(',')} for r in result]
        return types.SimpleNamespace(data=copy.deepcopy(result), count=total)


class Client:
    def table(self, name):
        return Query(name)


supabase = types.ModuleType('supabase')
supabase.Client = Client
sys.modules['supabase'] = supabase
auth = types.ModuleType('auth')
auth.get_client = lambda: Client()
auth.current_user = lambda: types.SimpleNamespace(**user) if user else None
auth.sign_in = lambda *a: None
auth.sign_out = lambda: None
def reset_inputs():
    for key in list(state):
        if key != 'anno_fiscale_selezionato':
            del state[key]
auth.reset_fiscal_inputs = reset_inputs
sys.modules['auth'] = auth
style = types.ModuleType('stile')
style.applica_stile = lambda: None
sys.modules['stile'] = style


def render(request):
    global tree, stack, contexts, event, mutations, tables, counts, user
    tables = copy.deepcopy(request['tables'])
    next_user = request.get('user')
    if (user or {}).get('id') != (next_user or {}).get('id'):
        state.clear()
    user = next_user
    event = request.get('event')
    inputs = request.get('inputs', {})
    if 'anno_fiscale_selezionato' in inputs and inputs['anno_fiscale_selezionato'] != state.get('anno_fiscale_selezionato'):
        reset_inputs()
    state.update(inputs)
    register_document_texts(inputs)
    counts = {}
    mutations = []
    tree = []
    stack = [tree]
    contexts = ['root']
    st.sidebar.node['children'] = []
    try:
        with open('/app/app.py', encoding='utf-8') as source:
            exec(compile(source.read(), 'app.py', 'exec'), {'__name__':'__react_app__'})
    except ControlFlow:
        pass
    def visible_keys(nodes):
        for item in nodes:
            if 'key' in item and item['kind'] != 'button':
                yield item['key']
            yield from visible_keys(item['children'])
    keys=set(visible_keys(tree + st.sidebar.node['children']))
    return json.dumps({'tree':tree,'sidebar':st.sidebar.node['children'],
                       'inputs':{k:state[k] for k in keys if k in state},
                       'mutations':mutations, 'tables':tables}, default=encode)
