::: rigatoni.Server
    handlers:
        python:
          paths: [ . ]
          options:
            separate_signature: true
            filters: [ "!^_" ]
            docstring_options:
              ignore_init_summary: true
