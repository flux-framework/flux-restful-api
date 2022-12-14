import os
from copy import deepcopy

import flux_restful_client.main.schemas as schemas
import flux_restful_client.utils as utils
import jsonschema
import requests
from flux_restful_client.logger import logger

from .settings import Settings


class FluxRestfulClient:
    """
    Create a FluxRestful Client to interact with the Flux RESTFul API server.
    """

    def __init__(
        self,
        host=None,
        user=None,
        token=None,
        quiet=False,
        settings_file=None,
        prefix="v1",
        **kwargs,
    ):

        # If we don't have default settings, load
        if not hasattr(self, "settings"):
            self.settings = Settings(settings_file)

        self.host = host or self.settings.host
        self.user = user or os.environ.get("FLUX_USER") or self.settings.flux_user
        self.token = token or os.environ.get("FLUX_TOKEN") or self.settings.flux_token
        self.headers = {}
        self.quiet = quiet
        self.prefix = prefix
        if self.user and self.token:
            self.set_basic_auth(self.user, self.token)
        self.session = requests.Session()

    def set_header(self, name, value):
        self.headers.update({name: value})

    def set_basic_auth(self, username, password):
        """
        A wrapper to adding basic authentication to the Request
        """
        auth_header = utils.get_basic_auth(username, password)
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

    def do_request(
        self, endpoint, method="GET", data=None, headers=None, params=None, stream=False
    ):
        """
        Do a request. This is a wrapper around requests.
        """
        # Always reset headers for new request.
        self.reset()

        headers = headers or self.headers
        url = "%s/%s/%s" % (self.host, self.prefix, endpoint)

        # Make the request and return to calling function, unless requires auth
        response = self.session.request(
            method, url, params=params, json=data, headers=headers, stream=stream
        )

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
        h = utils.parse_auth_header(authHeaderRaw)
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

    def list_nodes(self):
        """
        List nodes available.
        """
        return self.do_request("nodes", "GET").json()

    def cancel(self, jobid):
        """
        Request for a job to be cancelled based on identifier.
        """
        return self.do_request(f"jobs/{jobid}/cancel", "POST").json()

    def stream_output(self, jobid):
        """
        Request for job output to be streamed
        """
        response = self.do_request(f"jobs/{jobid}/output/stream", "GET", stream=True)
        for line in response.iter_lines():
            if line:
                yield line.decode("utf-8")

    def output(self, jobid):
        """
        Request for a job to be cancelled based on identifier.
        """
        return self.do_request(f"jobs/{jobid}/output", "GET").json()

    def stop_service(self):
        """
        Stop the server running.
        """
        return self.do_request("service/stop", "POST").json()

    def jobs(self, jobid=None, detail=False, listing=False):
        """
        Get a listing of jobs that the Flux RESTful API knows about!
        """
        endpoint = "jobs"
        params = {}
        if jobid:
            endpoint += "/" + str(jobid)

        # This indicates a jobs listing (not a single job)
        else:
            if detail:
                params["detail"] = "true"
            if listing:
                params["listing"] = "true"
        result = self.do_request(endpoint, "GET", params=params)
        if result.status_code == 404:
            print("There is no job for that identifier.")
            return
        return result.json()

    def search(self, query=None, start=None, length=None):
        """
        Search endpoint for jobs.
        """
        params = {}
        if query:
            params["query"] = str(query)
        if start is not None:
            params["start"] = start
        if length is not None:
            params["length"] = length
        return self.do_request("jobs/search", "GET", params=params).json()

    def submit(self, command, **kwargs):
        """
        Submit a job to the Flux RESTful API

        Optional kwargs that are accepted include:
        workdir (str): a working directory for the job
        num_tasks (int): Number of tasks (defaults to 1)
        cores_per_task (int): Number of cores per task (default to 1)
        gpus_per_task (int): Number of gpus per task (defaults to None)
        num_nodes (int): Number of nodes (defaults to None)
        option_flags (dict): Option flags (as dict, defaults to {})
        exclusive (bool): is the job exclusive? (defaults to False)
        is_launcher (bool): the command should be submit to a launcher.
        This is currently supported for snakemake and nextflow.
        """
        # Allow the user to provide a list (and stringify everything)
        if isinstance(command, list):
            command = " ".join([str(x) for x in command])
        data = {"command": command}
        for optional in [
            "num_tasks",
            "cores_per_task",
            "gpus_per_task",
            "option_flags",
            "num_nodes",
            "exclusive",
            "is_launcher",
            "workdir",
            "envars",
        ]:

            # Assume if it's provided, period, the user wants to set it!
            if optional in kwargs:
                data[optional] = kwargs[optional]

        # Validate the data first.
        print(data)
        jsonschema.validate(data, schema=schemas.job_submit_schema)
        result = self.do_request("jobs/submit", "POST", data=data)
        if result.status_code == 404:
            print("There is no job for that identifier.")
            return
        return result.json()

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "[flux-restful-client]"
