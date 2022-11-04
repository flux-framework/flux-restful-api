#!/bin/bash

flux start uvicorn app.main:app --host=${HOST} --port=${PORT}
