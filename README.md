[![PyPI version fury.io](https://badge.fury.io/py/netatmo-geopy.svg)](https://pypi.python.org/pypi/netatmo-geopy/)
[![Documentation Status](https://readthedocs.org/projects/netatmo-geopy/badge/?version=latest)](https://netatmo-geopy.readthedocs.io/en/latest/?badge=latest)
[![CI/CD](https://github.com/martibosch/netatmo-geopy/actions/workflows/dev.yml/badge.svg)](https://github.com/martibosch/netatmo-geopy/blob/main/.github/workflows/dev.yml)
[![codecov](https://codecov.io/gh/martibosch/netatmo-geopy/branch/main/graph/badge.svg?token=ZDFCCPJ6AK)](https://codecov.io/gh/martibosch/netatmo-geopy)
[![GitHub license](https://img.shields.io/github/license/martibosch/netatmo-geopy.svg)](https://github.com/martibosch/netatmo-geopy/blob/main/LICENSE)

# Netatmo GeoPy


Pythonic package to access Netatmo CWS data.

```python
import netatmo_geopy as nat

lon_sw, lat_sw, lon_ne, lat_ne = 6.5175, 46.5012, 6.7870, 46.6058
cws_recorder = nat.CWSRecorder(lon_sw, lat_sw, lon_ne, lat_ne)
gdf = cws_recorder.get_snapshot_gdf()
gdf.head()
```

<div>
    <style scoped>
     .dataframe tbody tr th:only-of-type {
         vertical-align: middle;
     }

     .dataframe tbody tr th {
         vertical-align: top;
     }

     .dataframe thead th {
         text-align: right;
     }
    </style>
    <table border="1" class="dataframe">
        <thead>
            <tr style="text-align: right;">
                <th></th>
                <th>2022-02-12T19:13</th>
                <th>geometry</th>
            </tr>
            <tr>
                <th>station_id</th>
                <th></th>
                <th></th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <th>02:00:00:01:5e:e0</th>
                <td>6.6</td>
                <td>POINT (6.82799 46.47089)</td>
            </tr>
            <tr>
                <th>02:00:00:22:c0:c0</th>
                <td>4.9</td>
                <td>POINT (6.82904 46.47005)</td>
            </tr>
            <tr>
                <th>02:00:00:2f:0b:16</th>
                <td>3.5</td>
                <td>POINT (6.82516 46.47294)</td>
            </tr>
            <tr>
                <th>02:00:00:59:00:2a</th>
                <td>3.8</td>
                <td>POINT (6.84547 46.46779)</td>
            </tr>
            <tr>
                <th>02:00:00:52:ed:5a</th>
                <td>3.8</td>
                <td>POINT (6.87359 46.47067)</td>
            </tr>
        </tbody>
    </table>
</div>

```python
nat.plot_snapshot(gdf)
```

![lausanne-snapshot](https://github.com/martibosch/netatmo-geopy/blob/main/docs/figures/lausanne.png)

See [the user guide](https://martibosch.github.io/netatmo-geopy/user-guide) for a more thorough overview of netatmo-geopy.

## Acknowledgements

* This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [zillionare/cookiecutter-pypackage](https://github.com/zillionare/cookiecutter-pypackage) project template.
