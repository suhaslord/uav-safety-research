# Phase 6 touchdown failure decomposition

Counts are not mutually exclusive: one unsafe touchdown may violate more than one simulated touchdown criterion.

| condition   | architecture        |   episodes |   unsafe_touchdowns |   lateral_failures |   horizontal_speed_failures |   vertical_speed_failures |   mean_unsafe_x_error |   mean_unsafe_abs_vx |   mean_unsafe_abs_vz |
|:------------|:--------------------|-----------:|--------------------:|-------------------:|----------------------------:|--------------------------:|----------------------:|---------------------:|---------------------:|
| blur        | image_aegis_phase6b |        100 |                   0 |                  0 |                           0 |                         0 |              0        |            0         |             0        |
| blur        | image_aegis_v3      |        100 |                   0 |                  0 |                           0 |                         0 |              0        |            0         |             0        |
| blur        | image_temporal      |        100 |                   0 |                  0 |                           0 |                         0 |              0        |            0         |             0        |
| clean       | image_aegis_phase6b |        100 |                   0 |                  0 |                           0 |                         0 |              0        |            0         |             0        |
| clean       | image_aegis_v3      |        100 |                   0 |                  0 |                           0 |                         0 |              0        |            0         |             0        |
| clean       | image_temporal      |        100 |                   0 |                  0 |                           0 |                         0 |              0        |            0         |             0        |
| low_light   | image_aegis_phase6b |        100 |                   0 |                  0 |                           0 |                         0 |              0        |            0         |             0        |
| low_light   | image_aegis_v3      |        100 |                   0 |                  0 |                           0 |                         0 |              0        |            0         |             0        |
| low_light   | image_temporal      |        100 |                   0 |                  0 |                           0 |                         0 |              0        |            0         |             0        |
| mixed       | image_aegis_phase6b |        100 |                   1 |                  0 |                           0 |                         1 |              0.120414 |            0.33451   |             0.880087 |
| mixed       | image_aegis_v3      |        100 |                   6 |                  1 |                           5 |                         0 |              0.239349 |            0.923764  |             0.443517 |
| mixed       | image_temporal      |        100 |                  43 |                 14 |                          39 |                         0 |              0.364153 |            1.10805   |             0.502069 |
| occlusion   | image_aegis_phase6b |        100 |                   4 |                  0 |                           0 |                         4 |              0.161738 |            0.0570455 |             0.853882 |
| occlusion   | image_aegis_v3      |        100 |                   7 |                  0 |                           0 |                         7 |              0.171307 |            0.118931  |             0.830761 |
| occlusion   | image_temporal      |        100 |                  14 |                  2 |                           2 |                        10 |              0.219563 |            0.386842  |             0.717225 |
