"""Main module."""
import glob
import json
import pathlib as pl
import re
import time
from datetime import datetime
from functools import reduce
from os import environ, path

import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import schedule
import tqdm
from fiona import errors as fiona_errors
from mpl_toolkits.axes_grid1 import make_axes_locatable
from shapely import geometry

from . import auth, settings, utils

__all__ = ["plot_snapshot", "CWSRecorder", "CWSDataset"]

NETATMO_CRS = "epsg:4326"


def _get_public_data(
    lon_sw,
    lat_sw,
    lon_ne,
    lat_ne,
    *,
    client_id=None,
    client_secret=None,
    username=None,
    password=None,
):
    if client_id is None:
        client_id = environ.get("NETATMO_CLIENT_ID")
    if client_secret is None:
        client_secret = environ.get("NETATMO_CLIENT_SECRET")
    if username is None:
        username = environ.get("NETATMO_USERNAME")
    if password is None:
        password = environ.get("NETATMO_PASSWORD")
    conn = auth.NetatmoConnect(client_id, client_secret, username, password)
    public_data_dict = dict(
        lon_sw=lon_sw,
        lat_sw=lat_sw,
        lon_ne=lon_ne,
        lat_ne=lat_ne,
        required_data="temperature",
    )

    response = conn.session.get(settings.PUBLIC_DATA_URL, data=public_data_dict)
    size_kb = len(response.content) / 1000
    domain = re.findall(r"(?s)//(.*?)/", settings.PUBLIC_DATA_URL)[0]
    utils.log(f"Downloaded {size_kb:,.2f}kB from {domain}")
    return response.json()


def _gdf_from_response_json(response_json, datetime_format):
    def _get_id_temperature_geom(station_record):
        for measure_key, measure_value_dict in station_record["measures"].items():
            try:
                return (
                    measure_key,
                    next(iter(measure_value_dict["res"].values()))[
                        measure_value_dict["type"].index("temperature")
                    ],
                    geometry.Point(*station_record["place"]["location"]),
                )
            except ValueError:
                pass

        return None

    return gpd.GeoDataFrame(
        [
            _get_id_temperature_geom(station_record)
            for station_record in response_json["body"]
        ],
        columns=[
            "station_id",
            datetime.fromtimestamp(response_json["time_server"]).strftime(
                datetime_format
            ),
            "geometry",
        ],
        crs=NETATMO_CRS,
    ).set_index("station_id")


def _join_snapshot_gdfs(snapshot_filepaths):
    temperature_gdf = reduce(
        lambda left, right: pd.merge(
            left, right, on=["station_id", "geometry"], how="outer"
        ),
        [
            gpd.read_file(snapshot_filepath)
            for snapshot_filepath in tqdm.tqdm(snapshot_filepaths)
        ],
    )
    return temperature_gdf[
        ["station_id"]
        + sorted(temperature_gdf.columns.drop(["station_id", "geometry"]))
        + ["geometry"]
    ].set_index("station_id")


def _get_basename(snapshot_gdf):
    # use the snapshot time (the only geo-data frame column other than "geometry")
    return snapshot_gdf.columns.drop("geometry")[0]


