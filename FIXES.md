# import-videos-from-cloud-storage: fixes 2026-10

Branch `ecosystem-fixes-2026-10` from `master` (f34fe79, released as v1.4.2). Legacy GUI app
(`AppService` + `gui_template`): targeted fixes and the image move only, no rewrite.

## Behaviour contract

- **Started from:** Ecosystem / app list, in a workspace (`context.teamId`, `context.workspaceId`).
  Long-running GUI session; the user stops it.
- **GUI state keys (unchanged):** `provider`, `bucketName` (a bucket, or a path that starts with
  the bucket name), `selected` (file viewer items `{path: "/<bucket>/<key>", type}`), `addMode`
  (`copyData` | `addBylink` - lower-case "l", as in the template), `dstProjectMode`,
  `dstProjectName`, `dstProjectId`, `dstDatasetMode`, `dstDatasetName`, `selectedDatasetName`.
- **Commands:** `preview` (Connect), `refresh_tree_viewer`, `process` (Start import).
- **Import:** selected folders are listed recursively (page by page) and every file with a
  supported video extension is imported; selected files as they are. One dataset; names are the
  key's base name, made unique.
  - `copyData`: one video at a time: download to the agent, check it with ffprobe
    (`sly.video.get_info`), upload, delete the local copy.
  - `addBylink`: `videos.bulk.add` with `s3://bucket/key` links, batches of 50, no download.
- **Output:** task output project; workflow output = the project (new project) or the dataset
  (existing project). The app never writes to, moves or deletes anything in the cloud storage and
  never sees or logs credentials (only provider names and bucket names).
- **Result:** all imported -> info modal with the count, session stays open. Some or all failed ->
  error modal and the task ends with an error.

## Fixed

| Commit | Problem | Tests old -> new |
|---|---|---|
| 1c35e75 | Copy mode wrote the local copy to `data_dir/<bucket>/<key>`: keys with `..` escaped the data dir, names > 255 bytes crashed, unreadable/failed videos stayed on disk. | 3 of 3 fail -> 3/3 |
| a9bb1f6 | Link mode sent base names as they were: the same file name in two folders, or a name already in the existing dataset, made the server reject the batch and the session crash after creating the project. A doubly selected file was imported twice. | 3 of 5 fail -> 8/8 total |
| e4b1122 | Unreadable videos were "skipped" with a doubled skip count in the success message; videos the server could not process (`upload_paths` returns nothing, logs "File skipped") counted as imported; all skipped -> "0 videos successfully imported" and an empty project as output; download errors, refused link batches and missing selected files (IndexError) crashed mid-import leaving the project; missing destination or nested dataset -> endless spinner; workflow output registered before anything was imported. | 11 of 11 fail -> 19/19 total |
| a0db1df | Image move (below), plus an AppService runtime test. | runtime test fails without protobuf |
| 958ad84 | A folder with an empty name (keys starting with `/`; present in dev buckets) has path `/<bucket>/`: selecting it imported every video in the bucket. | 1 of 1 fails -> 21/21 total |

Offline tests: `python -m pytest tests` (fake `sly.Api`, `AppService`, cloud storage and
`sly.video.get_info`; no server, no ffprobe). Run with supervisely 6.74.34 on Python 3.14.3 and
inside the per-app image built locally from the template (linux/amd64, Python 3.14.7): all pass;
there `sly.video.get_info` reads an ffmpeg-generated mp4 and raises on a random-bytes `.mp4`.

## Intentional behaviour changes

- **Per-video failures no longer abort the import**; each one is recorded with a reason
  (download failed, not a readable video, the server could not process it, link refused, not
  found in the storage, empty-name folder). Link batches that fail are retried in halves.
- **Unreadable or server-dropped videos now make the import fail** (they were "skipped" with a
  success message). A partial import sets the output project and workflow output, then shows an
  error modal with counts and the first five failed paths and raises: the session ends with an
  error.
- **Nothing imported -> the project (or dataset) this run created is removed** if the server
  reports it empty; error modal; task error. Projects/datasets the user selected are never
  removed.
