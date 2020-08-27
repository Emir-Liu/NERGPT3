import openai
import ast
import os
import base64
import io
import pandas as pd
from dotenv import load_dotenv
from pathlib2 import Path
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.express as px
from dash.dependencies import Input, Output, State

load_dotenv(dotenv_path=Path("..") / ".env")
openai.api_key = os.getenv("API-KEY")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.COSMO])
application = app.server
app.scripts.config.serve_locally = True
app.css.config.serve_locally = True
app.config["suppress_callback_exceptions"] = True

ner_table = pd.DataFrame(columns=['values', 'tags'])
upload_text = pd.DataFrame()
upload_tab = True
upload_column = ''
textarea_string = ''
primer = open('primer.txt').read()


def get_response(input_text, temp):
    response = openai.Completion.create(
      engine="davinci",
      prompt=primer + input_text,
      max_tokens=256,
      temperature=temp,
      stop="]"
    )
    string = response['choices'][0]['text'].strip() + ']'
    print(string)
    pairs = ast.literal_eval(string)
    return pairs


def get_ner(temp, labels):
    # split text by sentences to process long text w/o errors
    if upload_tab:
        sentences = upload_text[upload_column]
    else:
        text = textarea_string.replace('“', '').replace('”', '').replace('"', '')
        sentences = text.split(". ")
    pairs = []
    for sentence in sentences:
        input_text = '[' + labels + ']:' + sentence + '.'
        print('\n' + input_text)
        result = get_response(input_text, temp)
        pairs.extend(result)

    df = pd.DataFrame(columns=['values', 'tags'])
    df['values'] = [x for (x, y) in pairs]
    df['tags'] = [y for (x, y) in pairs]
    print(df)
    return df


def parse_contents(contents, filename):
    global upload_text
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            upload_text = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            upload_text = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file. Please upload a CSV or Excel file.'
        ])

    return html.Div([
        html.H5(filename),
        dcc.Dropdown(
            id='column-dropdown',
            options=[{"label": i, "value": i} for i in list(upload_text)],
            placeholder="Please select a column for tagging"
        ),
        html.Div(
            dash_table.DataTable(
                data=upload_text.to_dict('records'),
                columns=[{'name': i, 'id': i} for i in upload_text.columns],
                page_action='none',
                style_table={'height': '300px', 'overflowY': 'auto', 'overflowX': 'auto'},
                css=[{'selector': '.row', 'rule': 'margin: 0'}]
            )
        ),
    ])


def display_input_tab():
    content = dbc.Card(
        dbc.CardBody(
            [
                dbc.Textarea(
                    id='textarea',
                    placeholder='Input your text for NER',
                    style={'width': '100%', 'height': 300},
                ),
            ]
        ),
        className="card border-primary mb-3",
    )
    return content


def display_upload_tab():
    content = dbc.Card(
        dbc.CardBody(
            [
                dcc.Upload(
                    id='upload-data',
                    children=html.Div([
                        'Drag and Drop or ',
                        html.A('Select File')
                    ]),
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px'
                    },
                    multiple=False
                ),
                html.Div(id='output-data-upload'),
            ]
        ),
        className="card border-primary mb-3",
    )
    return content


def display_output_tab():
    if ner_table.empty:
        out = dbc.Alert("No tags found! Please adjust temperature and try again.", color="danger")
    else:
        out = dash_table.DataTable(
                    id='output-table',
                    columns=[{"name": i, "id": i} for i in ner_table.columns],
                    data=ner_table.to_dict('records'),
                    editable=True,
                    export_format='csv',
                    export_headers="display",
                    row_deletable=True,
                    css=[{'selector': '.row', 'rule': 'margin: 0'}],
                    style_table={'height': '600px', 'overflowY': 'auto', 'overflowX': 'auto'},
                )
    content = dbc.Card(
        dbc.CardBody([html.Br(), out]),
        className="card border-primary mb-3",
    )
    return content


def display_analysis_tab():
    fig = px.histogram(ner_table, x="tags")
    content = dbc.Card(
        dbc.CardBody(
            [
                html.Br(),
                dcc.Graph(figure=fig),
            ]
        ),
        className="card border-primary mb-3",
    )
    return content