def plot_snapshot(  # noqa: C901
    snapshot_gdf,
    *,
    snapshot_column=None,
    ax=None,
    cmap=None,
    legend=None,
    legend_position=None,
    legend_size=None,
    legend_pad=None,
    title=None,
    add_basemap=None,
    attribution=None,
    subplot_kws=None,
    plot_kws=None,
    set_title_kws=None,
    add_basemap_kws=None,
    append_axes_kws=None,
):
    """
    Plot a snapshot of station measurements.

    Parameters
    ----------
    snapshot_gdf : geopandas.GeoDataFrame
        Geo-data frame of CWS temperature measurements.
    snapshot_column : str, optional
        Column of CWS temperature measurements to plot. If None, the first column (other
        than `geometry`) is used.
    ax : `matplotlib.axes.Axes` instancd, optional
        Plot in given axis. If None creates a new figure.
    cmap : str or `matplotlib.colors.Colormap` instance, optional
        Colormap of the plot. If None, the default value from
        `settings.DEFAULT_PLOT_CMAP` is used.
    legend : bool, optional
        Whether a legend should be added to the plot. If None, the default value from
        `settings.DEFAULT_PLOT_LEGEND` is used.
    legend_position : str {"left", "right", "bottom", "top"}, optional
        Position of the legend axes, passed to
        `mpl_toolkits.axes_grid1.axes_divider.AxesDivider.append_axes`. If None, the
        default value from `settings.DEFAULT_PLOT_LEGEND_POSITION` is used.
    legend_size : numeric or str, optional
        Size of the legend axes, passed to
        `mpl_toolkits.axes_grid1.axes_divider.AxesDivider.append_axes`. If None, the
        default value from `settings.DEFAULT_PLOT_LEGEND_SIZE` is used.
    legend_pad : numeric or str, optional
        Padding between the plot and legend axes, passed to
        `mpl_toolkits.axes_grid1.axes_divider.AxesDivider.append_axes`. If None, the
        default value from `settings.DEFAULT_PLOT_LEGEND_PAD` is used.
    title : bool or str, optional
        Whether a title should be added to the plot. If True, the timestamp of the
        snapshot (geo-data frame column) is used. It is also possible to pass a string
        so that it is used as title label (instead of the timestamp). If None, the
        default value from `settings.DEFAULT_PLOT_TITLE` is used.
    add_basemap : bool, optional
        Whether a basemap should be added to the plot using `contextily.add_basemap`. If
        None, the default value from `settings.DEFAULT_PLOT_ADD_BASEMAP` is used.
    attribution : str or bool, optional
        Attribution text for the basemap source, added to the bottom of the plot, passed
        to `contextily.add_basemap`. If False, no attribution is added. If None, the
        default value from `settings.DEFAULT_PLOT_ATTRIBUTION` is used.
    subplot_kws, plot_kws, set_title_kws, add_basemap_kws, append_axes_kws : dict, \
                                                                             optional
        Keyword arguments passed to `matplotlib.pyplot.subplots`,
        `geopandas.GeoDataFrame.plot`, `matplotlib.axes.Axes.set_title`,
        `contextily.add_basemap` and
        `mpl_toolkits.axes_grid1.axes_divider.AxesDivider.append_axes` respectively.

    Returns
    -------
    ax : `matplotlib.axes.Axes`
        Axes with the plot drawn onto it.
    """
    # if no column is provided, we plot the "first" column other than "geometry"
    if snapshot_column is None:
        snapshot_column = snapshot_gdf.columns.drop("geometry")[0]

    # subplots arguments
    if ax is None:
        if subplot_kws is None:
            subplot_kws = {}
        fig, ax = plt.subplots(**subplot_kws)
    # plot arguments
    if plot_kws is None:
        _plot_kws = {}
    else:
        _plot_kws = plot_kws.copy()
    # _plot_kws = {key: plot_kws[key] for key in plot_kws}
    if cmap is None:
        cmap = _plot_kws.pop("cmap", settings.DEFAULT_PLOT_CMAP)
    if legend is None:
        legend = _plot_kws.pop("legend", settings.DEFAULT_PLOT_LEGEND)

    # plot
    if legend:
        divider = make_axes_locatable(ax)
        if legend_position is None:
            legend_position = settings.DEFAULT_PLOT_LEGEND_POSITION
        if legend_size is None:
            legend_size = settings.DEFAULT_PLOT_LEGEND_SIZE
        if append_axes_kws is None:
            _append_axes_kws = {}
        else:
            _append_axes_kws = append_axes_kws.copy()
        if legend_pad is None:
            legend_pad = _append_axes_kws.pop("pad", settings.DEFAULT_PLOT_LEGEND_PAD)
        _plot_kws["cax"] = divider.append_axes(
            legend_position, legend_size, pad=legend_pad, **_append_axes_kws
        )
    snapshot_gdf.plot(
        column=snapshot_column, cmap=cmap, ax=ax, legend=legend, **_plot_kws
    )
    if title is None:
        title = settings.DEFAULT_PLOT_TITLE
    if title:
        if title is True:
            title_label = snapshot_column
        elif isinstance(title, str):
            title_label = title
        if set_title_kws is None:
            set_title_kws = {}
        ax.set_title(title_label, **set_title_kws)

    # basemap
    if add_basemap is None:
        add_basemap = settings.DEFAULT_PLOT_ADD_BASEMAP
    if add_basemap:
        # raise ImportError(
        #     "The contextily package is required for adding basemaps. "
        #     "You can install it using 'conda install -c conda-forge contextily' or "
        #     "'pip install contextily'."
        # )
        # add_basemap arguments
        if add_basemap_kws is None:
            _add_basemap_kws = {}
        else:
            _add_basemap_kws = add_basemap_kws.copy()
        # _add_basemap_kws = {key: add_basemap_kws[key] for key in add_basemap_kws}
        if attribution is None:
            attribution = _add_basemap_kws.pop(
                "attribution", settings.DEFAULT_PLOT_ATTRIBUTION
            )
        # add basemap
        cx.add_basemap(
            ax=ax,
            crs=snapshot_gdf.crs,
            attribution=attribution,
            **_add_basemap_kws,
        )

    return ax


