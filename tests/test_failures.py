"""Partial and failed imports are reported as failures and leave no empty project behind."""

from conftest import UNREADABLE_SIZE, FakeApi, make_state

FILES = {"bkt/x/1.mp4": 3, "bkt/x/2.mp4": 3, "bkt/x/3.mp4": 3}


def _error_modals(g):
    return [m for m, level in g.app.modals if level == "error"]


def test_unreadable_video_fails_the_import_and_counts_right(app):
    api = FakeApi({**FILES, "bkt/x/2.mp4": UNREADABLE_SIZE})
    main, g, error = app(api, make_state([("/bkt/x", "folder")]))
    assert sorted(api.datasets[api.created_datasets[0]]) == ["1.mp4", "3.mp4"]
    assert error is not None and "1 of 3" in str(error) and "2 were imported" in str(error)
    assert "/bkt/x/2.mp4" in str(error)
    assert not any("successfully" in m for m, _ in g.app.modals)
    assert api.output_project == api.created_projects[0]


def test_video_dropped_by_the_server_is_a_failure(app):
    # VideoApi.upload_paths logs "File skipped ..." and returns nothing for such a video.
    api = FakeApi(FILES, rejects=["3.mp4"])
    main, g, error = app(api, make_state([("/bkt/x", "folder")]))
    assert sorted(api.datasets[api.created_datasets[0]]) == ["1.mp4", "2.mp4"]
    assert error is not None and "1 of 3" in str(error)


def test_download_failure_imports_the_rest_and_fails(app):
    api = FakeApi(FILES, download_fails=["bkt/x/1.mp4"])
    main, g, error = app(api, make_state([("/bkt/x", "folder")]))
    assert sorted(api.datasets[api.created_datasets[0]]) == ["2.mp4", "3.mp4"]
    assert error is not None and "1 of 3" in str(error)


def test_link_mode_rejection_keeps_the_rest(app):
    api = FakeApi(FILES, rejects=["2.mp4"])
    main, g, error = app(api, make_state([("/bkt/x", "folder")], add_mode="addBylink"))
    assert sorted(api.datasets[api.created_datasets[0]]) == ["1.mp4", "3.mp4"]
    assert error is not None and "1 of 3" in str(error)


def test_nothing_imported_removes_the_new_project(app):
    api = FakeApi({k: UNREADABLE_SIZE for k in FILES})
    main, g, error = app(api, make_state([("/bkt/x", "folder")]))
    assert error is not None and "No videos were imported" in str(error)
    assert api.removed_projects == api.created_projects == [100]
    assert api.output_project is None


def test_nothing_imported_into_existing_project_removes_only_the_new_dataset(app):
    api = FakeApi(FILES, rejects=["1.mp4", "2.mp4", "3.mp4"],
                  existing_project=(7, {70: ("ds", None, ["old.mp4"])}))
    main, g, error = app(api, make_state([("/bkt/x", "folder")], project_id=7))
    assert error is not None
    assert api.removed_projects == []
    assert api.removed_datasets == api.created_datasets and len(api.created_datasets) == 1
    assert api.datasets[70] == ["old.mp4"]


def test_nothing_imported_into_existing_dataset_removes_nothing(app):
    api = FakeApi(FILES, rejects=["1.mp4", "2.mp4", "3.mp4"],
                  existing_project=(7, {70: ("ds", None, [])}))
    main, g, error = app(api, make_state([("/bkt/x", "folder")], project_id=7, dataset_name="ds"))
    assert error is not None
    assert api.removed_projects == [] and api.removed_datasets == []


def test_selected_file_gone_is_a_failure(app):
    api = FakeApi(FILES)
    state = make_state([("/bkt/x/1.mp4", "file"), ("/bkt/x/deleted.mp4", "file")])
    main, g, error = app(api, state)
    assert api.datasets[api.created_datasets[0]] == ["1.mp4"]
    assert error is not None and "/bkt/x/deleted.mp4" in str(error)


def test_existing_project_not_found_shows_error_and_unlocks_the_button(app):
    api = FakeApi(FILES)
    main, g, error = app(api, make_state([("/bkt/x", "folder")], project_id=404))
    assert _error_modals(g)
    assert api.fields.get("data.processing") is False
    assert api.created_datasets == []


def test_existing_nested_dataset_is_found(app):
    api = FakeApi(FILES, existing_project=(7, {70: ("parent", None, []), 71: ("child", 70, [])}))
    main, g, error = app(api, make_state([("/bkt/x", "folder")], project_id=7, dataset_name="child"))
    assert error is None
    assert sorted(api.datasets[71]) == ["1.mp4", "2.mp4", "3.mp4"]


def test_success_message_counts(app):
    api = FakeApi({"bkt/x/1.mp4": 3, "bkt/x/notes.txt": 3})
    main, g, error = app(api, make_state([("/bkt/x", "folder")]))
    assert error is None
    (message, level), = g.app.modals
    assert level == "info" and "1 videos" in message and "1 file(s) skipped" in message
    assert api.fields.get("data.processing") is False
