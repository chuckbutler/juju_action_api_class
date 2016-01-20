#!/usr/bin/python3
import juju_actions

username="user-admin"
password="its-a-secret"

# if you dont supply an optional socket_endpoint path, it will try to infer
# from os.getenv("JUJU_API_SERVER")

api = juju_actions.API(username, password)

# the empty dict is a dict of params for the action if required. eg:
# {'force': true}
action_result = api.enqueue_action('clean-images', ['unit-redmine-0'], {}) 
# this object that is returned has a status field that can be used to poll for the result
status_result = get_action_status(action_result.tag)
print(status_result)
