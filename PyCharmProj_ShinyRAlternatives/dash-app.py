import dash
import dash_bootstrap_components as dbc
import pandas as pd
from pathlib import Path
import plotly.express as px
from prophet import Prophet
from dash import Input, Output, dcc, html


dt = pd.read_csv(Path(__file__).parent / "NEED_data_explorer_2021.csv",
                  encoding="latin-1",
                  na_values="n/a")



REGIONS = ["North East",
           "North West",
           "Yorks & Humber",
           "East Midlands",
           "West Midlands",
           "East of England",
           "London",
           "South East",
           "South West",
           "Wales"]


PERIODS = ["Pre 1919",
           "1919-44",
           "1945-64",
           "1965-82",
           "1983-92",
           "1993-99",
           "Post 1999"]


GAS_DIMS = dt.filter(regex="Gas Median").columns.values.tolist()
ELEC_DIMS = dt.filter(regex="Elec Median").columns.values.tolist()



app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

controls = dbc.Card(
    [
        html.Div(
            [
                dbc.Label("Energy type:"),
                dcc.Dropdown(
                    ['Gas', 'Electricity'],
                    "Gas",
                    id="energy_type"
                ),
            ]
        ),
        html.Div(
            [
                dbc.Label("Select region:"),
                dcc.Dropdown(
                    REGIONS,
                    REGIONS[0],
                    id="region_name",
                ),
            ]
        ),
    ],
    # body=True,
)

app.layout = dbc.Container(
    [
        html.H1("Dash test app"),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col(controls, md=4),
                dbc.Col(dcc.Graph(id="ts-graph"), md=8),
            ],
            align="center",
        ),
    ],
    fluid=True,
)


@app.callback(
    Output("ts-graph", "figure"),
    [
        Input("energy_type", "value"),
        Input("region_name", "value")
    ],
)
def make_graph(energy_type, region_name):
    print(energy_type)
    print(region_name)

    dt_chunk = dt.loc[(dt["Attribute 1"] == region_name) & (dt["Attribute 2"].isin(PERIODS)), ]

    if energy_type == "Gas":
        dt_chunk = dt_chunk[["Attribute 1", "Attribute 2"] + GAS_DIMS]
    else:
        dt_chunk = dt_chunk[["Attribute 1", "Attribute 2"] + ELEC_DIMS]

    dt_chunk = pd.melt(dt_chunk, id_vars=["Attribute 1", "Attribute 2"])
    dt_chunk.variable = dt_chunk.variable.str.replace("Gas Median |Elec Median ", "", regex=True)
    dt_chunk.value = pd.to_numeric(dt_chunk.value)
    dt_chunk.variable = pd.to_numeric(dt_chunk.variable)

    # st.write(dt_chunk)

    dt_chunk["ds"] = [str(year) + "-01-01" for year in dt_chunk.variable]
    dt_chunk = dt_chunk.rename(columns={"value": "y"})

    forecast_collector = []
    for build_age in dt_chunk["Attribute 2"].unique().tolist():
        history = dt_chunk[dt_chunk["Attribute 2"] == build_age][["ds", "y"]]
        history["ds"] = pd.to_datetime(history["ds"])
        m = Prophet()
        m.fit(history)

        history = history.reset_index()
        future = pd.DataFrame([history.ds.max() + pd.offsets.DateOffset(years=2)] +
                              [history.ds.max() + pd.offsets.DateOffset(years=1)] +
                              history.ds.tolist(),
                              columns=["ds"]
                              )

        forecast = m.predict(future)
        forecast["Attribute 1"] = dt_chunk["Attribute 1"].unique()[0]
        forecast["Attribute 2"] = build_age
        forecast = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'Attribute 1', 'Attribute 2']]
        forecast_collector.append(forecast)
    forecast_collector = pd.concat(forecast_collector)

    forecast_collector['origin'] = "Predicted"
    dt_chunk["origin"] = "Observed"
    forecast_collector = forecast_collector.rename(
        columns={"yhat": "y"})  # not strictly correct, but helps with concat later

    output = pd.concat([dt_chunk, forecast_collector])
    output = output[['Attribute 1', 'Attribute 2', 'ds', 'y', 'origin']]

    fig = px.line(output,
                  x="ds",
                  y="y",
                  color_discrete_sequence=["#FDE725",
                                           "#8FD744",
                                           "#35B779",
                                           "#21908C",
                                           "#31688E",
                                           "#443A83",
                                           "#440154"],
                  color='Attribute 2',
                  line_dash='origin',
                  title="Forecasted vs actual energy usage at yearly level",
                  labels={
                      "ds": "Year",
                      "y": "Median energy usage",
                      "Attribute 2": "Building age",
                      "origin": "Source"
                  }
                  )
    fig.update_traces(line=dict(width=4))

    return fig


if __name__ == "__main__":
    app.run_server(debug=True, port=8888)
