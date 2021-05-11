import os
from datetime import timedelta, date as dt, datetime as dttime
import json

import pandas as pd
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash_table import DataTable
import requests

headers = {'Accept': 'application/json', 'Accept-Language': 'hi_IN',
           'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/39.0.2171.95 Safari/537.36'}
cowin_server = 'https://cdn-api.co-vin.in/api/v2/'


def get_districts(s_id):
    district_url = f'{cowin_server}admin/location/districts/{s_id}'
    print('get districts for state ', s_id)
    response = requests.get(url=district_url, headers=headers)
    if response.status_code == 200:
        districts = json.loads(response.content)
    else:
        districts = {'districts': []}
        print('Failed: ', response)
    return districts


cols = ['Date', 'District', 'Center', 'Pincode', 'Address', 'Availability', 'Vaccine', 'Fee']
f = open('./metadata/states.json', 'r')
states = json.loads(f.read())
f.close()
districts = get_districts(1)
min_ages = {18: '18-44', 45: '45+'}

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CERULEAN])
server = app.server
app.title = "CoWIN Availability"
app.layout = html.Div(
    children=[
        html.Div(
            children=[
                html.H1(
                    children="CoWin Vaccine Availability", className="header-title"
                ),
                html.H4(
                    children="Get live data for vaccine availability in your state for a week from the "
                             "start date",
                    className="header-description",
                ),
            ],
            className="header",
        ),
        html.Br(),
        html.Div(  # style={'columnCount': 3},
            children=[html.Div(children="State", className="menu-title"),
                      dcc.Dropdown(
                          id="state-filter",
                          options=[{"label": s['state_name'], "value": s['state_id']}
                                   for s in states['states']
                                   ],
                          value=1,  # 9,
                          clearable=False,
                          className="dropdown",
                          style={'width': '55%', 'display': 'inline-block'},
                      ),
                      html.Div(children="District", className="menu-title"),
                      dcc.Dropdown(
                          id="district-filter",
                          options=[{"label": d['district_name'], "value": d['district_id']}
                                   for d in districts['districts']
                                   ],
                          value=0,
                          clearable=False,
                          className="dropdown",
                          style={'width': '55%', 'display': 'inline-block'},
                      ),
                      html.Div(children="Age", className="menu-title"),
                      dcc.Dropdown(
                          id="age-filter",
                          options=[{"label": min_ages[age], "value": age} for age in min_ages],
                          value=45,  # 18,
                          clearable=False,
                          searchable=False,
                          className="dropdown",
                          style={'width': '25%', 'display': 'inline-block'},
                      ),
                      html.Div(children="Start Date", className="menu-title"),
                      dcc.DatePickerSingle(
                          id='date-picker',
                          min_date_allowed=dt.today(),
                          max_date_allowed=dt(2021, 12, 31),
                          date=dt.today() + timedelta(days=1),
                      ),
                      ],
            className="menu",
        ),
        html.Br(),
        html.Footer(children=['Run by ', dcc.Link(children='Hiral Shah', href='https://www.linkedin.com/in/hiral-shah-11a15a104',)
                              ], style={'text-align': 'right'}
                    ),
        html.Br(),
        html.Div(
            children=[dcc.Loading(id="loading-icon",
                                  children=[html.H4(id='status'),
                                            DataTable(id='table',
                                                      sort_action="native",
                                                      sort_mode="multi",
                                                      columns=[{"name": i, "id": i} for i in cols],
                                                      page_size=10
                                                      ),
                                            ],
                                  )
                      ],
            className="wrapper",
        ),
    ], style={'marginTop': 25, 'margin-left': 25, 'margin-right': 25}
)

@app.callback(
    [Output('district-filter', 'options'),
     Output('district-filter', 'value')],
    Input('state-filter', 'value')
)
def update_districts(s_id):
    district_options = get_districts(s_id)
    return [{"label": d['district_name'], "value": d['district_id']} for d in district_options['districts']], 0


@app.callback(
    [Output('table', 'data'),
     Output('table', 'page_current'),
     Output('status', 'children')],
    [
        Input('state-filter', 'value'),
        Input('district-filter', 'value'),
        Input('age-filter', 'value'),
        Input('date-picker', 'date'),
    ],
)
def get_available_capacity(s_id, d_id, min_age, date):
    try:
        print(f'getting availability for state {s_id}, min age {min_age}, start date {date}')
        availability_df = pd.DataFrame(columns=cols)
        status = ''
        date = dt.strftime(dttime.strptime(date, "%Y-%m-%d").date(), '%d-%m-%Y')

        if d_id==0:
            districts = get_districts(s_id)
            for d in districts['districts']:
                dist_id = d['district_id']
                availability_df = get_availability(availability_df, dist_id, date, min_age)
        else:
            availability_df = get_availability(availability_df, d_id, date, min_age)
        if not len(availability_df):
            status = 'No slots available'

        return availability_df.to_dict('records'), 0, status

    except Exception as e:
        print("An error has occurred while getting the valid slots : {}".format(e))


def get_availability(availability_df, d_id, date, min_age):
    cowin_api = f'{cowin_server}appointment/sessions/public/calendarByDistrict?district_id={d_id}&date=' + date
    print('get availability for district ', d_id)
    response = requests.get(url=cowin_api, headers=headers)
    if response.status_code == 200:
        content = json.loads(response.content)
        if content['centers'] != 0:
            for c in content['centers']:
                for s in c['sessions']:
                    min_age_limit = s["min_age_limit"]
                    capacity = s["available_capacity"]
                    if int(min_age_limit) == min_age and int(capacity) > 0:
                        # print(s)
                        availability_df = availability_df.append({'Date': s['date'],
                                                                  'District': c['district_name'],
                                                                  'Center': c['name'],
                                                                  'Pincode': c['pincode'],
                                                                  'Address': c['address'],
                                                                  'Availability': capacity,
                                                                  'Vaccine': s['vaccine'],
                                                                  'Fee': c['fee_type']},
                                                                 ignore_index=True)
    else:
        print('Failed: ', response)

    return availability_df


if __name__ == '__main__':
    app.run_server(debug=True)
