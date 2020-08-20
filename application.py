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
from dash.dependencies import Input, Output, State

load_dotenv(dotenv_path=Path("..") / ".env")
openai.api_key = os.getenv("API-KEY")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.COSMO])
application = app.server
app.scripts.config.serve_locally = True
app.css.config.serve_locally = True
app.config["suppress_callback_exceptions"] = True

ner_table = pd.DataFrame(columns=['values', 'tags'])
primer = '''Jim bought 300 shares of Acme Corp. in 2006.
[("Jim", "person"), ("Acme Corp.", "organization"), ("2006", "year")]

I like to drink coffee in the
[("I", "person"), ("coffee", "drink")]

morning with my breakfast.
[("morning", "time"), ("breakfast", "food")]

Since I like dinosaurs, I think Jurassic Park is one of my favorite movies of all time.
[("I", "person"), ("dinosaurs", "animals"), ("Jurassic Park", "movie"), ("all time", "time")]

Mark Zuckerberg is one of the founders of Facebook, a company from the United States.
[("Mark Zuckerberg", "person"), ("Facebook", "company"), ("United States", "location")]

Amazon tells employees in New York and New Jersey
[("Amazon", "company"), ("New York", "location"), ("New Jersey", "location")]

to work from home to prevent coronavirus spread
[("coronavirus", "disease")]

European authorities fined Google a record $5.1 billion on Wednesday for abusing its power in the
[("European authorities", "people"), ("Google", "company"), ("$5.1 billion", "money")]

either a garlicky soy sauce or thick spicy red pepper sauce, Soban excels in all things seafood
[("soy sauce", "condiment"), ("spicy red pepper sauce", "condiment"), ("Soban", restaurant"), ("seafood", "food")]

Bannon, 66, was arrested on a yacht Thursday off the eastern
[("Bannon", "person"), ("66", "age"), ("Thursday", "date")]

'''


def get_response(sentence, temp):
    response = openai.Completion.create(
      engine="davinci",
      prompt=primer + sentence,
      max_tokens=256,
      temperature=temp,
      stop="]"
    )
    string = response['choices'][0]['text'].strip() + ']'
    pairs = ast.literal_eval(string)
    return pairs


def get_ner(text, temp):
    # split text by sentences to process long text w/o errors
    sentences = text.split(". ")
    pairs = []
    for sentence in sentences:
        print(sentence + '.')
        result = get_response(sentence + '.', temp)
        print(result)
        pairs.extend(result)

    df = pd.DataFrame(columns=['values', 'tags'])
    df['values'] = [x for (x, y) in pairs]
    df['tags'] = [y for (x, y) in pairs]
    print(df)
    return df


@app.callback(
    Output("output", "children"),
    [Input("extract-btn", "n_clicks")],
    [State("textarea", "value"), State("temp-slider", "value")]
)
def on_button_click(n_clicks, text, temp):
    global ner_table
    if n_clicks is None:
        return "Not clicked."
    else:
        print(n_clicks)
        print(text)
        print(temp)
        try:
            ner_table = get_ner(text, temp)
            return dash_table.DataTable(
                id='live-table',
                columns=[{"name": i, "id": i} for i in ner_table.columns],
                data=ner_table.to_dict('records'),
                editable=True,
                export_format='csv',
                export_headers="display",
                row_deletable=True
            ),
        except Exception as e:
            print(e)
            return html.Div("There was an error handling your request. Please try again.")


@app.callback(
    Output('temp-output', 'children'),
    [Input('temp-slider', 'value')])
def update_output(value):
    return 'Temperature: {}'.format(value)


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
                    dbc.Textarea(
                        id='textarea',
                        value='Input your text for NER.',
                        style={'width': '100%', 'height': 300},
                    ),
                    html.Div(id='temp-output'),
                    dcc.Slider(
                        id='temp-slider',
                        min=0,
                        max=1,
                        step=0.05,
                        value=0.5,
                    ),
                    dbc.Button("Extract", id="extract-btn", color="primary", className="mr-1"),
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
                    html.Div(id='output'),
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
