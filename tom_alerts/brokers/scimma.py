from tom_alerts.alerts import GenericQueryForm, GenericAlert, GenericBroker
from tom_targets.models import Target
from django import forms
import requests
from tom_base import settings

SCIMMA_URL = 'http://skip.dev.hop.scimma.org'


class SCIMMABrokerForm(GenericQueryForm):
    trigger_number = forms.CharField(required=True)


class SCIMMABroker(GenericBroker):
    """
    This is a prototype interface to the skip db built by SCIMMA
    """

    name = 'SCIMMA'
    form = SCIMMABrokerForm

    def fetch_alerts(self, parameters):
        response = requests.get(SCIMMA_URL + '/api/alerts/',
                                params={'event_trigger_number': parameters['trigger_number']},
                                headers=settings.BROKER_CREDENTIALS['SCIMMA'])
        response.raise_for_status()
        result = response.json()
        return iter(result['results'])

    def fetch_alert(self, alert_id):
        url = SCIMMA_URL + '/api/alerts/' + alert_id
        response = requests.get(url, headers=settings.BROKER_CREDENTIALS['SCIMMA'])
        response.raise_for_status()
        parsed = response.json()
        return parsed

    def process_reduced_data(self, target, alert=None):
        pass

    def to_generic_alert(self, alert):
        return GenericAlert(
            url=SCIMMA_URL + f'/api/alerts/{alert["id"]}',
            id=alert['id'],
            # This should be the object name if it is in the comments
            name=alert['id'],
            ra=alert['right_ascension'],
            dec=alert['declination'],
            timestamp=alert['alert_timestamp'],
            # Well mag is not well defined for XRT sources...
            mag=0.0,
            score=alert['message'].get('rank', 0),  # Not exactly what score means, but ish
        )

    def to_target(self, alert):
        # Galactic Coordinates come in the format:
        # "gal_coords": "76.19,  5.74 [deg] galactic lon,lat of the counterpart",
        gal_coords = alert['message']['gal_coords'].split('[')[0].split(',')
        gal_coords = [float(coord.strip()) for coord in gal_coords]
        return Target.objects.create(
            name=alert['name'],
            type='SIDEREAL',
            ra=alert['right_ascension'],
            dec=alert['right_ascension'],
            galactic_lng=gal_coords[0],
            galactic_lat=gal_coords[1],
        )
