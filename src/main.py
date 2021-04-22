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
        path = os.path.join(f"/{state['bucketName']}", file["prefix"], file["name"])
        # if file["type"] == "folder":
        #     path += "/"
        tree_items.append({
            "path": os.path.join(f"/{state['bucketName']}", file["prefix"], file["name"]),
            "size": file["size"]
        })
    fields = [
        {"field": "data.tree", "payload": tree_items},
    ]
    api.task.set_fields(task_id, fields)


def main():
    data = {}
    state = {}

    ui.init_context(data, team_id, workspace_id)
    ui.init_connection(data, state)
    ui.init_options(data, state)

    app.run(data=data, state=state)


#@TODO: set correct instance_version
# https://docs.supervise.ly/enterprise-edition/advanced-tuning/s3#links-plugin-cloud-providers-support
if __name__ == "__main__":
    sly.main_wrapper("main", main)
