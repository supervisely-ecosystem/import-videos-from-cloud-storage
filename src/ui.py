import supervisely_lib as sly
from functools import partial


def init_context(data, team_id, workspace_id):
    data["teamId"] = team_id
    data["workspaceId"] = workspace_id


def init_connection(data, state):
    state["provider"] = "google"  # "s3"
    state["bucketName"] = "surgar-bigdata-bucket-01"# "remote-img-test/"
    state["selected"] = ""
    data["tree"] = None


def init_options(data, state):
    state["addMode"] = "copyData"
    state["dstProjectMode"] = "newProject"
    state["dstProjectName"] = "my_videos"
    state["dstProjectId"] = None

    state["dstDatasetMode"] = "newDataset"
    state["dstDatasetName"] = "my_dataset"
    state["dstDatasetId"] = None

    data["processing"] = False


def init_progress(data, state):
    data["progressName1"] = None
    data["currentProgressLabel1"] = 0
    data["totalProgressLabel1"] = 0
    data["currentProgress1"] = 0
    data["totalProgress1"] = 0

    data["progressName2"] = None
    data["currentProgressLabel2"] = 0
    data["totalProgressLabel2"] = 0
    data["currentProgress2"] = 0
    data["totalProgress2"] = 0


def _update_progress_ui(api, task_id, progress: sly.Progress, index):
    fields = [
        {"field": f"data.progressName{index}", "payload": progress.message},
        {"field": f"data.currentProgressLabel{index}", "payload": progress.current_label},
        {"field": f"data.totalProgressLabel{index}", "payload": progress.total_label},
        {"field": f"data.currentProgress{index}", "payload": progress.current},
        {"field": f"data.totalProgress{index}", "payload": progress.total},
    ]
    api.task.set_fields(task_id, fields)


def _update_progress(count, index, api: sly.Api, task_id, progress: sly.Progress):
    progress.iters_done_report(count)
    _update_progress_ui(api, task_id, progress, index)


def get_progress_cb(api, task_id, index, message, total, is_size=False):
    progress = sly.Progress(message, total, is_size=is_size)
    progress_cb = partial(_update_progress, index=index, api=api, task_id=task_id, progress=progress)
    progress_cb(0)
    return progress_cb