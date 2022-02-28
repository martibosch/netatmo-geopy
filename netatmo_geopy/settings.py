"""Settings."""
import logging as lg

# Netatmo API
BASE_URL = "https://api.netatmo.com"
OAUTH2_TOKEN_URL = f"{BASE_URL}/oauth2/token"
PUBLIC_DATA_URL = f"{BASE_URL}/api/getpublicdata"

# recording/IO
RECORDER_DST_DIR = "./snapshot-data"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M"
SAVE_RESPONSES = False
SAVE_RESPONSES_DIR = "./responses"
SNAPSHOT_FILE_EXT = "gpkg"

# plotting
PLOT_CMAP = "coolwarm"
PLOT_LEGEND = True
PLOT_ATTRIBUTION = False
PLOT_LEGEND_POSITION = "right"
PLOT_LEGEND_SIZE = "2.5%"
PLOT_LEGEND_PAD = 0.2
PLOT_TITLE = True
PLOT_ADD_BASEMAP = True

# QC
OUTLIER_LOW_ALPHA = 0.01
OUTLIER_HIGH_ALPHA = 0.95
STATION_OUTLIER_THRESHOLD = 0.2
STATION_INDOOR_CORR_THRESHOLD = 0.9

# logging (mostly from `osmnx.utils`)
LOG_FILE = False
LOG_CONSOLE = True
LOG_LEVEL = lg.INFO
LOG_NAME = "netatmo-geopy"
LOG_FILENAME = "netatmo-geopy"
