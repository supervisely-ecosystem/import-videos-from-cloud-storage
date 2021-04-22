import os
from pathlib import Path
import sys
import supervisely_lib as sly
import ui

app: sly.AppService = sly.AppService()
app_sources_dir = str(Path(sys.argv[0]).parents[1])


team_id = int(os.environ['context.teamId'])
workspace_id = int(os.environ['context.workspaceId'])


@app.callback("preview")
@sly.timeit
def preview(api: sly.Api, task_id, context, state, app_logger):
    path = f"{state['provider']}://{state['bucketName']}"
    try:
        files = api.remote_storage.list(path)
    except Exception as e:
        # @TODO: connection dialog message
        pass

    # def filter(path):
    #     return False if "/venv" in path else True
    # files = sly.fs.list_files_recursively(app_sources_dir, filter_fn=filter)

    tree_items = []
    for file in files:
        if file["type"] == "folder":
            #path += "/" #@TODO: fix in widget
            continue
        path = os.path.join(f"/{state['bucketName']}", file["prefix"], file["name"])
        tree_items.append({
            "path": path,
            "size": file["size"]
        })
    fields = [
        {"field": "data.tree", "payload": tree_items},
    ]
    api.task.set_fields(task_id, fields)


@app.callback("process")
@sly.timeit
def process(api: sly.Api, task_id, context, state, app_logger):
    paths = state["selected"]

    remote_paths = []
    local_paths = []

    for path in paths:
        if sly.video.has_valid_ext(path) is False:
            sly.logger.warning(f"Unsupported video extension for path: {path}")
            continue
        full_remote_path = f"{state['provider']}://{state['bucketName']}{path}"
        remote_paths.append(full_remote_path)
        local_path = os.path.join(app.data_dir, path.lstrip("/"))
        sly.fs.ensure_base_path(local_path)
        local_paths.append(local_path)

    if len(local_paths) == 0:
        #@TODO: show dialog message
        sly.logger.warn("nothing to download")
        return

    api.remote_storage.download_paths(remote_paths, local_paths)


def main():
    data = {}
    state = {}

    ui.init_context(data, team_id, workspace_id)
    ui.init_connection(data, state)
    ui.init_options(data, state)

    app.run(data=data, state=state)


#@TODO: set correct instance_version
#@TODO: TONY - fix arguments description in docs remote-storage.bulk.download
#@TODO: download from cloud API - not working
# https://docs.supervise.ly/enterprise-edition/advanced-tuning/s3#links-plugin-cloud-providers-support
if __name__ == "__main__":
    sly.main_wrapper("main", main)
