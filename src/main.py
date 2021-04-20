import os

import supervisely_lib as sly


app: sly.AppService = sly.AppService()

team_id = int(os.environ['context.teamId'])
workspace_id = int(os.environ['context.workspaceId'])


#@ui.handle_exceptions(app.task_id, app.public_api)

@app.callback("preview")
@sly.timeit
def preview(api: sly.Api, task_id, context, state, app_logger):
    pass


def main():
    data = {}
    state = {}

    app.run(data=data, state=state)


if __name__ == "__main__":
    sly.main_wrapper("main", main)
