schema_url = "http://json-schema.org/draft-07/schema"

keyvals = {
    "type": "object",
    "patternProperties": {
        "\\w[\\w-]*": {"type": "string"},
    },
}

# A job submission schema
submit_properties = {
    "workdir": {"type": ["string", "null"]},
    "command": {
        "oneOf": [
            {
                "type": "string",
            },
            {"type": "array", "items": {"type": ["string", "number"]}},
        ]
    },
    "envars": {
        "oneOf": [
            {"type": "null"},
            keyvals,
        ]
    },
    "num_tasks": {"type": "number"},
    "cores_per_task": {"type": ["number", "null"]},
    "gpus_per_task": {"type": ["number", "null"]},
    "num_nodes": {"type": ["number", "null"]},
    "exclusive": {"type": ["boolean", "null"]},
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
