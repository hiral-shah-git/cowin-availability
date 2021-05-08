from datetime import timedelta, date as dt, datetime as dttime
import json

import pandas as pd
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash_table import DataTable
import requests
from app import app

headers = {'Accept': 'application/json', 'Accept-Language': 'hi_IN',
           'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/50.0.2661.102 Safari/537.36'}
cowin_server = 'https://cdn-api.co-vin.in/api/v2/'

cols = ['Date', 'District', 'Center', 'Pincode', 'Address', 'Availability', 'Vaccine', 'Fee']

f = open('./metadata/states.json', 'r')
states = json.loads(f.read())
f.close()
min_ages = [18, 45]

app.layout = html.Div(
        children=[
            html.Div(
                children=[
                    html.H1(
                        children="CoWin Vaccine Availability", className="header-title"
                    ),
                    html.H4(
                        children="Get complete overview of vaccine availability in your state for a week from the start date",
                        className="header-description",
                    ),
                ],
                className="header",
            ),
            html.Div(
                children=[
                    html.Div(
                        children=[
                            html.Div(children="State", className="menu-title"),
                            dcc.Dropdown(
                                id="state-filter",
                                options=[
                                    {"label": s['state_name'], "value": s['state_id']}
                                    for s in states['states']
                                ],
                                value=1,  # 9,
                                clearable=False,
                                className="dropdown",
                                style={'width': '50%', 'display': 'inline-block'},
                            ),
                            #     ]
                            # ),
                            # html.Div(
                            #     children=[
                            html.Div(children="Min. age", className="menu-title"),
                            dcc.Dropdown(
                                id="age-filter",
                                options=[{"label": age, "value": age}
                                         for age in min_ages
                                         ],
                                value=45,  # 18,
                                clearable=False,
                                searchable=False,
                                className="dropdown",
                                style={'width': '25%', 'display': 'inline-block'},
                            ),
                            #     ],
                            # ),
                            # html.Div(
                            #     children=[
                            html.Div(children="Start Date", className="menu-title"),
                            dcc.DatePickerSingle(
                                id='date-picker',
                                min_date_allowed=dt.today(),
                                max_date_allowed=dt(2021, 12, 31),
                                date=dt.today() + timedelta(days=1),
                            ),
                        ]
                    ),
                ],
                className="menu",
            ),
            html.Div(
                children=[dcc.Loading(id="loading-icon",
                                      children=[
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
        ]
    )


@app.callback(
    Output('table', 'data'),
    [
        Input("state-filter", "value"),
        Input("age-filter", "value"),
        Input("date-picker", "date"),
    ],
)
def get_available_capacity(s_id, min_age, date):
    try:
        print(f'getting availability for state {s_id}, min age {min_age}, start date {date}')
        # dist_availability_df = pd.DataFrame(columns=['District', 'Availability'])
        center_availability_df = pd.DataFrame(columns=cols)

        district_url = f'{cowin_server}admin/location/districts/{s_id}'
        response = requests.get(url=district_url, headers=headers)
        if response.status_code == 200:
            districts = json.loads(response.content)
            date = dt.strftime(dttime.strptime(date, "%Y-%m-%d").date(), '%d-%m-%Y')
            for d in districts['districts']:  # [{'district_name': 'Gurgaon', 'district_id': 188}]:
                # total_availability = 0
                d_id = d['district_id']
                cowin_api = f'{cowin_server}appointment/sessions/public/calendarByDistrict?district_id={d_id}&date=' + date
                response = requests.get(url=cowin_api, headers=headers)
                if response.status_code == 200:
                    content = json.loads(response.content)
                    if content['centers'] != 0:
                        for c in content['centers']:
                            for s in c['sessions']:
                                min_age_limit = s["min_age_limit"]
                                available_capacity = s["available_capacity"]
                                if int(min_age_limit) == min_age and int(available_capacity) > 0:
                                    # total_availability += available_capacity
                                    # print(d['district_name'])
                                    print(s)
                                    center_availability_df = center_availability_df.append({'Date': s['date'],
                                                                                            'District': c['district_name'],
                                                                                            'Center': c['name'],
                                                                                            'Pincode': c['pincode'],
                                                                                            'Address': c['address'],
                                                                                            'Availability': available_capacity,
                                                                                            'Vaccine': s['vaccine'],
                                                                                            'Fee': c['fee_type']},
                                                                                           ignore_index=True)

        return center_availability_df.to_dict('records')

    except Exception as e:
        print("An error has occurred while getting the valid slots : {}".format(e))


if __name__ == '__main__':
    try:
        app.title = "CoWIN Availability"
        print('init successful')
        app.run_server(host='0.0.0.0', port=8050, debug=True)

    except Exception as e:
        print("An error has occurred while checking the availability of slot : {}".format(e))
