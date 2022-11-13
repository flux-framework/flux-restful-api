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

    # STOPPED HERE - serialize in jquery from form, submit as application/json.
    async def load_data(self):
        form = await self.request.form()
        self.command = form.get("command")
        self.workdir = form.get("workdir") or None
        self.num_tasks = form.get("num_tasks") or 1
        self.num_nodes = form.get("num_nodes") or 1
        self.runtime = form.get("runtime") or 0
        self.cores_per_task = form.get("cores_per_task") or None
        self.gpus_per_task = form.get("gpus_per_task") or None
        self.exclusive = form.get("exclusive") or False

    @property
    def kwargs(self):
        """
        Prepared key value dictionary of items.
        """
        kwargs = {}
        for key in [
            "command",
            "num_tasks",
            "num_nodes",
            "cores_per_task",
            "gpys_per_task",
            "exclusive",
        ]:
            if getattr(self, key, None) is not None:
                kwargs[key] = getattr(self, key)
        return kwargs

    def is_valid(self):
        """
        Determine if the form is valid (devoid of errors)
        """
        self.errors = flux_cli.validate_submit_kwargs(self.kwargs, runtime=self.runtime)
        if not self.errors:
            return True
        return False