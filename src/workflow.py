
# This module contains the functions that are used to configure the input and output of the workflow for the current app.

import supervisely as sly
from typing import Literal

workflow_processed = False # This variable is used to prevent the workflow from being processed multiple times in the same app run.

def workflow_input(api):
    raise NotImplementedError

def workflow_output(api: sly.Api, id: int, type: Literal["project", "dataset"]):
    try:
        if workflow_processed:
            sly.logger.debug("Workflow has already been processed for this app run and will be skipped.")
            return
        if type == "project":
            api.app.workflow.add_output_project(id)
            sly.logger.debug(f"Workflow: Output project - {id}")
        elif type == "dataset":
            api.app.workflow.add_output_dataset(id)
            sly.logger.debug(f"Workflow: Output dataset - {id}")
        workflow_processed = True
    except Exception as e:
         sly.logger.debug(f"Failed to add input to the workflow: {repr(e)}")
        