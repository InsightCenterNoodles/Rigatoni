# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/InsightCenterNoodles/Rigatoni/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                    |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------------- | -------: | -------: | ------: | --------: |
| rigatoni/\_\_init\_\_.py                |       11 |        2 |     82% |     30-31 |
| rigatoni/core.py                        |      324 |       16 |     95% |627-628, 642, 645-648, 659, 664, 680, 707, 720, 729, 734, 742, 751, 755 |
| rigatoni/geometry/\_\_init\_\_.py       |        3 |        0 |    100% |           |
| rigatoni/geometry/byte\_server.py       |       68 |       56 |     18% |27-41, 46-48, 59-65, 75-113, 122-127, 132-133, 139-141, 145 |
| rigatoni/geometry/geometry\_creation.py |      295 |      109 |     63% |59-62, 99-104, 107-112, 115-125, 176-179, 295, 327, 334, 340, 368-408, 422-434, 442-449, 466-497, 508-555, 581-584, 645-646, 684, 698, 702-703 |
| rigatoni/geometry/geometry\_objects.py  |       17 |        0 |    100% |           |
| rigatoni/noodle\_objects.py             |      396 |        0 |    100% |           |
|                               **TOTAL** | **1114** |  **183** | **84%** |           |


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