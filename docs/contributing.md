# Contributing

Any help with the project would be super appreciated. Here are some steps to get started.

1. Clone the repo
2. Install the dependencies
   ```bash
   pip install -r requirements.txt
   pip install -r tests/requirements.txt
   ```
3. Switch to the `develop` branch or create a new one
4. Make your changes
5. To update the documentation, simply edit the docstrings for each method.
6. Run the tests
    - These flags will help show which lines are missing test coverage
   ```bash
    pytest --cov rigatoni --cov-report term-missing
   ```
7. Submit a pull request
    - There are github actions set up to run the tests and build the docs for each pull request.
   