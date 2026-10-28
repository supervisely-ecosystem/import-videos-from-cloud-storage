import posixpath
from typing import Callable, List, Tuple

import supervisely as sly
from supervisely.io.fs import silent_remove

import globals as g
import ui


def copy_videos_from_cloud(
    api: sly.Api,
    task_id: int,
    dataset: sly.DatasetInfo,
    remote_paths_batch: List[str],
    temp_paths_batch: List[str],
    local_paths_batch: List[str],
    progress_items_cb: Callable,
    failed: List[Tuple[str, str]],
) -> int:
    """Downloads and uploads the videos one by one. A video that fails (download error, unreadable
    video, upload error or dropped by the server) is recorded in `failed` and the rest continues.
    Returns the number of imported videos."""
    imported = 0
    for remote_path, temp_path, local_path in zip(
        remote_paths_batch, temp_paths_batch, local_paths_batch
    ):
        progress_file_cb = ui.get_progress_cb(
            api,
            task_id,
            2,
            "Downloading to temp dir: {!r} ".format(temp_path),
            g.FILE_SIZE[temp_path],
            is_size=True,
        )
        try:
            api.remote_storage.download_path(
                remote_path, local_path, progress_file_cb, team_id=g.TEAM_ID
            )
            reason = _upload_video(api, task_id, dataset, temp_path, local_path)
        except Exception as e:
            reason = repr(e)
        finally:
            silent_remove(local_path)  # cleanup, also when the video failed
        if reason is None:
            imported += 1
        else:
            sly.logger.warning(f"Failed to import {temp_path!r}: {reason}")
            failed.append((temp_path, reason))
        progress_items_cb(1)
    return imported


def _upload_video(api, task_id, dataset, temp_path, local_path):
    """Returns None when the video is imported, else the reason it was not."""
    temp_cb = ui.get_progress_cb(
        api,
        task_id,
        2,
        "Processing: {!r} ".format(temp_path),
        1,
        is_size=False,
        func=ui.set_progress,
    )
    try:
        sly.video.get_info(local_path)
    except Exception as e:
        temp_cb(1)
        return f"not a readable video: {e}"
    temp_cb(1)
    video_name = posixpath.basename(temp_path)
    video_name = api.video.get_free_name(dataset.id, video_name)
    progress_upload_cb = ui.get_progress_cb(
        api,
        task_id,
        2,
        "Uploading to Supervisely: {!r} ".format(temp_path),
        sly.fs.get_file_size(local_path),
        is_size=True,
        func=ui.set_progress,
    )
    infos = api.video.upload_paths(
        dataset.id,
        [video_name],
        [local_path],
        item_progress=progress_upload_cb,
    )
    if not infos:
        # VideoApi.upload_paths logs "File skipped ..." and returns nothing when the server
        # fails to process the video
        return "the server could not process the video (see 'File skipped' in the app log)"
    return None
