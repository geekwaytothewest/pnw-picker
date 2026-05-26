import http.client
import json
import os

def get_auth():
    """Authenticate to Auth0 via the client_credentials grant.

    Credentials are read from the environment so they never live in source:
      AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET
    """
    client_id = os.environ.get("AUTH0_CLIENT_ID")
    client_secret = os.environ.get("AUTH0_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "Missing AUTH0_CLIENT_ID and/or AUTH0_CLIENT_SECRET environment variables."
        )

    conn = http.client.HTTPSConnection("geekway.auth0.com")
    payload = json.dumps({
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": "https://api.ruleslawyer.geekway.com",
        "grant_type": "client_credentials",
        "email": "mattie@mattie.lgbt",
    })
    headers = { 'content-type': "application/json" }
    conn.request("POST", "/oauth/token", payload, headers)

    res = conn.getresponse()
    data = res.read()
    decoded = data.decode("utf-8")

    return decoded

def get_api_resource(access_token, resource, url):
    """5/4/19: Now uses HTTPS. Base endpoint was /pnw/service/api, now just /."""
    # sub_endpoint = '/copycollections/2'
    # sub_endpoint = '/api/legacy/org/1/con/273/coll/16/' #pnw
    sub_endpoint = '/api/legacy/org/1/con/273/coll/17/' #playtest
    conn = http.client.HTTPSConnection(url)
    headers = { 'authorization': "Bearer " + access_token }
    conn.request("GET", sub_endpoint + resource, headers=headers)

    res = conn.getresponse()
    if res.status != 200:
        raise(IOError(f"Error parsing API: status {res.status} {res.reason}"))

    data = res.read()
    payload = data.decode("utf-8")

    return payload

def retrieve_data_api(endpoint, url='{}'):
    """Get either plays or games from a remote api."""
    if endpoint not in ['plays','games']:
        raise IOError("endpoint must be 'plays' or 'games'")

    # authenticate to get access_token
    auth = json.loads(get_auth())
    access_token = auth['access_token']

    # fetch the endpoint
    # This serializes to a python object
    # Deserialize it with json.dump
    return json.loads(get_api_resource(access_token,endpoint,url))
