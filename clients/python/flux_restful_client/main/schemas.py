schema_url = "http://json-schema.org/draft-07/schema"

keyvals = {
    "type": "object",
    "patternProperties": {
        "\\w[\\w-]*": {"type": "string"},
    },
}

# A job submission schema
submit_properties = {
    "workdir": {
        "type": ["string", "null"],
        "description": "working directory for the job to run",
    },
    "command": {
        "oneOf": [
            {
                "type": "string",
            },
            {"type": "array", "items": {"type": ["string", "number"]}},
        ],
        "description": "full command for job to run as a string or list.",
    },
    "envars": {
        "description": "key value pairs to export to the environment.",
        "oneOf": [
            {"type": "null"},
            keyvals,
        ],
    },
    "num_tasks": {"type": "number", "description": "number of tasks for the job."},
    "cores_per_task": {
        "type": ["number", "null"],
        "description": "number of cores per task for the job.",
    },
    "gpus_per_task": {
        "type": ["number", "null"],
        "description": "number of gpus per task for the job.",
    },
    "num_nodes": {
        "type": ["number", "null"],
        "description": "number of nodes for the job.",
    },
    "exclusive": {
        "type": ["boolean", "null"],
        "description": "ask for exclusive nodes for the job.",
    },
    "is_launcher": {
        "type": ["boolean", "null"],
        "description": "indicate the command is for a launcher (e.g., nextflow, snakemake)",
    },
}

job_submit_schema = {
    "$schema": schema_url,
    "title": "Flux Job Submit Schema",
    "type": "object",
    "required": [
        "command",
    ],
    "properties": submit_properties,
    "additionalProperties": False,
}


# Currently all of these are required
settingsProperties = {
    "flux_token": {"type": ["string", "null"]},
    "flux_user": {"type": ["string", "null"]},
    "host": {"type": "string"},
    "config_editor": {"type": "string"},
    "workdir": {"type": ["string", "null"]},
}

settings = {
    "$schema": schema_url,
    "title": "Settings Schema",
    "type": "object",
    "required": [
        "host",
        "config_editor",
    ],
    "properties": settingsProperties,
    "additionalProperties": False,
}
