#!/usr/bin/env python
"""Tests for `netatmo_geopy` package."""
# pylint: disable=redefined-outer-name
import json
import logging as lg
import time

import numpy as np
import pytest

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
    cws_recorder = nat.CWSRecorder(
        1,
        2,
        3,
        4,
        dst_dir=datadir,
        client_id="abcd",
        client_secret="abcd",
        username="john",
        password="doe",
        datetime_format="%Y-%m-%dT%H:%M:%S",
    )
    for response_id in response_ids:
        with open(shared_datadir / f"response-{response_id}.json") as src:
            requests_mock.get(settings.PUBLIC_DATA_URL, json=json.load(src))
        cws_recorder.dump_snapshot_gdf()
        # to ensure different file names when dumping the snapshots
        time.sleep(2)

    # test `CWSDataset`
    cws_dataset = nat.CWSDataset(snapshot_data_dir=datadir)
    assert len(cws_dataset.snapshot_filepaths) == len(response_ids)
    assert cws_dataset.temperature_gdf.shape == (2, 3)

    # test plotting
    # use `add_basemap=False` to avoid having to mock contextily's requests
    ax = nat.plot_snapshot(cws_dataset.temperature_gdf, add_basemap=False)
    assert len(ax.collections[0].get_array()) == 2
    assert len(ax.get_title()) > 0
    ax = nat.plot_snapshot(cws_dataset.temperature_gdf, title=False, add_basemap=False)
    assert len(ax.get_title()) == 0

    axes = [
        nat.plot_snapshot(
            cws_dataset.temperature_gdf,
            snapshot_column=snapshot_column,
            add_basemap=False,
        )
        for snapshot_column in cws_dataset.temperature_gdf.columns.drop("geometry")
    ]
    assert not np.array_equal(
        axes[0].collections[0].get_array(), axes[1].collections[0].get_array()
    )


def test_logging():
    # test logger
    utils.log("test a fake default message")
    utils.log("test a fake debug", level=lg.DEBUG)
    utils.log("test a fake info", level=lg.INFO)
    utils.log("test a fake warning", level=lg.WARNING)
    utils.log("test a fake error", level=lg.ERROR)