- The success count is the number of videos actually imported (was `total - 2 * skipped`).
- Link-mode names are made unique (`clip.mp4`, `clip_01.mp4`), like copy mode already did.
- Workflow output is registered after the import, only when something was imported.
- Missing destination: error modal and the button is unlocked; an existing nested dataset is found
  by a recursive lookup if its name is unique.
- Success modal adds "N file(s) skipped: not a supported video extension" when files were skipped.

## Found but not fixed

- Keys that start with `/` cannot be addressed (viewer path drops the bucket, the SDK strips `/`);
  reported as failures through an empty-name folder, not imported.
- The viewer shows only the first 100 entries of a folder (`USER_PREVIEW_LIMIT`).
- Copy mode calls `video.get_free_name` (one request) per video and updates progress with several
  `task.set_fields` calls per video; slow, not wrong.
- A quota error (`PaymentRequired`, re-raised by `upload_paths`) is recorded per video instead of
  stopping at once.
- `preview` catches `Exception as e` without using it (no warning logged); left as is.
- **Security finding R6 (ecosystem-security.md):** the user's checkout
  `workapps/import-videos-from-cloud-storage/local.env` has an uncommitted `AGENT_TOKEN` (the
  sys-add-project-from-ecosystem agent token, sha256 c15b9acf). Not touched (rules: leave the
  user's checkouts alone); the committed `local.env` on master and on this branch has no token.
  Rotation of that agent is the fix; `git checkout -- local.env` in the checkout is up to the user.

## Image

`supervisely/import-export:6.74.34` (sdk_legacy) -> `supervisely/import-videos-from-cloud-storage:6.74.34`,
a per-app image from `build_image_from_template.yml` on `base-py-sdk-hardened:6.74.34`
(Python 3.14, has ffmpeg/ffprobe) with `dev_requirements.txt` = `supervisely==6.74.34` +
`protobuf==3.20.3`.

- **Why not the bare hardened base:** the legacy `AppService` receives GUI commands as protobuf
  messages and `base-py-sdk-hardened` has no protobuf, so the GUI would never answer.
  `tests/test_runtime.py` runs a real `AppService` loop through protobuf messages.
- SDK stays 6.74.34, the newest allowed for `instance_version` 6.17.22.
- CI: `release.yml` and `release_branch.yml` run `build-image` before the release (skipped when
  the tag exists); `build_app_image.yml` added.

## Dev-check plan

Start each case with
`uv run ecosystem-fleet/fleet.py run import-videos-from-cloud-storage --workspace 733 --version ecosystem-fixes-2026-10 --branch --no-wait`
and the same without `--version/--branch` (published v1.4.2), then use the session GUI. Delete
the projects the checks create afterwards.

| # | GUI steps | Expected on the branch | Published v1.4.2 |
|---|---|---|---|
| 1 | Azure Blob Storage, `supervisely-test`, Connect; select folder `videos` (3 mp4 in `test/` and `test/deepfolder/`); copy; new project | 3 videos, info modal "3 videos ...", playable; no files left in the session data dir | same |
| 2 | Same as 1 in "add by link" mode | 3 videos by link, playable | same |
| 3 | Run 2 again into the same existing project and dataset | 3 more videos named `*_01.mp4`, success | session crashes (409 name conflict) |
| 4 | Amazon S3, bucket field `remote-img-test/demo_videos`, Connect; select folder `my_folder_01` and one top-level video; copy | all mp4 of the selection imported | same (the video app already handled sub-paths) |
| 5 | Google Cloud Storage `sly-dev-test`, folder `vid` (1 mp4 + json files); copy | 1 video; modal mentions skipped files | 1 video, no mention |
| 6 | A folder with one valid and one broken `.mp4` (no such folder on dev; needs a test object uploaded by the coordinator) | 1 imported, error "1 of 2 videos failed", task error | "0 videos has been successfully imported" (1 is), task success |
| 7 | Only the broken `.mp4` of case 6 | "No videos were imported", no project left, task error | "-1 videos has been successfully imported", empty project as output |
| 8 | `remote-img-test`; select the blank-named folder at the top and one file from `demo_videos` | 1 imported, error naming `/remote-img-test/` | **do not run**: imports every video in the bucket |
