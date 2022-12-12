from typing import List, Optional

from fastapi import Request

import app.library.flux as flux_cli


class SubmitForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.command: str
        self.workdir: Optional[str] = None
        self.num_tasks: Optional[int] = None
        self.num_nodes: Optional[int] = None
        self.runtime: Optional[int] = None
        self.cores_per_task: Optional[int] = None
        self.gpus_per_task: Optional[int] = None
        self.exclusive: Optional[bool] = False
        self.is_launcher: Optional[bool] = False
        self.exclusive: Optional[bool] = False

    async def load_data(self):
        form = await self.request.form()
        self.command = form.get("command")
        self.workdir = form.get("workdir")
        self.num_tasks = form.get("num_tasks")
        self.num_nodes = form.get("num_nodes")
        self.runtime = form.get("runtime") or 0
        self.cores_per_task = form.get("cores_per_task")
        self.gpus_per_task = form.get("gpus_per_task")
        self.exclusive = True if form.get("exclusive") == "on" else False
        self.is_launcher = True if form.get("is_launcher") == "on" else False

    @property
    def kwargs(self):
        """
        Prepared key value dictionary of items.
        """
        kwargs = {}
        as_int = ["num_tasks", "num_nodes", "cores_per_task", "gpus_per_task"]
        as_bool = ["exclusive", "is_launcher"]
        for key in as_int + as_bool + ["command"]:
            if getattr(self, key, None) is not None:
                value = getattr(self, key)

                # Form could submit an empty value
                if value == "":
                    continue

                # Parse as integer
                if key in as_int:
                    kwargs[key] = int(value)
                elif key in as_bool:
                    kwargs[key] = value
                else:
                    kwargs[key] = value
        return kwargs

    def is_valid(self):
        """
        Determine if the form is valid (devoid of errors)
        """
        self.errors = flux_cli.validate_submit_kwargs(self.kwargs, runtime=self.runtime)
        if not self.errors:
            return True
        return False
