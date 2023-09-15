import os

import supervisely as sly

import globals as g
import ui

from utils import copy_videos_from_cloud


@g.app.callback("refresh_tree_viewer")
@sly.timeit
def refresh_tree_viewer(api: sly.Api, task_id, context, state, app_logger):
    new_path = state["viewerPath"]
    g.FILE_SIZE = {}

    path = f"{state['provider']}://{new_path.strip('/')}"
    try:
        files = api.remote_storage.list(path, recursive=False, limit=g.USER_PREVIEW_LIMIT + 1)
    except Exception as e:
        sly.logger.warn(repr(e))
        g.app.show_modal_window(
            "Can not find bucket or permission denied. Please, check if provider / bucket name are "
            "correct or contact tech support",
            level="warning",
        )
        fields = [
            {"field": "data.tree", "payload": None},
            {"field": "data.connecting", "payload": False},
            {"field": "state.viewerLoading", "payload": False},
        ]
        api.task.set_fields(task_id, fields)
        return

    files = [f for f in files if f["type"] == "folder" or (f["type"] == "file" and f["size"] > 0)]

    if len(files) > g.USER_PREVIEW_LIMIT:
        files.pop()
        g.app.show_modal_window(
            f"Found too many files. Showing the first {g.USER_PREVIEW_LIMIT} files"
        )

    tree_items = []
    for file in files:
        state["bucketName"] = state["bucketName"].split("/")[0]
        path = os.path.join(f"/{state['bucketName']}", file["prefix"], file["name"])
        tree_items.append({"path": path, "size": file["size"], "type": file["type"]})
        g.FILE_SIZE[path] = file["size"]

    fields = [
        {"field": "data.tree", "payload": tree_items},
        {"field": "state.viewerLoading", "payload": False},
    ]
    api.task.set_fields(task_id, fields)


@g.app.callback("preview")
@sly.timeit
def preview(api: sly.Api, task_id, context, state, app_logger):
    g.FILE_SIZE = {}

    path = f"{state['provider']}://{state['bucketName']}"
    try:
        files = api.remote_storage.list(path, recursive=False, limit=g.USER_PREVIEW_LIMIT + 1)
    except Exception as e:
        g.app.show_modal_window(
            "Can not find bucket or permission denied. Please, check if provider / bucket name are "
            "correct or contact tech support",
            level="warning",
        )
        fields = [
            {"field": "data.tree", "payload": None},
            {"field": "data.connecting", "payload": False},
        ]
        api.task.set_fields(task_id, fields)
        return

    files = [f for f in files if f["type"] == "folder" or (f["type"] == "file" and f["size"] > 0)]
    if len(files) > g.USER_PREVIEW_LIMIT:
        files.pop()
        g.app.show_modal_window(
            f"Found too many files. Showing the first {g.USER_PREVIEW_LIMIT} files"
        )

    tree_items = []
    for file in files:
        state["bucketName"] = state["bucketName"].split("/")[0]
        path = os.path.join(f"/{state['bucketName']}", file["prefix"], file["name"])
        tree_items.append({"path": path, "size": file["size"], "type": file["type"]})
        g.FILE_SIZE[path] = file["size"]

    fields = [
        {"field": "data.tree", "payload": tree_items},
        {"field": "data.connecting", "payload": False},
    ]
    api.task.set_fields(task_id, fields)


