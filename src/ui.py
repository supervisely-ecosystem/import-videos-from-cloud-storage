import supervisely_lib as sly


def init_context(data, team_id, workspace_id):
    data["teamId"] = team_id
    data["workspaceId"] = workspace_id


def init_connection(data, state):
    # @TODO: for debug ""
    state["provider"] = "google" #"s3" # "google"
    state["bucketName"] = "surgar-bigdata-bucket-01" #"remote-img-test/" #"surgar-bigdata-bucket-01"
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
