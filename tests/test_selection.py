"""What gets imported for a selection in the file viewer."""

from conftest import FakeApi, make_state


def test_folder_selected_under_bucket_subpath(app):
    api = FakeApi({"bkt/sub/dir/1.mp4": 3, "bkt/sub/dir/deep/2.avi": 3, "bkt/sub/other/3.mp4": 3})
    main, g, error = app(api, make_state([("/bkt/sub/dir", "folder")], bucket="bkt/sub"))
    assert error is None
    assert sorted(api.datasets[api.created_datasets[0]]) == ["1.mp4", "2.avi"]


def test_large_folder_is_listed_page_by_page(app):
    api = FakeApi({f"bkt/x/{i:05d}.mp4": 1 for i in range(25)}, page_size=10)
    main, g, error = app(api, make_state([("/bkt/x", "folder")], add_mode="addBylink"))
    assert error is None
    assert len(api.datasets[api.created_datasets[0]]) == 25


def test_file_selected_twice_is_imported_once(app):
    api = FakeApi({"bkt/x/1.mp4": 3, "bkt/x/2.mp4": 3})
    main, g, error = app(api, make_state([("/bkt/x", "folder"), ("/bkt/x/1.mp4", "file")]))
    assert error is None
    assert sorted(api.datasets[api.created_datasets[0]]) == ["1.mp4", "2.mp4"]


def test_link_mode_same_name_in_two_folders(app):
    api = FakeApi({"bkt/x/a/clip.mp4": 3, "bkt/x/b/clip.mp4": 3})
    main, g, error = app(api, make_state([("/bkt/x", "folder")], add_mode="addBylink"))
    assert error is None
    assert sorted(api.datasets[api.created_datasets[0]]) == ["clip.mp4", "clip_01.mp4"]
    assert api.remote_storage.downloads == []


def test_link_mode_into_existing_dataset_with_the_same_name(app):
    api = FakeApi({"bkt/x/clip.mp4": 3}, existing_project=(7, {70: ("ds", None, ["clip.mp4"])}))
    state = make_state([("/bkt/x", "folder")], add_mode="addBylink", project_id=7, dataset_name="ds")
    main, g, error = app(api, state)
    assert error is None
    assert api.datasets[70] == ["clip.mp4", "clip_01.mp4"]
    assert api.video.calls == [("links", ["clip_01.mp4"], ["s3://bkt/x/clip.mp4"])]


def test_folder_with_empty_name_does_not_import_the_whole_bucket(app):
    # a key "/a.mp4" makes the viewer show a folder with an empty name: "/bkt/"
    api = FakeApi({"bkt//a.mp4": 3, "bkt/x/1.mp4": 3, "bkt/y/2.mp4": 3})
    main, g, error = app(api, make_state([("/bkt/", "folder"), ("/bkt/x/1.mp4", "file")]))
    assert api.datasets[api.created_datasets[0]] == ["1.mp4"]
    assert error is not None and "/bkt/" in str(error)
