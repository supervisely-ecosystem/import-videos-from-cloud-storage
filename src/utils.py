from typing import Callable, List
import supervisely as sly
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
    skipped_videos: int = 0,
):
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
        api.remote_storage.download_path(remote_path, local_path, progress_file_cb)
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
            video_info = sly.video.get_info(local_path)
        except Exception as e:
            sly.logger.warn(f"Couldn't read video info for file: {local_path}. Error: {e}")
            skipped_videos += 1
            temp_cb(1)
            progress_items_cb(1)
            continue
        temp_cb(1)
        video_name = sly.fs.get_file_name_with_ext(local_path)
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
        api.video.upload_paths(
            dataset.id,
            [video_name],
            [local_path],
            infos=[video_info],
            item_progress=progress_upload_cb,
        )
        progress_items_cb(1)
    return skipped_videos
