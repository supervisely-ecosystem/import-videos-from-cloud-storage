import os
from pathlib import Path
import sys
import supervisely_lib as sly
import ui

app: sly.AppService = sly.AppService()
app_sources_dir = str(Path(sys.argv[0]).parents[1])


team_id = int(os.environ['context.teamId'])
workspace_id = int(os.environ['context.workspaceId'])

file_size = None


@app.callback("preview")
@sly.timeit
def preview(api: sly.Api, task_id, context, state, app_logger):
    global file_size
    file_size = {}

    path = f"{state['provider']}://{state['bucketName']}"
    try:
        files = api.remote_storage.list(path)
    except Exception as e:
        # @TODO: connection dialog message
        pass

    tree_items = []
    for file in files:
        path = os.path.join(f"/{state['bucketName']}", file["prefix"], file["name"])
        tree_items.append({
            "path": path,
            "size": file["size"]
        })
        file_size[path] = file["size"]

    fields = [
        {"field": "data.tree", "payload": tree_items},
    ]
    api.task.set_fields(task_id, fields)


@app.callback("process")
@sly.timeit
def process(api: sly.Api, task_id, context, state, app_logger):
    paths = state["selected"]

    remote_paths = []
    widget_paths = []
    local_paths = []

    def _add_to_processing_list(path):
        nonlocal remote_paths, local_paths
        if sly.video.has_valid_ext(path) is False:
            sly.logger.warning(f"Unsupported video extension for path: {path}")
            return
        full_remote_path = f"{state['provider']}://{path.lstrip('/')}"
        remote_paths.append(full_remote_path)
        widget_paths.append(path)
        local_path = os.path.join(app.data_dir, path.lstrip("/"))
        sly.fs.ensure_base_path(local_path)
        local_paths.append(local_path)

    # find selected dirs
    selected_dirs = []
    for path in paths:
        if sly.fs.get_file_ext(path) == '':
            # path to directory
            selected_dirs.append(path)

    # get all files from selected dirs
    if len(selected_dirs) > 0:
        for path in file_size.keys():
            if path in selected_dirs:
                continue
            if path.startswith(tuple(selected_dirs)):
                _add_to_processing_list(path)

    # get other selected files
    for path in paths:
        if sly.fs.get_file_ext(path) != '':
            _add_to_processing_list(path)

    if len(local_paths) == 0:
        #@TODO: show dialog message
        sly.logger.warn("nothing to download")
        return

    project = None
    if state["dstProjectMode"] == "newProject":
        project = api.project.create(workspace_id, state["dstProjectName"], sly.ProjectType.VIDEOS, change_name_if_conflict=True)
    elif state["dstProjectMode"] == "existingProject":
        project = api.project.get_info_by_id(state["dstProjectId"])
    if project is None:
        sly.logger.error("Result project is None (not found or not created)")
        return

    dataset = None
    if state["dstDatasetMode"] == "newDataset":
        dataset = api.dataset.create(project.id, state["dstDatasetName"], change_name_if_conflict=True)
    elif state["dstDatasetMode"] == "existingDataset":
        dataset = api.dataset.get_info_by_id(state["dstDatasetId"])
    if dataset is None:
        sly.logger.error("Result dataset is None (not found or not created)")
        return

    progress_items_cb = ui.get_progress_cb(api, task_id, 1, "Importing", len(remote_paths))
    for remote_path, temp_path, local_path in zip(remote_paths, widget_paths, local_paths):
        progress_file_cb = ui.get_progress_cb(api, task_id, 2,
                                              "Downloading to temp dir: {!r} ".format(temp_path),
                                              file_size[temp_path],
                                              is_size=True)
        api.remote_storage.download_path(remote_path, local_path, progress_file_cb)
        video_info = sly.video.get_info(local_path)
        video_name = sly.fs.get_file_name_with_ext(local_path)
        video_name = api.video.get_free_name(dataset.id, video_name)
        if state["addMode"] == "addBylink":
            h = sly.fs.get_file_hash(local_path)
            api.video.upload_links(dataset.id, names=[video_name], hashes=[h], links=[remote_path], infos=[video_info])
        elif state["addMode"] == "copyData":
            api.video.upload_paths(dataset.id, [video_name], [local_path], infos=[video_info])
        progress_items_cb(1)


def main():
    data = {}
    state = {}

    sly.fs.clean_dir(app.data_dir)  # @TODO: for debug

    ui.init_context(data, team_id, workspace_id)
    ui.init_connection(data, state)
    ui.init_options(data, state)
    ui.init_progress(data, state)

    app.run(data=data, state=state)

# @TODO: uncommend UI debug values
#@TODO: filter project - keep only video projects (update widget sly-project-selector)
#@TODO: add error text if destination dataset/project is not defined
#@TODO: release new SDK and change ersion in config
#@TODO: progres bars
#@TODO: set correct instance_version
#@TODO: TONY - fix arguments description in docs remote-storage.bulk.download
#@TODO: download from cloud API - not working
# https://docs.supervise.ly/enterprise-edition/advanced-tuning/s3#links-plugin-cloud-providers-support
if __name__ == "__main__":
    sly.main_wrapper("main", main)
