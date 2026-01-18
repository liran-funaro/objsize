#!/bin/env python3
"""
This scripts executes the test workflow locally.
"""

import subprocess

import yaml

skip_steps = "install", "coveralls"


def load_workflow():
    with open(".github/workflows/test.yaml") as f:
        return yaml.safe_load(f)


def iter_steps(workflow: dict, job="test"):
    steps = workflow["jobs"][job]["steps"]

    for step in steps:
        step_run = step.get("run", None)
        if step_run is None:
            continue
        step_name = step.get("name", "")
        if any(skip_name in step_name.lower() for skip_name in skip_steps):
            continue
        yield step_name, step_run


def run_job(workflow: dict, job="test"):
    for name, run in iter_steps(workflow, job):
        print(name)
        ret = subprocess.run(run, shell=True)
        if ret.returncode != 0:
            exit(ret.returncode)


def main():
    workflow = load_workflow()
    run_job(workflow, "lint")
    run_job(workflow, "test")


if __name__ == "__main__":
    main()
