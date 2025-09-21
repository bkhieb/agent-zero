### docker_publish

build and optionally push docker images to github container registry
default registry `ghcr.io`, username sourced from `REGISTRY_USER`, project `trailherotv`
default tag format `{date}-{iteration}` e.g. `20250913-1`

required environment:
- `REGISTRY_USER`: github packages / ghcr username used for repository namespace and docker login
- `REGISTRY_PASSWORD`: personal access token (with `write:packages`) stored as a secret/environment variable used for login

the tool aborts when `push=true` and either variable is missing, and surfaces a warning when building without credentials

required args:
- `image`: service or component name appended after project path

optional args:
- `context_path`: build context directory, default `.`
- `dockerfile`: path to Dockerfile relative to context
- `project`: override project segment in image path
- `username`: override registry username when building without pushing (defaults to `REGISTRY_USER`)
- `registry`: override container registry domain
- `tag`: explicit tag override (use when not following date-iteration format)
- `date`: date used when building default tag (`YYYYMMDD`)
- `iteration`: iteration number used in default tag
- `additional_tags`: list or comma separated string of extra tags (e.g. `latest`)
- `tag_latest`: boolean, append `latest` tag automatically when true
- `build_args`: dict or `KEY=VALUE` pairs passed with `--build-arg`
- `labels`: dict or `KEY=VALUE` pairs for image labels
- `target`: optional build stage target
- `platforms`: list or comma separated platforms for `--platform`
- `push`: boolean, set false to skip `docker push`

returns build and push logs together with the published image references

before invoking confirm docker cli is installed, the build context contains the intended Dockerfile, and the `REGISTRY_USER`/`REGISTRY_PASSWORD` variables are exported in the environment (e.g. via `export` or a secrets manager)
avoid exposing secrets in conversation history; keep `REGISTRY_PASSWORD` sourced from a secret manager when possible

usage example:

~~~json
{
    "thoughts": [
        "Need to publish nginx-hls image for today's release",
        "Use the docker_publish tool with date-tag naming"
    ],
    "headline": "Build and push nginx-hls image",
    "tool_name": "docker_publish",
    "tool_args": {
        "image": "nginx-hls",
        "date": "20250913",
        "iteration": 1,
        "context_path": "./deploy/nginx-hls",
        "dockerfile": "Dockerfile",
        "additional_tags": ["latest"]
    }
}
~~~
