<div align="center" markdown>
<img src="https://i.imgur.com/imzti2w.png"/>

# Import videos from cloud storage

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#How-To-Use">How To Use</a>
</p>


[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](https://ecosystem.supervise.ly/apps/supervisely-ecosystem/import-videos-from-cloud-storage)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/import-videos-from-cloud-storage)
[![views](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/import-videos-from-cloud-storage&counter=views&label=views)](https://supervise.ly)
[![used by teams](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/import-videos-from-cloud-storage&counter=downloads&label=used%20by%20teams)](https://supervise.ly)
[![runs](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/import-videos-from-cloud-storage&counter=runs&label=runs)](https://supervise.ly)

</div>

# Overview

This apps allows to import videos from most popular cloud storage providers to Supervisely Private instance.

List of providers:
- Amazon s3
- Google Cloud Storage (CS)
- Microsoft Azure
- and others with s3 compatible interfaces

App supports two types of import:
1. copy videos from cloud to Supervisely Storage (pros: fast video streaming, cons: data is duplicated)
2. add videos by link (pros: data will not be duplicated, cons: video streaming lags are possible - it depends on 
   cloud configuration)

⚠️ Notice: for any of these import types app downloads video to its temp directory, processes it and extracts some 
technical information like timestamp-frame index mapping, number of streams, resolution and so on. Once the video is 
processed, it will be removed from temp directory. This is the one time procedure.

# How To Use

0. Ask your instance administrator to add cloud credentials to instance settings. It can be done both in .env 
   configuration files or in Admin UI dashboard.
1. Add app to your team from Ecosystem
2. Run app from `Team Apps` Page
3. Connect to cloud bucket, preview and select files and directories, import selected files to some project/dataset. 
   You can perform these actions as many times as needed
3. Once you are ready with the app, you should close app manually


Watch short video for more details:

<a data-key="sly-embeded-video-link" href="https://youtu.be/20pDcGWxOYo" data-video-code="20pDcGWxOYo">
    <img src="https://i.imgur.com/Fke5a5R.png" alt="SLY_EMBEDED_VIDEO_LINK"  style="max-width:500px;">
</a>

# Screenshot

<img src="https://i.imgur.com/wgsVrYL.png"/>
