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
    def filter(path):
        return False if "/venv" in path else True

    files = sly.fs.list_files_recursively(app_sources_dir, filter_fn=filter)

    tree_items = []
    for file in files:
        tree_items.append({
            "path": file,
            "size": 1234
        })
    fields = [
        {"field": "data.tree", "payload": tree_items},
    ]
    api.task.set_fields(task_id, fields)


def main():
    data = {}
    state = {}

    ui.init_bucket_preview(data, state)

    app.run(data=data, state=state)


#@TODO: set correct instance_version
if __name__ == "__main__":
    sly.main_wrapper("main", main)
