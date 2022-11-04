import requests 
import logging 
import json
import os
from copy import deepcopy

logger = logging.getLogger(__name__)

class FluxRestfulClient:
    def __init__(self, host=None, user=None, token=None):
        self.host = host  or "http://127.0.0.1:5000"
        self.user = user or os.environ.get('FLUX_USER')
        self.token = token or os.environ.get('FLUX_TOKEN')
        self.session = requests.Session()
        self.headers = {}

    def set_header(self, name, value):
        self.headers.update({name: value})

    def set_basic_auth(self, username, password):
        """
        A wrapper to adding basic authentication to the Request
        """
        auth_header = get_basic_auth(username, password)
        if isinstance(auth_header, bytes):
            auth_header = auth_header.decode("utf-8")
        self.set_header("Authorization", "Basic %s" % auth_header)

    def reset(self):
        """
        Reset and prepare for a new request.
        """
        if "Authorization" in self.headers:
            self.headers = {"Authorization": self.headers["Authorization"]}
        else:
            self.headers = {}

    def do_request(self, endpoint, method="GET", data=None, headers=None):
        """
        Do a request. This is a wrapper around requests.
        """
        # Always reset headers for new request.
        self.reset()

        headers = headers or {}
        url = "%s/%s" % (self.host, endpoint)

        # Make the request and return to calling function, unless requires auth
        response = self.session.request(method, url, json=data, headers=headers)

        # A 401 response is a request for authentication
        if response.status_code != 401:
            return response

        # Otherwise, authenticate the request and retry
        if self.authenticate_request(response):            
            return self.session.request(method, url, json=data, headers=self.headers)
        return response

    def authenticate_request(self, originalResponse):
        """
        Authenticate Request
        Given a response, look for a Www-Authenticate header to parse. We
        return True/False to indicate if the request should be retried.
        """
        authHeaderRaw = originalResponse.headers.get("Www-Authenticate")
        if not authHeaderRaw:

            return False

        # If we have a username and password, set basic auth automatically
        if self.token and self.username:
            self.set_basic_auth(self.username, self.token)

        headers = deepcopy(self.headers)
        if "Authorization" not in headers:
            logger.error(
                "This endpoint requires a token. Please set "
                "client.set_basic_auth(username, password) first "
                "or export them to the environment."
            )
            return False

        # Prepare request to retry
        h = parse_auth_header(authHeaderRaw)
        headers.update(
            {
                "service": h.Service,
                "Accept": "application/json",
                "User-Agent": "flux-restful-client",
            }
        )

        # Currently we don't set a scope (it defaults to build)
        authResponse = self.session.request("GET", h.Realm, headers=headers)
        if authResponse.status_code != 200:
            return False

        # Request the token
        info = authResponse.json()
        token = info.get("token")
        if not token:
            token = info.get("access_token")

        # Set the token to the original request and retry
        self.headers.update({"Authorization": "Bearer %s" % token})
        return True

    def jobs(self, jobid=None):
        """
        Given the id for a result, download to file
        """
        print('JOBS LIST')
        import IPython 
        IPython.embed()
        endpoint = "jobs/"
        if jobid:
            endpoint += str(jobid) + "/"
        result = self.do_request(endpoint, "GET")
        if result.status_code == 404:
            print("There is no job for that identifier.")
            return
        return result.json()

    def submit(self, command):
        """
        Given the id for a result, download to file
        """
        endpoint = "jobs/submit"
        if isinstance(command, list):
            command = " ".join([str(x) for x in command])
        data = {"command": command}
        result = self.do_request(endpoint, "GET", data=data)
        if result.status_code == 404:
            print("There is no job for that identifier.")
            return
        return result.json()


# Helper functions

def get_basic_auth(username, password):
    auth_str = "%s:%s" % (username, password)
    return base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")


def parse_auth_header(authHeaderRaw):
    """
    Parse authentication header into pieces
    """
    regex = re.compile('([a-zA-z]+)="(.+?)"')
    matches = regex.findall(authHeaderRaw)
    lookup = dict()
    for match in matches:
        lookup[match[0]] = match[1]
    return authHeader(lookup)


class authHeader:
    def __init__(self, lookup):
        """
        Given a dictionary of values, match them to class attributes
        """
        for key in lookup:
            if key in ["realm", "service", "scope"]:
                setattr(self, key.capitalize(), lookup[key])


def read_file(filename):
    with open(filename, "r") as fd:
        content = fd.read()
    return content


def read_json(filename):
    return json.loads(read_file(filename))