@app.callback(
    Output("extract-output", "children"),
    [Input("extract-btn", "n_clicks")],
    [State("temp-slider", "value"), State("label-input", "value")]
)
def extract_button(n_clicks, temp, labels):
    global ner_table
    if n_clicks is None:
        return "Please input text or upload file to begin."
    else:
        print(n_clicks)
        print(temp)
        print(labels)
        try:
            if labels is None:
                labels = ''
            ner_table = get_ner(temp, labels)
            if labels != '':
                labels = labels.replace(', ', ',').split(',')
                ner_table = ner_table[ner_table['tags'].isin(labels)]
            return [
                dbc.Tabs(
                    [
                        dbc.Tab(label="Output", tab_id='tab-1'),
                        dbc.Tab(label="Analysis", tab_id='tab-2'),
                    ],
                    id='output-tabs',
                    active_tab="tab-1"
                ),
                html.Div(id="output-content"),
            ]
        except Exception as e:
            print(e)
            return html.Div("There was an error handling your request. Please try again.")


@app.callback(
    Output('temp-output', 'children'),
    [Input('temp-slider', 'value')])
def update_slider(value):
    return html.H3('Temperature: {}'.format(value))


@app.callback(
    Output('textarea-output', 'children'),
    [Input('textarea', 'value')])
def update_textarea(value):
    global textarea_string
    textarea_string = value
    print(textarea_string)


@app.callback(
    Output('dropdown-output', 'children'),
    [Input('column-dropdown', 'value')])
def update_dropdown(value):
    global upload_column
    upload_column = value


@app.callback(Output('output-data-upload', 'children'),
              [Input('upload-data', 'contents')],
              [State('upload-data', 'filename')])
def upload_data_output(content, filename):
    if content is not None:
        children = parse_contents(content, filename)
        return children


@app.callback(Output("input-content", "children"), [Input("input-tabs", "active_tab")])
def switch_input_tab(tab_id):
    global upload_tab
    print(tab_id)
    if tab_id == "tab-0":
        upload_tab = False
        return display_input_tab()
    elif tab_id == "tab-1":
        upload_tab = True
        return display_upload_tab()


@app.callback(Output("output-content", "children"), [Input("output-tabs", "active_tab")])
def switch_output_tab(tab_id):
    if tab_id == "tab-1":
        return display_output_tab()
    elif tab_id == "tab-2":
        return display_analysis_tab()


@app.callback(
    Output("output-table", "children"),
    [Input("output-table", "data_previous")],
    [State("output-table", "data")],
)
def update_anomaly_table(prev, curr):
    if prev is None:
        dash.exceptions.PreventUpdate()
    else:
        removed = list(
            set([i["values"] for i in prev])
            - set([i["values"] for i in curr])
        )[0]
        global ner_table
        ner_table = ner_table[ner_table['values'] != removed]


app.layout = html.Div(
    children=[
        html.H1("Named Entity Recognition"),
        html.Div("Extract entities from text using named entity recognition (NER). NER labels sequences of words in a "
                 "text which are the names of things, such as person and company names."),
        html.Div("Temperature controls randomness. Lowering results in less random completions. As temperature "
                 "approaches zero, the model will become deterministic and repetitive. Given the task, we do not want "
                 "a very \"creative\" model, as this creates issues in the output. A temperature of around 0.5 works "
                 "decently well. Feel free to experiment!"),
        html.Hr(),
        dbc.Row(children=[
            dbc.Col(
                children=[
                    html.Br(),
                    html.H3("Tags"),
                    dbc.Input(id="label-input",
                              placeholder="Separate w/ commas, leave blank for automatic label generation",
                              type="text"),
                    html.Br(),
                    html.Div(id='temp-output'),
                    dcc.Slider(
                        id='temp-slider',
                        min=0,
                        max=1,
                        step=0.05,
                        value=0.5,
                    ),
                    html.H3("Text"),
                    dbc.Tabs(
                        [
                            dbc.Tab(label="Input", id="tab-0"),
                            dbc.Tab(label="Upload", id="tab-1"),
                        ],
                        id="input-tabs",
                        active_tab="tab-0"
                    ),
                    html.Div(id='input-content'),
                    html.Br(),
                    dbc.Button("EXTRACT", id="extract-btn", block=True, color="primary", className="mr-1"),
                    html.Br(),
                    html.Img(
                        src="https://cdn.openai.com/API/logo-assets/powered-by-openai-dark.png",
                        width=260,
                        height=28
                    ),
                ],
                width=6
            ),
            dbc.Col(
                [
                    html.Br(),
                    dbc.Spinner(
                        html.Div(id='extract-output'),
                        spinner_style={"width": "3rem", "height": "3rem"}
                    )
                ],
                width=6
            )
        ]),
        html.Div(id="dropdown-output", style={"display": "none"}),
        html.Div(id="textarea-output", style={"display": "none"}),
    ],
    style={"margin-left": "5%", "margin-right": "5%", "margin-top": "5%", "margin-bottom": "5%"}
)


if __name__ == '__main__':
    application.run(debug=True, host='0.0.0.0', port='80')
