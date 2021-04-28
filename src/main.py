import os
import time
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
        app.show_modal_window("Can not find bucket or permission denied. Please, check if provider / bucket name are "
                              "correct or contact tech support", level="warning")
        fields = [
            {"field": "data.tree", "payload": None},
            {"field": "data.connecting", "payload": False},
        ]
        api.task.set_fields(task_id, fields)
        return

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
        {"field": "data.connecting", "payload": False},
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
        app.show_modal_window("There are no videos to import", "warning")
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

    progress_items_cb = ui.get_progress_cb(api, task_id, 1, "Finished", len(remote_paths))
    for remote_path, temp_path, local_path in zip(remote_paths, widget_paths, local_paths):
        progress_file_cb = ui.get_progress_cb(api, task_id, 2,
                                              "Downloading to temp dir: {!r} ".format(temp_path),
                                              file_size[temp_path],
                                              is_size=True)
        api.remote_storage.download_path(remote_path, local_path, progress_file_cb)
        temp_cb = ui.get_progress_cb(api, task_id, 2, "Processing: {!r} ".format(temp_path), 1, is_size=False, func=ui.set_progress)
        video_info = sly.video.get_info(local_path)
        temp_cb(1)
        video_name = sly.fs.get_file_name_with_ext(local_path)
        video_name = api.video.get_free_name(dataset.id, video_name)
        if state["addMode"] == "addBylink":
            h = sly.fs.get_file_hash(local_path)
            api.video.upload_links(dataset.id, names=[video_name], hashes=[h], links=[remote_path], infos=[video_info])
        elif state["addMode"] == "copyData":
            progress_upload_cb = ui.get_progress_cb(api, task_id, 2,
                                                    "Uploading to Supervisely: {!r} ".format(temp_path),
                                                    sly.fs.get_file_size(local_path),  # file_size[temp_path]  #@TODO: file lengths in monitor and in the cloud slightly are different
                                                    is_size=True,
                                                    func=ui.set_progress)
            api.video.upload_paths(dataset.id, [video_name], [local_path], infos=[video_info], item_progress=progress_upload_cb)
        progress_items_cb(1)

    ui.reset_progress(api, task_id, 1)
    ui.reset_progress(api, task_id, 2)
    app.show_modal_window(f"{len(remote_paths)} videos has been successfully imported to the project \"{project.name}\""
                          f", dataset \"{dataset.name}\". You can continue importing other videos to the same or new "
                          f"project. If you've finished with the app, stop it manually.")
    api.app.set_field(task_id, "data.processing", False)
    api.task.set_output_project(task_id, project.id, project.name)


def main():
    data = {}
    state = {}

    ui.init_context(data, team_id, workspace_id)
    ui.init_connection(data, state)
    ui.init_options(data, state)
    ui.init_progress(data, state)

    app.run(data=data, state=state)


if __name__ == "__main__":
    sly.main_wrapper("main", main)
