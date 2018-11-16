from django import template

from tom_observations.models import DataProduct, ObservationRecord
from tom_observations.facility import get_service_classes

register = template.Library()


@register.inclusion_tag('tom_observations/partials/dataproduct_list.html')
def dataproduct_list(target=None):
    if target:
        products = target.dataproduct_set.all()
    products = DataProduct.objects.all().order_by('-created')
    return {'products': products}


@register.inclusion_tag('tom_observations/partials/observing_buttons.html')
def observing_buttons(target):
    facilities = get_service_classes()
    return {'target': target, 'facilities': facilities}


@register.inclusion_tag('tom_observations/partials/observation_list.html')
def observation_list(target=None):
    if target:
        observations = target.observationrecord_set.all()
    observations = ObservationRecord.objects.all().order_by('-created')
    print(observations)
    return {'observations': observations}