# Juju Actions Class

for consuming/interacting with the VPE-Router Proxy

## Deployment and Configuration

    juju deploy local:trusty/vpe-router
    juju set vpe-router vpe-router=10.0.0.50 user=root pass=its-a-secret

## Interaction with the proxy charm via Juju CLI

Add a new corporation to the turborouter associating it to a specific vlan

    juju action do vpe-router/0 add-corporation domain-name=acme iface-name=eth0 vlan-id=acmeinternal cidr=10.240.0.0/24




 Connect the turborouter to another one where the same domain is present

    juju action do vpe-router/0 connect-domains domain-name=acme iface-name=eth1 tunnel-name=tun0 local-ip=54.21.10.151 remote-ip=54.23.64.131 tunnel-key=sesame internal-local-ip=10.1.0.51 internal-remote-ip=10.0.0.3 tunnel-type=gre

 Remove the tunnel to another turborouter where the domain is present

    juju action do vpe-router/0 delete-domain-connection domain-name=acme tunnel-name=tun0

 Remove the corporation completely from the turborouter

    juju action do vpe-router/0 delete-corporation domain-name=acme`

Interaction with the proxy charm via Python
The python class found in this repository `juju_actions.py`

> Note: if you are not sure of the Model Controller password, run `juju api-info password`

	#!/usr/bin/python3
	import juju_actions
 	username="user-admin"
	password="its-a-secret"

	# if you don’t supply an optional socket_endpoint path, it will try to infer
	# from os.getenv("JUJU_API_SERVER")

	api = juju_actions.API(username, password)

	# NOTE: the format for each unit is ‘unit-{{service}}-{{unit-number}}’
	# enqueue the action on the proxy charm to execute against its configured vpe-router



	# Add a new corporation to the turborouter associating it to a specific vlan
	action_result = api.enqueue_action(‘add-corporation’, [‘unit-vpe-router-0’], {‘domain-name’: ‘acme’, ‘iface-name’: ‘eth0’, ‘vlan-id’: ‘acmeinternal’, ‘cidr’: ‘10.240.0.0/24’})

	# this object that is returned has a status field that can be used to poll for the
	# result
	status_result = get_action_status(action_result.tag)
	print(status_result)

	# Connect the turborouter to another one where the same domain is present
	api.enqueue_action(‘connect-domains’, [‘unit-vpe-router-0’], { ‘domain-name’: ‘acme’, ‘iface-name’: ‘eth1’, ‘tunnel-name’: ‘tun0’, ‘local-ip’: ‘54.21.10.151’, ‘remote-ip’: ‘54.23.64.131’, ‘tunnel-key’: ‘sesame’, ‘internal-local-ip’: ‘10.1.0.51’, ‘internal-remote-ip’: ‘10.0.0.3’, ‘tunnel-type’: ‘gre’})

	# Remove the tunnel to another turborouter where the domain is present
	api.enqueue_action(‘delete-domain-connection’, [‘unit-vpe-router-0’], {‘domain-name’: ‘acme’, ‘tunnel-name’: ‘tun0’})

	# Remove the corporation completely from the turborouter
	api.enqueue_action(‘delete-corporation’, [‘unit-vpe-router-0’], {‘domain-name’: ‘acme’})
