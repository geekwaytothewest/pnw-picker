import http.client
import json

def get_auth():
    """Yeah, these don't belong here."""
    conn = http.client.HTTPSConnection("auth_url_goes_here")
    payload = "{\"client_id\":\"client_id_goes_here\",\"client_secret\":\"client_secret_goes_here\",\"audience\":\"audience_goes_here\",\"grant_type\":\"client_credentials\",\"email\":\"admin_email_goes_here\"}"
    headers = { 'content-type': "application/json" }
    conn.request("POST", "/oauth/token", payload, headers)

    res = conn.getresponse()
    data = res.read()
    decoded = data.decode("utf-8")

    return decoded

def get_api_resource(access_token, resource, url):
    """5/4/19: Now uses HTTPS. Base endpoint was /pnw/service/api, now just /."""
    # sub_endpoint = '/copycollections/2'
    sub_endpoint = '/api/legacy/org/org_id_goes_here/con/con_id_goes_here/coll/coll_id_goes_here'
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
