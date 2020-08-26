import openai
import ast
import os
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
primer = '''[]:Jim bought 300 shares of Acme Corp. in 2006.
[("Jim", "person"), ("Acme Corp.", "organization"), ("2006", "year")]

[]:I like to drink coffee in the morning with my breakfast.
[("I", "person"), ("coffee", "drink"), ("morning", "time"), ("breakfast", "food")]

[]:Since I like dinosaurs, I think Jurassic Park is one of my favorite movies of all time.
[("I", "person"), ("dinosaurs", "animals"), ("Jurassic Park", "movie"), ("all time", "time")]

[person, company, location]:Mark Zuckerberg is one of the founders of Facebook, a company from the United States.
[("Mark Zuckerberg", "person"), ("Facebook", "company"), ("United States", "location")]

[company, location]:Amazon tells employees in New York and New Jersey
[("Amazon", "company"), ("New York", "location"), ("New Jersey", "location")]

[disease]:to work from home to prevent coronavirus spread
[("coronavirus", "disease")]

[people, company, money]:European authorities fined Google a record $5.1 billion on Wednesday for abusing its power in the
[("European authorities", "people"), ("Google", "company"), ("$5.1 billion", "money")]

[condiment, restaurant, food]:either a garlicky soy sauce or thick spicy red pepper sauce, Soban excels in all things seafood
[("soy sauce", "condiment"), ("spicy red pepper sauce", "condiment"), ("Soban", restaurant"), ("seafood", "food")]

[person, age, date]:Bannon, 66, was arrested on a yacht Thursday off the eastern
[("Bannon", "person"), ("66", "age"), ("Thursday", "date")]

[location, food]:Evan Funke runs this temple of pasta and Italian cuisine in Venice in the iconic former Joe’s space along Abbot Kinney.
[("Venice", "location"), ("Abbot Kinney", "location"), ("Joe's", "location"), ("pasta", "food")]

[food]:But the main draws are the handmade pastas: rigatoni all’amatriciana, tonnarelli cacio e pepe, and pappardelle bolognese.
[("rigatoni all’amatriciana", "food"), ("tonnarelli cacio e pepe", "food"), ("pappardelle bolognese", "food")]

[dish]:But the main draws are the handmade pastas: rigatoni all’amatriciana, tonnarelli cacio e pepe, and pappardelle bolognese.
[("rigatoni all’amatriciana", "dish"), ("tonnarelli cacio e pepe", "dish"), ("pappardelle bolognese", "dish")]

[location]:It all adds to the charm, with Greek salad, falafel, hummus, and lamb shawarma as the menu highlights.
[]

[food, person]:The neighborhood has discovered the place too, with packed tables on many nights in the rather small space.
[]

[food, person, location]:The neighborhood has discovered the place too, with packed tables on many nights in the rather small space.
[("The neighborhood", "location"), ("the place", "location")]

[person]:The neighborhood has discovered the place too, with packed tables on many nights in the rather small space.
[]

[person]:But my son matters.
[("my son", "person")]

[]:Rep.
[]

[]:Mr.
[]

[]:Dr.
[]

'''


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


def get_ner(text, temp, labels):
    # split text by sentences to process long text w/o errors
    text = text.replace('“', '').replace('”', '').replace('"', '')
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


def display_output_tab():
    content = dbc.Card(
        dbc.CardBody(
            [
                html.Br(),
                dash_table.DataTable(
                    id='output-table',
                    columns=[{"name": i, "id": i} for i in ner_table.columns],
                    data=ner_table.to_dict('records'),
                    editable=True,
                    export_format='csv',
                    export_headers="display",
                    row_deletable=True
                )
            ]
        ),
        className="mt-3",
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
        className="mt-3",
    )
    return content


@app.callback(
    Output("extract-output", "children"),
    [Input("extract-btn", "n_clicks")],
    [State("textarea", "value"), State("temp-slider", "value"), State("label-input", "value")]
)
def extract_button(n_clicks, text, temp, labels):
    global ner_table
    if n_clicks is None:
        return "Not clicked."
    else:
        print(n_clicks)
        print(text)
        print(temp)
        try:
            if labels is None:
                labels = ''
            ner_table = get_ner(text, temp, labels)
            if labels != '':
                labels = labels.replace(', ', ',').split(',')
                ner_table = ner_table[ner_table['tags'].isin(labels)]
            return [
                dbc.Tabs(
                    [
                        dbc.Tab(label="Output", tab_id='tab-1'),
                        dbc.Tab(label="Analysis", tab_id='tab-2'),
                    ],
                    id='tabs',
                    active_tab="tab-1"
                ),
                html.Div(id="content"),
            ]
        except Exception as e:
            print(e)
            return html.Div("There was an error handling your request. Please try again.")


@app.callback(
    Output('temp-output', 'children'),
    [Input('temp-slider', 'value')])
def update_slider(value):
    return html.H3('Temperature: {}'.format(value))


@app.callback(Output("content", "children"), [Input("tabs", "active_tab")])
def switch_tab(tab_id):
    if tab_id == "tab-1":
        return display_output_tab()
    elif tab_id == "tab-2":
        return display_analysis_tab()
    return html.P("This shouldn't ever be displayed...")


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
                    html.H3("Text"),
                    dbc.Textarea(
                        id='textarea',
                        placeholder='Input your text for NER',
                        style={'width': '100%', 'height': 300},
                    ),
                    html.Br(),
                    html.Div(id='temp-output'),
                    dcc.Slider(
                        id='temp-slider',
                        min=0,
                        max=1,
                        step=0.05,
                        value=0.5,
                    ),
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
                dbc.Spinner(
                    html.Div(id='extract-output'),
                    spinner_style={"width": "3rem", "height": "3rem"}
                ),
                width=6
            )
        ]),
    ],
    style={"margin-left": "5%", "margin-right": "5%", "margin-top": "5%", "margin-bottom": "5%"}
)


if __name__ == '__main__':
    application.run(debug=True, host='0.0.0.0', port='80')
