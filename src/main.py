import os
from pathlib import Path
import sys
import supervisely_lib as sly


app: sly.AppService = sly.AppService()
app_sources_dir = str(Path(sys.argv[0]).parents[1])


team_id = int(os.environ['context.teamId'])
workspace_id = int(os.environ['context.workspaceId'])


#@ui.handle_exceptions(app.task_id, app.public_api)
@app.callback("preview")
@sly.timeit
def preview(api: sly.Api, task_id, context, state, app_logger):
    pass


def test():
    pass


def main():
    #test()
    #exit(0)

    data = {}
    state = {}

    app.run(data=data, state=state)


#@TODO: set correct instance_version
if __name__ == "__main__":
    sly.main_wrapper("main", main)
