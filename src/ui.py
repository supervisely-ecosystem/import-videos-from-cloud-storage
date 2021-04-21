import supervisely_lib as sly


def init_bucket_preview(data, state):
    state["bucketName"] = ""
    state["selected"] = ""
    data["tree"] = None