class CWSRecorder(object):
    """CWSRecorder."""

    def __init__(
        self,
        lon_sw,
        lat_sw,
        lon_ne,
        lat_ne,
        *,
        dst_dir=None,
        client_id=None,
        client_secret=None,
        username=None,
        password=None,
        time_unit=None,
        interval=None,
        at=None,
        until=None,
        datetime_format=None,
        snapshot_file_ext=None,
        save_responses=None,
        save_responses_dir=None,
    ):
        """
        Initialize a CWS recorder for a given region.

        Parameters
        ----------
        lon_sw, lat_sw, lon_ne, lat_ne : numeric
            Latitude/longitude coordinates of the bounds of the region of interest
        dst_dir : str or pathlib.Path object, optional
            Path to the directory where the recorded snapshots are to be dumped. Only
            used when the `dump_snapshot_gdf` method is called, ignored otherwise. If
            None, the default value from `settings.DEAFULT_DST_DIR`.
        client_id, client_secret, username, password : str, optional
            Authentication credentials for Netatmo. If None, the respective values set
            in the "NETATMO_CLIENT_ID", "NETATMO_CLIENT_SECRET", "NETATMO_USERNAME" and
            "NETATMO_PASSWORD" environment variables are used.
        time_unit : str {"second", "seconds", "minute", "minutes", "hour", "hours", \
                    "day", "days", "week", "weeks", "monday", "tuesday", "wednesday", \
                    "thursday", "friday", "saturday", "sunday"}, optional
            Time unit. If None, no snaphots are taken periodically - snapshots are only
            taken by manually calling `get_snapshot_gdf` or `dump_snapshot_gdf`.
        interval : int, optional
            Quantity of the time unit set in `time_unit`, altogether defining the
            interval between snapshots. If None, the default value from the `schedule`
            library, i.e., 1, is used. Ignored if `time_unit` is None.
        at : str, optional
            Time string defining the particular time when snapshots are taken. See also
            https://schedule.readthedocs.io/en/stable/reference.html#schedule.Job.at.
            Ignored if `time_unit` is None. The following formats are accepted:

            * for daily jobs -> HH:MM:SS or HH:MM
            * for hourly jobs -> MM:SS or :MM
            * for minute jobs -> :SS.
        until : datetime.datetime, datetime.timedelta, datetime.time or str, optional
            Latest time (in the future) when a snapshot will be taken. If None, the
            periodic snapshots are taken indefinetly. Ignored if `time_unit` is None.
            The following formats are accepted:

            * datetime.datetime
            * datetime.timedelta
            * datetime.time
            * string in one of the following formats: "%Y-%m-%d %H:%M:%S",
              "%Y-%m-%d %H:%M", "%Y-%m-%d", "%H:%M:%S", "%H:%M" as defined by
              `datetime.strptime` behaviour.
        datetime_format : str, optional
            Datetime format string. Used to name the geo-data frame columns and the
            snapshot file dumps. If None, the default value from
            `settings.DEFAULT_DATETIME_FORMAT` is used.
        snapshot_file_ext : str, optional
            File extension used when dumping recorded snapshot files, which must match
            an OGR vector format driver (see `fiona.supported_drivers`). If None, the
            default value from `settings.DEFAULT_SNAPSHOT_FILE_EXT` is used.
        save_responses : bool, optional
            Whether the JSON responses from the Netatmo public data API calls are
            stored. If None, the default value from `settings.DEFAULT_SAVE_RESPONSES`is
            used.
        save_responses_dir : str or pathlib.Path object, optional.
            Path to the directory where the JSON responses are to be stored. If None,
            the default value from `settings.DEFAULT_SAVE_RESPONSES_DIR`is used. Ignored
            if `save_responses` is False.
        """
        super(CWSRecorder, self).__init__()

        self.lon_sw = lon_sw
        self.lat_sw = lat_sw
        self.lon_ne = lon_ne
        self.lat_ne = lat_ne
        self.dst_dir = dst_dir

        # auth
        self._client_id = client_id
        self._client_secret = client_secret
        self._username = username
        self._password = password

        # IO
        if datetime_format is None:
            datetime_format = settings.DEFAULT_DATETIME_FORMAT
        self.datetime_format = datetime_format
        if snapshot_file_ext is None:
            snapshot_file_ext = settings.DEFAULT_SNAPSHOT_FILE_EXT
        self.snapshot_file_ext = snapshot_file_ext
        if save_responses is None:
            save_responses = settings.DEFAULT_SAVE_RESPONSES
        self.save_responses = save_responses
        if save_responses_dir is None:
            save_responses_dir = settings.DEFAULT_SAVE_RESPONSES_DIR
        self.save_responses_dir = save_responses_dir

        # schedule
        if time_unit:
            if interval:
                caller = schedule.every(interval)
            else:
                caller = schedule.every()
            caller = getattr(caller, time_unit)
            if at:
                caller = caller.at(at)
            if until:
                caller = caller.until(until)
            caller.do(self.dump_snapshot_gdf)
            while schedule.get_jobs():
                schedule.run_pending()
                time.sleep(1)

    def get_snapshot_gdf(self):
        """Get current CWS temperature snapshot."""
        response_json = _get_public_data(
            self.lon_sw,
            self.lat_sw,
            self.lon_ne,
            self.lat_ne,
            client_id=self._client_id,
            client_secret=self._client_secret,
            username=self._username,
            password=self._password,
        )

        snapshot_gdf = _gdf_from_response_json(response_json, self.datetime_format)

        if self.save_responses:
            dst_response_filepath = path.join(
                self.save_responses_dir, f"{_get_basename(snapshot_gdf)}.json"
            )
            with open(dst_response_filepath, "w") as dst:
                json.dump(response_json, dst)
            utils.log(f"Dumped response to file '{dst_response_filepath}'")

        return snapshot_gdf

    def dump_snapshot_gdf(self):
        """Get current CWS temperature snapshot and dump it to a file."""
        snapshot_gdf = self.get_snapshot_gdf()
        dst_filepath = path.join(
            self.dst_dir, f"{_get_basename(snapshot_gdf)}.{self.snapshot_file_ext}"
        )
        snapshot_gdf.to_file(dst_filepath)
        utils.log(f"Dumped snapshot geo-data frame to file '{dst_filepath}'")


