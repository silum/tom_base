from django import template
from django.conf import settings
from dateutil.parser import parse
from plotly import offline
import plotly.graph_objs as go
from astropy import units as u
from astropy.coordinates import Angle
from guardian.shortcuts import get_objects_for_user

from tom_targets.models import Target, TargetExtra, TargetList
from tom_targets.forms import TargetVisibilityForm, TargetGroupingVisibilityForm
from tom_observations.utils import get_sidereal_visibility
from tom_observations.facility import get_service_class, get_service_classes

register = template.Library()


@register.inclusion_tag('tom_targets/partials/recent_targets.html', takes_context=True)
def recent_targets(context, limit=10):
    """
    Displays a list of the most recently created targets in the TOM up to the given limit, or 10 if not specified.
    """
    return {'targets': get_objects_for_user(context['user'], 'tom_targets.view_target').order_by('-created')[:limit]}


@register.inclusion_tag('tom_targets/partials/target_feature.html')
def target_feature(target):
    """
    Displays the featured image for a target.
    """
    return {'target': target}


@register.inclusion_tag('tom_targets/partials/target_data.html')
def target_data(target):
    """
    Displays the data of a target.
    """
    return {
        'target': target,
        'display_extras': [ex['name'] for ex in settings.EXTRA_FIELDS if not ex.get('hidden')]
    }


@register.inclusion_tag('tom_targets/partials/target_groups.html')
def target_groups(target):
    """
    Widget displaying groups this target is in and controls for modifying group association for the given target.
    """
    groups = TargetList.objects.filter(targets=target)
    return {'target': target,
            'groups': groups}


@register.inclusion_tag('tom_targets/partials/target_plan.html', takes_context=True)
def target_plan(context):
    """
    Displays form and renders plot for visibility calculation. Using this templatetag to render a plot requires that
    the context of the parent view have values for start_time, end_time, and airmass.
    """
    request = context['request']
    plan_form = TargetVisibilityForm()
    visibility_graph = ''
    if all(request.GET.get(x) for x in ['start_time', 'end_time']):
        plan_form = TargetVisibilityForm({
            'start_time': request.GET.get('start_time'),
            'end_time': request.GET.get('end_time'),
            'airmass': request.GET.get('airmass'),
            'target': context['object']
        })
        if plan_form.is_valid():
            start_time = parse(request.GET['start_time'])
            end_time = parse(request.GET['end_time'])
            if request.GET.get('airmass'):
                airmass_limit = float(request.GET.get('airmass'))
            else:
                airmass_limit = None
            visibility_data = get_sidereal_visibility([context['object']],
                                                      start_time, end_time, 10, airmass_limit)
            print(visibility_data[context['object'].name])
            plot_data = [
                go.Scatter(
                    x=site_visibility['airmass_data'][0],
                    y=site_visibility['airmass_data'][1],
                    mode='lines',
                    name=f"({site_visibility.get('site').facility}) {site_visibility['site'].display_name}"
                ) for site_visibility in visibility_data[context['object'].name]
            ]
            layout = go.Layout(yaxis=dict(autorange='reversed'))
            visibility_graph = offline.plot(
                go.Figure(data=plot_data, layout=layout), output_type='div', show_link=False
            )
    return {
        'form': plan_form,
        'target': context['object'],
        'visibility_graph': visibility_graph
    }


@register.inclusion_tag('tom_targets/partials/targetgrouping_plan.html', takes_context=True)
def targetgrouping_plan(context):
    request = context['request']
    plan_form = TargetGroupingVisibilityForm()
    visibility_graph = ''
    if all(request.GET.get(x) for x in ['site', 'airmass', 'start_date', 'end_date']):
        plan_form = TargetGroupingVisibilityForm({
            'site': request.GET.get('site'),
            'airmass': request.GET.get('airmass'),
            'start_date': request.GET.get('start_date'),
            'end_date': request.GET.get('end_date')
        })
        if plan_form.is_valid():
            sitecode = request.GET['site']
            start_date = parse(request.GET['start_date'])
            end_date = parse(request.GET['end_date'])
            airmass = float(request.GET['airmass'])
            for facility_class in get_service_classes():
                try:
                    site = get_service_class(facility_class)().get_site(sitecode)
                    break
                except KeyError:
                    pass
            visibility = {}
            visibility = get_sidereal_visibility(context['object'].targets.all(), start_date, end_date, 10,
                                                 float(airmass), sites=[site])
            plot_data = [
                go.Scatter(
                    x=data[0]['airmass_data'][0],
                    y=data[0]['airmass_data'][1],
                    mode='lines',
                    name=target
                ) for target, data in visibility.items()
            ]
            layout = go.Layout(title=f'Visibility at {site.display_name} on {start_date}',
                               yaxis=dict(autorange='reversed'))
            visibility_graph = offline.plot(
                go.Figure(data=plot_data, layout=layout), output_type='div', show_link=False
            )

    return {
        'form': plan_form,
        'targetlist': context['object'],
        'visibility_graph': visibility_graph
    }


@register.inclusion_tag('tom_targets/partials/target_distribution.html')
def target_distribution(targets):
    """
    Displays a plot showing on a map the locations of all sidereal targets in the TOM.
    """
    locations = targets.filter(type=Target.SIDEREAL).values_list('ra', 'dec', 'name')
    data = [
        dict(
            lon=[l[0] for l in locations],
            lat=[l[1] for l in locations],
            text=[l[2] for l in locations],
            hoverinfo='lon+lat+text',
            mode='markers',
            type='scattergeo'
        ),
        dict(
            lon=list(range(0, 360, 60))+[180]*4,
            lat=[0]*6+[-60, -30, 30, 60],
            text=list(range(0, 360, 60))+[-60, -30, 30, 60],
            hoverinfo='none',
            mode='text',
            type='scattergeo'
        )
    ]
    layout = {
        'title': 'Target Distribution (sidereal)',
        'hovermode': 'closest',
        'showlegend': False,
        'geo': {
            'projection': {
                'type': 'mollweide',
            },
            'showcoastlines': False,
            'showland': False,
            'lonaxis': {
                'showgrid': True,
                'range': [0, 360],
            },
            'lataxis': {
                'showgrid': True,
                'range': [-90, 90],
            },
        }
    }
    figure = offline.plot(go.Figure(data=data, layout=layout), output_type='div', show_link=False)
    return {'figure': figure}


@register.filter
def deg_to_sexigesimal(value, fmt):
    """
    Displays a degree coordinate value in sexigesimal, given a format of hms or dms.
    """
    a = Angle(value, unit=u.degree)
    if fmt == 'hms':
        return '{0:02.0f}:{1:02.0f}:{2:05.3f}'.format(a.hms.h, a.hms.m, a.hms.s)
    elif fmt == 'dms':
        rep = a.signed_dms
        sign = '-' if rep.sign < 0 else '+'
        return '{0}{1:02.0f}:{2:02.0f}:{3:05.3f}'.format(sign, rep.d, rep.m, rep.s)
    else:
        return 'fmt must be "hms" or "dms"'


@register.filter
def target_extra_field(target, name):
    """
    Returns a ``TargetExtra`` value of the given name, if one exists.
    """
    try:
        return TargetExtra.objects.get(target=target, key=name).value
    except TargetExtra.DoesNotExist:
        return None


@register.inclusion_tag('tom_targets/partials/targetlist_select.html')
def select_target_js():
    """
    """
    return


@register.inclusion_tag('tom_targets/partials/aladin.html')
def aladin(target):
    """
    Displays Aladin skyview of the given target.
    """
    return {'target': target}
