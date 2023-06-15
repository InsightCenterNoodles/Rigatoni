# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/InsightCenterNoodles/Rigatoni/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                              |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------- | -------: | -------: | ------: | --------: |
| rigatoni/\_\_init\_\_.py          |       11 |        2 |     82% |     30-31 |
| rigatoni/core.py                  |      329 |        8 |     98% |808, 870, 900, 921, 936, 956, 978, 991 |
| rigatoni/geometry/\_\_init\_\_.py |        3 |        0 |    100% |           |
| rigatoni/geometry/byte\_server.py |       68 |       56 |     18% |32-46, 51-53, 64-70, 79-115, 124-129, 134-135, 141-143, 147 |
| rigatoni/geometry/methods.py      |      295 |      109 |     63% |59-62, 99-104, 107-112, 115-125, 176-179, 298, 333, 340, 346, 374-414, 428-440, 448-455, 472-503, 525-571, 597-600, 661-662, 700, 714, 718-719 |
| rigatoni/geometry/objects.py      |       17 |        0 |    100% |           |
| rigatoni/noodle\_objects.py       |      396 |        0 |    100% |           |
|                         **TOTAL** | **1119** |  **175** | **84%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/InsightCenterNoodles/Rigatoni/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/InsightCenterNoodles/Rigatoni/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/InsightCenterNoodles/Rigatoni/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/InsightCenterNoodles/Rigatoni/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FInsightCenterNoodles%2FRigatoni%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/InsightCenterNoodles/Rigatoni/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.