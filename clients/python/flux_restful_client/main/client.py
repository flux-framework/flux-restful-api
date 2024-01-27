import os
import sys
import time

import flux_restful_client.main.schemas as schemas
import flux_restful_client.utils as utils
import httpx
import jsonschema
from flux_restful_client.logger import logger
from jose import jwt

from .settings import Settings


def get_encoded_auth(user, token, secret_key):
    """
    This is encoded with the shared user/server secret
    """
    if not secret_key:
        sys.exit("Cannot generate header without secret key")
    auth_str = {"user": user, "pass": token, "scope": "token"}
    return jwt.encode(auth_str, secret_key)  # algorithm is 'HS256'


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
        secret_key=None,
        settings_file=None,
        prefix="v1",
        attempts=5,
        timeout=2,
        **kwargs,
    ):
        # If we don't have default settings, load
        if not hasattr(self, "settings"):
            self.settings = Settings(settings_file)

        self.host = host or os.environ.get("FLUX_RESTFUL_HOST") or self.settings.host
        self.user = user or os.environ.get("FLUX_USER") or self.settings.flux_user
        self.token = token or os.environ.get("FLUX_TOKEN") or self.settings.flux_token
        self.secret_key = secret_key or os.environ.get("FLUX_SECRET_KEY")
        self.headers = {}
        self.quiet = quiet
        self.prefix = prefix
        self.attempts = attempts
        self.timeout = timeout
        self.session = httpx.Client()

    def set_header(self, name, value):
        self.headers.update({name: value})

    def set_bearer_auth(self, token):
        """
        Add a token directly to a request
        """
        self.set_header("Authorization", f"Bearer {token}")

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
        self,
        endpoint,
        method="GET",
        data=None,
        headers=None,
        params=None,
        stream=False,
        timeout=None,
        attempts=None,
    ):
        """
        Do a request. This is a wrapper around httpx.
        """
        attempts = self.attempts if attempts is None else attempts
        timeout = self.timeout if timeout is None else timeout

        # Always reset headers for new request.
        self.reset()

        headers = headers or self.headers
        url = f"{self.host}/{self.prefix}/{endpoint}"
        method = method.upper()

        # Make the request and return to calling function, unless requires auth
        try:
            if method == "POST" and stream:
                response = self.session.stream(
                    method, url, json=data, params=params, headers=headers
                )
            elif method == "POST":
                response = self.session.post(url, params=data, headers=headers)
            elif method == "GET" and stream:
                response = self.session.stream(
                    method, url, params=params, headers=headers
                )
            elif method == "GET":
                response = self.session.get(url, params=params, headers=headers)

        except Exception as e:
            if attempts > 0:
                time.sleep(timeout)
                return self.do_request(
                    endpoint,
                    method,
                    data,
                    headers,
                    params,
                    stream,
                    timeout=timeout * 2,
                    attempts=attempts - 1,
                )
            raise e

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
        # If we have user and token and get here, likely need to recreate
        if "Authorization" in self.headers:
            del self.headers["Authorization"]

        if "www-authenticate" not in originalResponse.headers:
            logger.error(f"{originalResponse.url} missing www-authenticate header.")
            return False

        # Make request with encoded secret payload
        headers = {
            "Authorization": "Bearer %s"
            % get_encoded_auth(self.user, self.token, self.secret_key)
        }
        response = self.do_request("token", method="post", headers=headers)
        if response.status_code != 200:
            logger.error(f"Issue requesting token: {response.reason}")
            return False

        token = response.json()
        assert "access_token" in token and "token_type" in token
        self.set_bearer_auth(token["access_token"])
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
            if optional == "option_flags" and optional in kwargs:
                kwargs[optional] = utils.flatten_list(kwargs[optional])
            if optional in kwargs:
                data[optional] = kwargs[optional]

        # Validate the data first.
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
