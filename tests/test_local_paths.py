"""Downloaded files stay inside the app's temp dir, whatever the bucket keys look like."""

import os

from conftest import UNREADABLE_SIZE, FakeApi, make_state


def _files_under(root):
    return [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs]


def test_key_with_dotdot_is_not_written_outside_data_dir(app, tmp_path):
    # S3 keys are arbitrary strings: "x/../../../escaped.mp4" is a valid key.
    api = FakeApi({"bkt/x/ok.mp4": 3, "bkt/x/../../../escaped.mp4": 3})
    main, g, error = app(api, make_state([("/bkt/x", "folder")]))
    assert error is None
    data_dir = os.path.realpath(g.app.data_dir)
    for p in api.remote_storage.downloads:
        assert os.path.realpath(p).startswith(data_dir + os.sep), p
    assert not (tmp_path / "escaped.mp4").exists()
    assert sorted(api.datasets[api.created_datasets[0]]) == ["escaped.mp4", "ok.mp4"]


def test_long_key_name_is_imported(app):
    long_name = "a" * 300 + ".mp4"  # longer than the 255-byte local file name limit
    api = FakeApi({f"bkt/x/{long_name}": 3, "bkt/x/short.mp4": 3})
    main, g, error = app(api, make_state([("/bkt/x", "folder")]))
    assert error is None
    assert sorted(api.datasets[api.created_datasets[0]]) == sorted([long_name, "short.mp4"])


def test_no_downloaded_file_is_left_behind(app):
    api = FakeApi({"bkt/x/1.mp4": 3, "bkt/x/bad.mp4": UNREADABLE_SIZE})
    main, g, error = app(api, make_state([("/bkt/x", "folder")]))
    assert _files_under(g.app.data_dir) == []
