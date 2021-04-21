import os
from pathlib import Path
import sys
import supervisely_lib as sly
import gcs
from hurry.filesize import size as fsize


app: sly.AppService = sly.AppService()
app_repo_dir = str(Path(sys.argv[0]).parents[1])


team_id = int(os.environ['context.teamId'])
workspace_id = int(os.environ['context.workspaceId'])


#@ui.handle_exceptions(app.task_id, app.public_api)
@app.callback("preview")
@sly.timeit
def preview(api: sly.Api, task_id, context, state, app_logger):
    pass


def test():
    # cred_path = os.path.join(app_repo_dir, "gcs_debug_creds.json")
    # gcs.init(cred_path)
    #
    # bucket_name = "surgar-bigdata-bucket-01"
    # tree = []
    # blobs = gcs.list_blobs(bucket_name)
    # for blob in blobs:
    #     tree.append({
    #         "path": blob.name,
    #         "size": blob.size
    #     })
    #     print(blob.name, ": ", fsize(blob.size))
    #
    # video_path = "test-supervisely/2019-11-19_122223_VID014.mp4"
    # save_path = os.path.join(app.data_dir, video_path)
    # #gcs.download_file(bucket_name, video_path, save_path)
    # gcs.streaming_download(bucket_name, video_path, save_path)

    video_path = os.path.join(app.data_dir, "sample-mp4-file.mp4")
    res = sly.video.get_info(video_path)


def main():
    test()
    exit(0)

    data = {}
    state = {}

    app.run(data=data, state=state)


if __name__ == "__main__":
    sly.main_wrapper("main", main)
