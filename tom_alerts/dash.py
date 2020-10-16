import re

import dash
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as dhc

from django.conf import settings
from django_plotly_dash import DjangoDash

from skip_dpd.skip_client import get_client


app = DjangoDash('SkipSwiftXRTDash', external_stylesheets=[dbc.themes.BOOTSTRAP], add_bootstrap_links=True)

comment_warnings_prefix = 'ranks\.php for details.'
counterpart_identifier_regex = re.compile(r'\d?\w+\s\w\d+\.\d(\+|-)\d+')
comment_warnings_regex = re.compile(r'({prefix}).*$'.format(prefix=comment_warnings_prefix))


def generate_pagination(page_size, page_num):
    # TODO: make this return which set of alerts are being displayed
    return dbc.Row([
        dbc.Col(f'Showing {(page_num-1)*(page_size) + 1} - {page_num*page_size} alerts', width=8),
        dbc.Col(width=1),
        dbc.Col(width=1),
        dbc.Col(width=1),
        dbc.Col([dhc.Button('<', id='last-page', n_clicks=0),
                f' {page_num} ',
                dhc.Button('>', id='next-page', n_clicks=0)
            ], 
            width=1
        ),
    ], id='pagination')

def generate_table(alerts, page_size, page_num):
    table_header = [
        dhc.Thead(
            dhc.Tr([
                dhc.Th(''),
               # dhc.Th(''),
                dhc.Th('Counterpart Identifier'),
                dhc.Th('Right Ascension'),
                dhc.Th('Declination'),
                dhc.Th('LIGO Event TrigNum'),
                dhc.Th('Telescope'),
                dhc.Th('Rank'),
                dhc.Th('Comments'),
            ])
        )
    ]
    table_rows = []
    print('got here')

    for i, alert in enumerate(alerts):
        alert_id = alert['id']
        ci_match = counterpart_identifier_regex.search(alert['message']['comments'])
        counterpart_identifier = ci_match[0] if ci_match else ''
        cw_match = comment_warnings_regex.search(alert['message']['comments'])
        comment_warnings = cw_match[0][len(comment_warnings_prefix):] if cw_match else ''
        table_rows.append(

            dhc.Tr([
            #dhc.Td(dhc.Div([dcc.Checklist(
            #            id={"item": i, "action": "done"},
            #            options=[{"label": "", "value": "create_target"}],
            #            value=False,
            #            style={"display": "inline"},
            #        )])),
            dhc.Td(dhc.A(alert_id, href=f'/api/alerts/{alert_id}')),
            dhc.Td(counterpart_identifier),
            dhc.Td(alert['right_ascension_sexagesimal']),
            dhc.Td(alert['declination_sexagesimal']),
            dhc.Td(alert['message'].get('event_trig_num', '')),
            dhc.Td(alert['message'].get('telescope', '')),
            dhc.Td(alert['message'].get('rank', '')),
            dhc.Td(comment_warnings),
        ]))
    return dhc.Div([
        dcc.Store(id='session'),
        dbc.Table(table_header + table_rows, bordered=True),
        generate_pagination(page_size, page_num)
    ])


skip_client = get_client()()
lvc_topic = skip_client.get_topics(name='lvc-counterpart')[0]
alerts = skip_client.get_alerts(page=1, page_size=settings.DEFAULT_PAGE_SIZE, topic=[lvc_topic['id']])


app.layout = dhc.Div([
    dcc.Input(
        id='event-trigger-number',
        type='text',
        placeholder='test'
    ),
    dhc.Div(generate_table(alerts, 20, 1), id='table-container'),
])


@app.callback(
    [Output('table-container', 'children'),
    Output('session', 'data')],
    [Input('event-trigger-number', 'value'),
    Input('last-page', 'n_clicks_timestamp'),
    Input('next-page', 'n_clicks_timestamp')],
    [State('session', 'data')]
)
def update_table(event_trig_num, last_page_timestamp, next_page_timestamp, data):
    if not data:
        data = {'page_num': 1}
    if last_page_timestamp and data['page_num'] > 1:
        data['page_num'] -= 1
    elif next_page_timestamp and data['page_num'] < 20:  # TODO: 20 should be num_pages
        data['page_num'] += 1
    event_trigger_number = event_trig_num if event_trig_num else ''
    alerts = skip_client.get_alerts(page=data['page_num'], page_size=settings.DEFAULT_PAGE_SIZE,
                                    topic=[lvc_topic['id']], event_trigger_number=event_trigger_number)

    return generate_table(alerts, 20, data['page_num']), data
