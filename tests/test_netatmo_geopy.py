#!/usr/bin/env python
"""Tests for `netatmo_geopy` package."""
# pylint: disable=redefined-outer-name
import glob
import json
import logging as lg
import threading
import time
from datetime import datetime, timedelta
from os import path

import geopandas as gpd
import numpy as np
import pytest
import schedule

import netatmo_geopy as nat
from netatmo_geopy import settings, utils


@pytest.fixture
def mock_auth(requests_mock):
    requests_mock.post(
        settings.OAUTH2_TOKEN_URL, json={"token_type": "bearer", "access_token": "abcd"}
    )


@pytest.fixture
def mock_get_public_data(requests_mock):
    requests_mock.get(settings.PUBLIC_DATA_URL)


def test_core(requests_mock, datadir, shared_datadir, mock_auth):
    response_ids = ["00", "01"]

    # test `CWSRecorder`
    # `datetime_format` is provided to ensure different file names when dumping the
    # snapshots
    cws_recorder_args = [
        1,
        2,
        3,
        4,
    ]
    cws_recorder_kws = dict(
        dst_dir=datadir,
        client_id="abcd",
        client_secret="abcd",
        username="john",
        password="doe",
        datetime_format="%Y-%m-%dT%H:%M:%S",
    )
    cws_recorder = nat.CWSRecorder(*cws_recorder_args, **cws_recorder_kws)
    for response_id in response_ids:
        with open(shared_datadir / f"response-{response_id}.json") as src:
            requests_mock.get(settings.PUBLIC_DATA_URL, json=json.load(src))
        cws_recorder.dump_snapshot_gdf()
        # to ensure different file names when dumping the snapshots
        time.sleep(2)

    # test saving raw responses
    cws_recorder_kws["save_responses"] = True
    settings.SAVE_RESPONSES_DIR = datadir
    cws_recorder = nat.CWSRecorder(*cws_recorder_args, **cws_recorder_kws)
    response_filepattern = path.join(datadir, "*.json")
    num_datadir_files = len(glob.glob(response_filepattern))
    for response_id in response_ids:
        with open(shared_datadir / f"response-{response_id}.json") as src:
            requests_mock.get(settings.PUBLIC_DATA_URL, json=json.load(src))
        cws_recorder.get_snapshot_gdf()
    assert len(glob.glob(response_filepattern)) == num_datadir_files + len(response_ids)

    # test schedule
    # this is quite a hacky test, since `schedule` does not run in the background and we
    # want to avoid tests that take too long to execute (especially with long idle
    # periods).
    # Hence, we will use a thread to start the recorder, and another to first verify
    # that the recorder has scheduled jobs, and then cancel them so that we do not have
    # to wait for the recorder to finish.
    _ = cws_recorder_kws.pop("save_responses")
    cws_recorder_kws.update(
        time_unit="minutes",
        interval=3,
        at=":30",
        until=datetime.now() + timedelta(minutes=10),
    )

    # we need to use a "global" variable because we cannot get function return values
    # when using threads
    num_jobs_dict = {}

    def _get_and_cancel_jobs(num_jobs_dict):
        num_jobs_dict["num_jobs"] = len(schedule.get_jobs())
        schedule.clear()

    t1 = threading.Thread(
        target=nat.CWSRecorder,
        args=cws_recorder_args,
        kwargs=cws_recorder_kws,
    )
    t1.start()
    t2 = threading.Thread(target=_get_and_cancel_jobs, args=(num_jobs_dict,))
    t2.start()
    assert num_jobs_dict["num_jobs"] > 0

    # test `CWSDataset`
    # test that the time series geo-data frame has the right shape
    cws_dataset = nat.CWSDataset(snapshot_data_dir=datadir)
    assert cws_dataset.ts_gdf.shape == (2, 3)
    # test that we can also instantiate the dataset from the time series geo-dataframe
    ts_gdf_filepath = datadir / "ts-gdf.gpkg"
    cws_dataset.ts_gdf.to_file(ts_gdf_filepath)
    cws_dataset = nat.CWSDataset(ts_gdf_filepath=ts_gdf_filepath)
    assert cws_dataset.ts_gdf.shape == (2, 3)

    # test plotting
    # use `add_basemap=False` to avoid having to mock contextily's requests
    ax = nat.plot_snapshot(cws_dataset.ts_gdf, add_basemap=False)
    assert len(ax.collections[0].get_array()) == 2
    assert len(ax.get_title()) > 0
    ax = nat.plot_snapshot(cws_dataset.ts_gdf, title=False, add_basemap=False)
    assert len(ax.get_title()) == 0
    axes = [
        nat.plot_snapshot(
            cws_dataset.ts_gdf,
            snapshot_column=snapshot_column,
            add_basemap=False,
        )
        for snapshot_column in cws_dataset.ts_gdf.columns.drop("geometry")
    ]
    assert not np.array_equal(
        axes[0].collections[0].get_array(), axes[1].collections[0].get_array()
    )

    # test quality controls
    # to that end, we first need a bigger time series geo-data frame, so we will create
    # a fake one and set it as the `ts_gdf` attribute.
    num_stations = 20
    cws_dataset.ts_gdf = gpd.GeoDataFrame(
        np.random.rand(num_stations, 50),
        geometry=gpd.points_from_xy(
            x=np.random.rand(num_stations), y=np.random.rand(num_stations)
        ),
    )
    # mislocated stations
    mislocated_stations = cws_dataset.get_mislocated_stations()
    assert len(mislocated_stations) == num_stations
    assert mislocated_stations.dtype == bool
    # outlier stations
    outlier_stations = cws_dataset.get_outlier_stations()
    assert len(outlier_stations) == num_stations
    assert outlier_stations.dtype == bool
    # more technical test: if we make the acceptance (i.e., non outlier) range wider and
    # set a higher threshold, there must be less outliers
    num_outlier_stations = outlier_stations.sum()
    assert (
        num_outlier_stations
        >= cws_dataset.get_outlier_stations(
            low_alpha=settings.OUTLIER_LOW_ALPHA / 2,
            high_alpha=settings.OUTLIER_HIGH_ALPHA
            + (1 - settings.OUTLIER_HIGH_ALPHA) / 2,
            station_outlier_threshold=settings.STATION_OUTLIER_THRESHOLD / 2,
        ).sum()
    )
    # indoor stations
    indoor_stations = cws_dataset.get_indoor_stations()
    assert len(indoor_stations) == num_stations
    assert indoor_stations.dtype == bool
    # more technical test: if we make the correlation threshold lower, there must be
    # less indoor stations
    num_indoor_stations = indoor_stations.sum()
    assert (
        num_indoor_stations
        >= cws_dataset.get_indoor_stations(
            station_indoor_corr_threshold=settings.STATION_INDOOR_CORR_THRESHOLD / 2
        ).sum()
    )


def test_logging():
    # test logger
    utils.log("test a fake default message")
    utils.log("test a fake debug", level=lg.DEBUG)
    utils.log("test a fake info", level=lg.INFO)
    utils.log("test a fake warning", level=lg.WARNING)
    utils.log("test a fake error", level=lg.ERROR)
