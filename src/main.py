import os
import posixpath

import supervisely as sly

import globals as g
import workflow as w
import ui

from utils import copy_videos_from_cloud


@g.app.callback("refresh_tree_viewer")
@sly.timeit
def refresh_tree_viewer(api: sly.Api, task_id, context, state, app_logger):
    new_path = state["viewerPath"]
    g.FILE_SIZE = {}

    path = f"{state['provider']}://{new_path.strip('/')}"
    try:
        files = api.remote_storage.list(
            path, recursive=False, limit=g.USER_PREVIEW_LIMIT + 1, team_id=g.TEAM_ID
        )
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

    files = [
        f
        for f in files
        if f["type"] == "folder" or (f["type"] == "file" and f["size"] > 0)
    ]

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
        files = api.remote_storage.list(
            path, recursive=False, limit=g.USER_PREVIEW_LIMIT + 1, team_id=g.TEAM_ID
        )
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

    files = [
        f
        for f in files
        if f["type"] == "folder" or (f["type"] == "file" and f["size"] > 0)
    ]
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

    added_paths = set()
    skipped_unsupported = []

    def _add_to_processing_list(path):
        nonlocal remote_paths, local_paths
        if path in added_paths:  # a file selected both directly and inside a selected folder
            return
        added_paths.add(path)
        if sly.video.has_valid_ext(path) is False:
            sly.logger.warning(f"Unsupported video extension for path: {path}")
            skipped_unsupported.append(path)
            return
        full_remote_path = f"{state['provider']}://{path.lstrip('/')}"
        remote_paths.append(full_remote_path)
        widget_paths.append(path)
        # Bucket keys may contain "..", or be longer than a local file name may be:
        # the local copy gets a name of its own inside the app temp dir.
        local_path = safe_local_path(g.app.data_dir, len(local_paths), path)
        local_paths.append(local_path)

    # find selected dirs
    selected_dirs = []
    not_found = []  # selected items that can not be imported: (path, reason)
    for path in paths:
        if path["type"] == "folder":
            if "/" not in path["path"].strip("/"):
                # A folder with an empty name (keys that start with "/") is shown as
                # "/<bucket>/"; listing it would list - and import - the whole bucket.
                sly.logger.warning(f"Folder with an empty name is skipped: {path['path']!r}")
                not_found.append((path["path"], "a folder with an empty name can not be listed"))
                continue
            # path to directory
            selected_dirs.append(path["path"])

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
                path = os.path.join(
                    f"/{state['bucketName']}", file["prefix"], file["name"]
                )
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
    if g.FILE_SIZE is None:
        g.FILE_SIZE = {}
    for path in paths:
        if path["type"] == "file":
            try:
                full_remote_path = f"{state['provider']}://{path['path'].lstrip('/')}"
                file = api.remote_storage.get_file_info_by_path(path=full_remote_path, team_id=g.TEAM_ID)
            except Exception as e:  # the SDK raises IndexError when nothing is found
                sly.logger.warning(f"Couldn't find file: {path['path']}: {e!r}")
                not_found.append((path["path"], "not found in the storage"))
                continue
            g.FILE_SIZE[path["path"]] = file["size"]
            _add_to_processing_list(path["path"])

    if len(local_paths) == 0:
        g.app.show_modal_window("There are no videos to import", "warning")
        sly.logger.warn("nothing to download")
        api.app.set_field(task_id, "data.processing", False)
        return

    project, dataset, created = None, None, []
    try:
        project, dataset, created = get_destination(api, state)
    finally:
        if dataset is None:
            api.app.set_field(task_id, "data.processing", False)
    if dataset is None:
        return

    used_names = set()
    if state["addMode"] == "addBylink":
        used_names = {info.name for info in api.video.get_list(dataset.id)}

    imported = 0
    failed = list(not_found)
    planned = len(remote_paths) + len(not_found)
    progress_items_cb = ui.get_progress_cb(
        api, task_id, 1, "Finished", len(remote_paths)
    )
    for remote_paths_batch, temp_paths_batch, local_paths_batch in zip(
        sly.batched(remote_paths), sly.batched(widget_paths), sly.batched(local_paths)
    ):
        if state["addMode"] == "addBylink":
            # names must be unique in the dataset: "a/clip.mp4" and "b/clip.mp4" -> clip, clip_01
            video_names = [
                free_name(used_names, posixpath.basename(path)) for path in temp_paths_batch
            ]
            imported += upload_with_fallback(
                lambda names, links: api.video.upload_links(
                    dataset.id, links=links, names=names, skip_download=True
                ),
                video_names,
                remote_paths_batch,
                temp_paths_batch,
                failed,
            )
            progress_items_cb(len(remote_paths_batch))

        elif state["addMode"] == "copyData":
            imported += copy_videos_from_cloud(
                api,
                task_id,
                dataset,
                remote_paths_batch,
                temp_paths_batch,
                local_paths_batch,
                progress_items_cb,
                failed,
            )
    ui.reset_progress(api, task_id, 1)
    ui.reset_progress(api, task_id, 2)
    sly.logger.info(
        "Import summary",
        extra={"planned": planned, "imported": imported, "failed": len(failed),
               "skipped_unsupported": len(skipped_unsupported)},
    )

    if imported == 0:
        remove_if_empty(api, created)
        message = (
            f"No videos were imported: all {planned} selected videos failed. "
            + describe_failures(failed)
        )
        g.app.show_modal_window(message, "error")
        raise RuntimeError(message)

    if state["dstProjectMode"] == "newProject":
        w.workflow_output(api, project.id, type="project")
    else:
        w.workflow_output(api, dataset.id, type="dataset")
    api.task.set_output_project(task_id, project.id, project.name)

    if failed:
        message = (
            f"Import is incomplete: {len(failed)} of {planned} videos failed, "
            f'{imported} were imported to the project "{project.name}", dataset "{dataset.name}". '
            + describe_failures(failed)
        )
        g.app.show_modal_window(message, "error")
        raise RuntimeError(message)

    skipped_note = ""
    if skipped_unsupported:
        skipped_note = (
            f" {len(skipped_unsupported)} file(s) skipped: not a supported video extension"
            f" (see the app log)."
        )
    g.app.show_modal_window(
        f'{imported} videos has been successfully imported to the project "{project.name}"'
        f', dataset "{dataset.name}".{skipped_note} You can continue importing other videos to the '
        f"same or new project. If you've finished with the app, stop it manually."
    )
    api.app.set_field(task_id, "data.processing", False)


