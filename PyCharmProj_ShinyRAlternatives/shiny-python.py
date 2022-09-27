from shiny import App, reactive, render, ui
import pandas as pd
from pathlib import Path
# import plotly.express as px
from prophet import Prophet

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

app_ui = ui.page_fluid(
    ui.h2("Test app: Py Shiny"),
    ui.layout_sidebar(
        ui.panel_sidebar(
            ui.input_selectize("energy_type",
                               "Energy type:",
                               ['Gas', 'Electricity'],
                               multiple=False),
            ui.input_selectize("region_name",
                               "Region:",
                               REGIONS,
                               multiple=False)
        ),
        ui.panel_main(
            ui.output_table("linechart")
        )
    )
)


def server(input, output, session):

    @reactive.Calc
    def selectedData():

        dt_chunk = dt.loc[(dt["Attribute 1"] == input.region_name()) & (dt["Attribute 2"].isin(PERIODS)), ]

        if input.energy_type() == "Gas":
            dt_chunk = dt_chunk[["Attribute 1", "Attribute 2"] + GAS_DIMS]
        else:
            dt_chunk = dt_chunk[["Attribute 1", "Attribute 2"] + ELEC_DIMS]

        dt_chunk = pd.melt(dt_chunk, id_vars=["Attribute 1", "Attribute 2"])
        dt_chunk.variable = dt_chunk.variable.str.replace("Gas Median |Elec Median ", "", regex=True)
        dt_chunk.value = pd.to_numeric(dt_chunk.value)
        dt_chunk.variable = pd.to_numeric(dt_chunk.variable)
        return dt_chunk


    @output(id="linechart")
    # @render.plot
    @render.table
    def linechart():
        # print(f'x times 2 is: "{selectedData()}"')
        dt_chunk = selectedData()

        dt_chunk["ds"] = [str(year) + "-01-01" for year in dt_chunk.variable]
        # pd.Period('2012', 'Y')
        # dt_chunk["ds"] = pd.to_datetime(dt_chunk["ds"])
        # dt_chunk.ds = dt_chunk.ds.dt.date
        dt_chunk = dt_chunk.rename(columns={"value": "y"})

        forecast_collector = []
        for build_age in dt_chunk["Attribute 2"].unique().tolist():
            history = dt_chunk[dt_chunk["Attribute 2"] == build_age][["ds", "y"]]
            history["ds"] = pd.to_datetime(history["ds"])
            m = Prophet()
            m.fit(history)

            # future = m.make_future_dataframe(periods=2, freq="Y")  # This does not work well for yearly data

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

        # Merge forecast with OG data:
        forecast_collector['origin'] = "Predicted"
        dt_chunk["origin"] = "Observed"
        forecast_collector = forecast_collector.rename(columns={"yhat": "y"})  # not strictly correct, but helps with concat later

        output = pd.concat([dt_chunk, forecast_collector])
        output = output[['Attribute 1', 'Attribute 2', 'ds', 'y', 'origin']]

        return output

        # # Plotly no worky yet in py-shiny:
        # fig = px.line(output,
        #               x="ds",
        #               y="y",
        #               color_discrete_sequence=["#FDE725",
        #                                        "#8FD744",
        #                                        "#35B779",
        #                                        "#21908C",
        #                                        "#31688E",
        #                                        "#443A83",
        #                                        "#440154"],
        #               color='Attribute 2',
        #               line_dash='origin',
        #               title="Forecasted vs actual energy usage at yearly level",
        #               labels={
        #                   "ds": "Year",
        #                   "y": "Median energy usage",
        #                   "Attribute 2": "Building age",
        #                   "origin": "Source"
        #               }
        #               )
        # fig.update_traces(line=dict(width=4))
        # # fig.show()
        # # return fig

app = App(app_ui, server, debug=True)
