import logging
from importlib import import_module

from django.conf import settings
from hop import Stream
from hop.auth import Auth

logger = logging.getLogger(__name__)


def import_method(name):
    mod_name, method = name.rsplit('.', 1)
    try:
        mod = import_module(mod_name)
        m = getattr(mod, method)
    except (ImportError, AttributeError):
        raise ImportError('Could not import {}. Did you provide the correct path?'.format(name))
    return m


def run_hook(name, *args, **kwargs):
    hook = settings.HOOKS.get(name)
    if hook:
        method = import_method(hook)
        return method(*args, **kwargs)


def target_post_save(target, created):
    logger.info('Target post save hook: %s created: %s', target, created)


def observation_change_state(observation, previous_state):
    logger.info('Observation change state hook: %s from %s to %s', observation, previous_state, observation.status)
    if observation.terminal and previous_state != observation.status:
        creds = settings.BROKER_CREDENTIALS['Hopskotch']
        stream = Stream(auth=Auth(creds['username'], creds['password']))
        message = {}

        message = {'type': 'observation', 'parameters': observation.parameters_as_dict, 'status': observation.status,
                   'target': observation.target.name, 'ra': observation.target.ra,
                   'dec': observation.target.dec, 'facility': observation.facility}
        with stream.open('kafka://dev.hop.scimma.org:9092/tomtoolkit-test', 'w') as s:
            s.write(message)

        logger.log(msg='Successfully submitted alert upstream to SCiMMA!', level=logging.INFO)