@g.app.callback("process")
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
        local_path = os.path.join(g.app.data_dir, path.lstrip("/"))
        sly.fs.ensure_base_path(local_path)
        local_paths.append(local_path)

    # find selected dirs
    selected_dirs = []
    for path in paths:
        if sly.fs.get_file_ext(path) == "":
            # path to directory
            selected_dirs.append(path)

    # get all files from selected dirs
    if len(selected_dirs) > 0:
        g.FILE_SIZE = {}
        for dir_path in selected_dirs:
            full_dir_path = f"{state['provider']}://{dir_path.strip('/')}"
            files_cnt = 0
            for file in list_objects(api, full_dir_path):
                if file["size"] <= 0:
                    continue

                state["bucketName"] = state["bucketName"].split("/")[0]
                path = os.path.join(f"/{state['bucketName']}", file["prefix"], file["name"])
                g.FILE_SIZE[path] = file["size"]
                files_cnt += 1
                if files_cnt % 10000 == 0:
                    sly.logger.info(f"Listing files from remote storage {files_cnt}")

        for path in g.FILE_SIZE.keys():
            if path in selected_dirs:
                continue
            if path.startswith(tuple(selected_dirs)):
                _add_to_processing_list(path)

    # get other selected files
    for path in paths:
        if sly.fs.get_file_ext(path) != "":
            try:
                full_remote_path = f"{state['provider']}://{path.lstrip('/')}"
                file = api.remote_storage.get_file_info_by_path(path=full_remote_path)
                g.FILE_SIZE[path] = file["size"]
                _add_to_processing_list(path)
            except FileNotFoundError as e:
                sly.logger.warn(f"Couldn't find file: {path}")
                continue

    if len(local_paths) == 0:
        g.app.show_modal_window("There are no videos to import", "warning")
        sly.logger.warn("nothing to download")
        api.app.set_field(task_id, "data.processing", False)
        return

    project = None
    if state["dstProjectMode"] == "newProject":
        project = api.project.create(
            g.WORKSPACE_ID,
            state["dstProjectName"],
            sly.ProjectType.VIDEOS,
            change_name_if_conflict=True,
        )
    elif state["dstProjectMode"] == "existingProject":
        project = api.project.get_info_by_id(state["dstProjectId"])
    if project is None:
        sly.logger.error("Result project is None (not found or not created)")
        return

    dataset = None
    if state["dstDatasetMode"] == "newDataset":
        dataset = api.dataset.create(
            project.id, state["dstDatasetName"], change_name_if_conflict=True
        )
    elif state["dstDatasetMode"] == "existingDataset":
        dataset = api.dataset.get_info_by_name(project.id, state["selectedDatasetName"])
    if dataset is None:
        sly.logger.error("Result dataset is None (not found or not created)")
        return

    skipped_videos = 0
    progress_items_cb = ui.get_progress_cb(api, task_id, 1, "Finished", len(remote_paths))
    for remote_paths_batch, temp_paths_batch, local_paths_batch in zip(
        sly.batched(remote_paths), sly.batched(widget_paths), sly.batched(local_paths)
    ):
        if state["addMode"] == "addBylink":
            video_names = [
                sly.fs.get_file_name_with_ext(local_path) for local_path in local_paths_batch
            ]
            api.video.upload_links(
                dataset.id, links=remote_paths_batch, names=video_names, skip_download=True
            )
            progress_items_cb(len(remote_paths_batch))

        elif state["addMode"] == "copyData":
            skipped_videos = copy_videos_from_cloud(
                api,
                task_id,
                dataset,
                remote_paths_batch,
                temp_paths_batch,
                local_paths_batch,
                progress_items_cb,
                skipped_videos,
            )
            skipped_videos += skipped_videos

    ui.reset_progress(api, task_id, 1)
    ui.reset_progress(api, task_id, 2)
    g.app.show_modal_window(
        f'{len(remote_paths)-skipped_videos} videos has been successfully imported to the project "{project.name}"'
        f', dataset "{dataset.name}". You can continue importing other videos to the same or new '
        f"project. If you've finished with the app, stop it manually."
    )
    api.app.set_field(task_id, "data.processing", False)
    api.task.set_output_project(task_id, project.id, project.name)


def list_objects(api, full_dir_path):
    start_after = None
    last_obj = None
    while True:
        remote_objs = api.remote_storage.list(
            path=full_dir_path,
            files=True,
            folders=False,
            recursive=True,
            start_after=start_after,
        )
        if len(remote_objs) == 0:
            break
        if last_obj is not None:
            if remote_objs[-1] == last_obj:
                break
        last_obj = remote_objs[-1]
        start_after = f'{last_obj["prefix"]}/{last_obj["name"]}'
        yield from remote_objs


def main():
    data = {}
    state = {}

    ui.init_context(data, g.TEAM_ID, g.WORKSPACE_ID)
    ui.init_connection(data, state)
    ui.init_options(data, state)
    ui.init_progress(data, state)

    g.app.run(data=data, state=state)


if __name__ == "__main__":
    sly.main_wrapper("main", main)