class CWSDataset(object):
    """CWSDataset."""

    def __init__(
        self,
        *,
        snapshot_filepaths=None,
        snapshot_data_dir=None,
        snapshot_file_ext=None,
        datetime_format=None,
    ):
        """
        Initialize a CWS dataset from recorded snapshot files.

        Parameters
        ----------
        snapshot_filepaths : list-like of str, path or file-like objects, optional
            List of paths to the input snapshot recording files, passed to
            `geopandas.read_file`.
        snapshot_data_dir : str or pathlib.Path object
            Path to the directory where the snapshot recording files are located.
            Ignored if `snapshot_filepaths` is provided.
        snapshot_file_ext : str, optional
            File extension of the snapshot recording, used to obtain the list of input
            files in `snapshot_data_dir`. If None, the default value from
            `settings.DEFAULT_SNAPSHOT_FILE_EXT` is used. Ignored if
            `snapshot_filepaths` is provided.
        datetime_format : str, optional
            Datetime format string. Used to name the geo-data frame columns and the
            snapshot file dumps. If None, the default value from
            `settings.DEFAULT_DATETIME_FORMAT` is used.
        """
        super(CWSDataset, self).__init__()

        if snapshot_filepaths is None:
            if snapshot_file_ext is None:
                snapshot_file_ext = settings.DEFAULT_SNAPSHOT_FILE_EXT
            snapshot_filepaths = glob.glob(
                path.join(snapshot_data_dir, f"*.{snapshot_file_ext}")
            )
        self.snapshot_filepaths = snapshot_filepaths

        if datetime_format is None:
            datetime_format = settings.DEFAULT_DATETIME_FORMAT
        self.datetime_format = datetime_format

    @property
    def temperature_gdf(self):
        """Time series of temperature measurements at the station locations."""
        try:
            return self._temperature_gdf
        except AttributeError:
            self._temperature_gdf = _join_snapshot_gdfs(self.snapshot_filepaths)
            return self._temperature_gdf
