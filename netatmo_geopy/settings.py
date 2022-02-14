"""Settings."""
import logging as lg

# Netatmo API
BASE_URL = "https://api.netatmo.com"
OAUTH2_TOKEN_URL = f"{BASE_URL}/oauth2/token"
PUBLIC_DATA_URL = f"{BASE_URL}/api/getpublicdata"

# recording/IO
DEFAULT_DST_DIR = "./snapshot-data"
DEFAULT_DATETIME_FORMAT = "%Y-%m-%dT%H:%M"
DEFAULT_SNAPSHOT_FILE_EXT = "gpkg"
DEFAULT_SAVE_RESPONSES = False
DEFAULT_SAVE_RESPONSES_DIR = "./responses"

# plotting
DEFAULT_PLOT_CMAP = "coolwarm"
DEFAULT_PLOT_LEGEND = True
DEFAULT_PLOT_ATTRIBUTION = False
DEFAULT_PLOT_LEGEND_POSITION = "right"
DEFAULT_PLOT_LEGEND_SIZE = "2.5%"
DEFAULT_PLOT_LEGEND_PAD = 0.2
DEFAULT_PLOT_TITLE = True
DEFAULT_PLOT_ADD_BASEMAP = True

# logging (mostly from `osmnx.utils`)
LOG_FILE = False
LOG_CONSOLE = True
LOG_LEVEL = lg.INFO
LOG_NAME = "netatmo-geopy"
LOG_FILENAME = "netatmo-geopy"
