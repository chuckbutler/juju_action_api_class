import jujuclient
import os


class Action():
    def __init__(self, data):
        # I am undecided if we need this
        # model_id = ""
        self.uuid = data['action']['tag']
        self.data = data  # straight from juju api
        self.juju_status = data['status']

    @classmethod
    def from_data(cls, data):
        o = cls(data=data)
        return o


def get_service_units(status):
    results = {}
    services = status.get('Services', {})
    for svc_name, svc_data in services.items():
        units = svc_data['Units'] or {}
        sub_to = svc_data['SubordinateTo']
        if not units and sub_to:
            for sub in sub_to:
                for unit_name, unit_data in \
                        (services[sub].get('Units') or {}).items():
                    for sub_name, sub_data in \
                            (unit_data['Subordinates'] or {}).items():
                        if sub_name.startswith(svc_name):
                            units[sub_name] = sub_data
        results[svc_name] = units
    return results


class ActionEnvironment(jujuclient.Environment):
    def actions_available(self, service=None):
        args = {
            "Type": 'Action',
            "Request": 'ServicesCharmActions',
            "Params": {
                "Entities": []
            }
        }

        services = self.status().get('Services', {})
        service_names = [service] if service else services
        for name in service_names:
            args['Params']['Entities'].append(
                {
                    "Tag": 'service-' + name
                }
            )

        return self._rpc(args)

    def actions_list_all(self, service=None):
        args = {
            "Type": 'Action',
            "Request": 'ListAll',
            "Params": {
                "Entities": []
            }
        }

        service_units = get_service_units(self.status())
        service_names = [service] if service else service_units.keys()
        units = []

        for name in service_names:
            units += service_units[name].keys()

        for unit in set(units):
            args['Params']['Entities'].append(
                {
                    "Tag": "unit-%s" % unit.replace('/', '-'),
                }
            )

        return self._rpc(args)

    def actions_enqueue(self, action, receivers, params=None):
        args = {
            "Type": "Action",
            "Request": "Enqueue",
            "Params": {
                "Actions": []
            }
        }

        for receiver in receivers:
            args['Params']['Actions'].append({
                "Receiver": receiver,
                "Name": action,
                "Parameters": params or {},
            })

        return self._rpc(args)

    def actions_cancel(self, uuid):
        return self._rpc({
            'Type': 'Action',
            'Request': 'Cancel',
            "Params": {
                "Entities": [{'Tag': 'action-' + uuid}]
            }
        })


class API(object):
    def __init__(self, user, secret, endpoint=None):
        '''
        Establishes a connection between the given state server and this
        class. Provide the params:

        @param endpoint - websocket address of the juju model controller
        @param user - this is usually 'user-admin', but may change
        @param secret - the environment secret generated during juju bootstrap.
        '''

        if not endpoint:
            api_addresses = os.getenv('JUJU_API_ADDRESSES')
            if api_addresses:
                endpoint = 'wss://%s' % api_addresses.split()[0]

        try:
            env = ActionEnvironment(endpoint)
            env.login(secret, user=user)
        except jujuclient.EnvError as e:
            raise e

        self.env = env

    def get_status(self):
        return self.env.status()

    def get_annotations(self, services):
        '''
        Return dict of (servicename: annotations) for each servicename
        in `services`.
        '''
        if not services:
            return None

        d = {}
        for s in services:
            d[s] = self.env.get_annotation(s, 'service')['Annotations']
        return d

    def get_actions(self, service=None):
        return self.env.actions_list_all(service)

    def get_action_status(self, action_tag):
        '''
        responds with the action status, which is one of three values:

         - completed
         - pending
         - failed

         @param action_tag - the action UUID return from the enqueue method
         eg: action-3428e20d-fcd7-4911-803b-9b857a2e5ec9
        '''
        status = self.get_status()
        for action_record in status:
            if action_record['action']['tag'] == action_tag:
                return action_record['status']

    def cancel_action(self, uuid):
        return self.env.actions_cancel(uuid)

    def get_service_units(self):
        return get_service_units(self.env.status())

    def get_action_specs(self):
        results = self.env.actions_available()
        return _parse_action_specs(results)

    def enqueue_action(self, action, receivers, params):
        result = self.env.actions_enqueue(action, receivers, params)
        return Action.from_data(result['results'][0])


def _parse_action_specs(api_results):
    results = {}

    r = api_results['results']
    for service in r:
        servicetag = service['servicetag']
        service_name = servicetag[8:]  # remove 'service-' prefix
        specs = {}
        if service['actions']['ActionSpecs']:
            for spec_name, spec_def in \
                    service['actions']['ActionSpecs'].items():
                specs[spec_name] = ActionSpec(spec_name, spec_def)
        results[service_name] = specs
    return results


def _parse_action_properties(action_properties_dict):
    results = {}

    d = action_properties_dict
    for prop_name, prop_def in d.items():
        results[prop_name] = ActionProperty(prop_name, prop_def)
    return results


class Dict(dict):
    def __getattr__(self, name):
        return self[name]


class ActionSpec(Dict):
    def __init__(self, name, data_dict):
        params = data_dict['Params']
        super(ActionSpec, self).__init__(
            name=name,
            title=params['title'],
            description=params['description'],
            properties=_parse_action_properties(params['properties'])
        )


class ActionProperty(Dict):
    types = {
        'string': str,
        'integer': int,
        'boolean': bool,
        'number': float,
    }
    type_checks = {
        str: 'string',
        int: 'integer',
        bool: 'boolean',
        float: 'number',
    }

    def __init__(self, name, data_dict):
        super(ActionProperty, self).__init__(
            name=name,
            description=data_dict.get('description', ''),
            default=data_dict.get('default', ''),
            type=data_dict.get(
                'type', self._infer_type(data_dict.get('default'))),
        )

    def _infer_type(self, default):
        if default is None:
            return 'string'
        for _type in self.type_checks:
            if isinstance(default, _type):
                return self.type_checks[_type]
        return 'string'

    def to_python(self, value):
        f = self.types.get(self.type)
        return f(value) if f else value