def get_destination(api: sly.Api, state: dict):
    """Returns (project, dataset, created) for the GUI choice; `created` lists what this run created
    as ("project" | "dataset", id). Shows an error and returns dataset None if the choice is gone."""
    created = []
    project = None
    if state["dstProjectMode"] == "newProject":
        project = api.project.create(
            g.WORKSPACE_ID,
            state["dstProjectName"],
            sly.ProjectType.VIDEOS,
            change_name_if_conflict=True,
        )
        created.append(("project", project.id))
    elif state["dstProjectMode"] == "existingProject":
        project = api.project.get_info_by_id(state["dstProjectId"])
    if project is None:
        message = f"Result project (id {state.get('dstProjectId')}) is not found. Select another project."
        sly.logger.error(message)
        g.app.show_modal_window(message, "error")
        return None, None, created

    dataset = None
    if state["dstDatasetMode"] == "newDataset":
        dataset = api.dataset.create(
            project.id, state["dstDatasetName"], change_name_if_conflict=True
        )
        created.append(("dataset", dataset.id))
    elif state["dstDatasetMode"] == "existingDataset":
        name = state["selectedDatasetName"]
        dataset = api.dataset.get_info_by_name(project.id, name)
        if dataset is None:  # a nested dataset: look in the whole tree, use it if the name is unique
            matches = [
                ds
                for ds in api.dataset.get_list(
                    project.id, filters=[{"field": "name", "operator": "=", "value": name}],
                    recursive=True,
                )
                if ds.name == name
            ]
            dataset = matches[0] if len(matches) == 1 else None
    if dataset is None:
        message = (
            f'Result dataset "{state.get("selectedDatasetName")}" is not found (or its name is not '
            f'unique) in the project "{project.name}". Select another dataset.'
        )
        sly.logger.error(message)
        g.app.show_modal_window(message, "error")
        remove_if_empty(api, created)
        return project, None, created
    return project, dataset, created


def upload_with_fallback(upload, names, sources, paths, failed) -> int:
    """Uploads one batch; if the batch fails, uploads its halves separately (down to single items)
    so that one bad file does not fail the others. Records failures in `failed`; returns the number
    of uploaded items."""
    try:
        upload(names, sources)
        return len(names)
    except Exception as e:
        if len(names) == 1:
            sly.logger.warning(f"Failed to import {paths[0]!r}: {e!r}")
            failed.append((paths[0], repr(e)))
            return 0
        sly.logger.warning(f"Batch of {len(names)} videos failed ({e!r}), retrying in parts")
    half = len(names) // 2
    return upload_with_fallback(
        upload, names[:half], sources[:half], paths[:half], failed
    ) + upload_with_fallback(upload, names[half:], sources[half:], paths[half:], failed)


def describe_failures(failed, limit: int = 5) -> str:
    shown = "; ".join(f"{path}: {reason}" for path, reason in failed[:limit])
    more = f"; and {len(failed) - limit} more (see the app log)" if len(failed) > limit else ""
    return f"Failed: {shown}{more}."


def remove_if_empty(api: sly.Api, created) -> None:
    """Removes what this run created (the project, else the dataset), only if the server reports
    it empty. Projects and datasets the user selected are never removed."""
    kinds = dict(created)
    kind = "project" if "project" in kinds else "dataset" if "dataset" in kinds else None
    if kind is None:
        return
    module = api.project if kind == "project" else api.dataset
    try:
        info = module.get_info_by_id(kinds[kind])
        if info is not None and info.items_count == 0:
            module.remove(kinds[kind])
            sly.logger.info(f"Removed the empty {kind} {kinds[kind]} created by this import")
    except Exception as e:
        sly.logger.warning(f"Could not remove the empty {kind} {kinds[kind]}: {e!r}")


def safe_local_path(data_dir: str, index: int, remote_path: str) -> str:
    """Local download path for a remote file: always directly inside `data_dir/downloads`."""
    ext = sly.fs.get_file_ext(posixpath.basename(remote_path))
    if len(ext) > 16 or "/" in ext or "\\" in ext:
        ext = ""
    local_path = os.path.join(data_dir, "downloads", f"{index:08d}{ext}")
    sly.fs.ensure_base_path(local_path)
    return local_path


def free_name(used_names: set, name: str) -> str:
    """`name`, or `name_01.ext`, `name_02.ext`, ... if taken; adds the result to `used_names`."""
    res = name
    suffix = 1
    stem, ext = sly.fs.get_file_name(name), sly.fs.get_file_ext(name)
    while res in used_names:
        res = f"{stem}_{suffix:02d}{ext}"
        suffix += 1
    used_names.add(res)
    return res


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
            team_id=g.TEAM_ID,
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
