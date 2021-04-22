import supervisely_lib as sly


def init_context(data, team_id, workspace_id):
    data["teamId"] = team_id
    data["workspaceId"] = workspace_id


def init_bucket_preview(data, state):
    state["bucketName"] = ""
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
