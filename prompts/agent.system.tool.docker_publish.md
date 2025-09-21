### docker_publish

build and optionally push docker images to github container registry
default registry `ghcr.io`, username `bkhieb`, project `trailherotv`
default tag format `{date}-{iteration}` e.g. `20250913-1`

required args:
- `image`: service or component name appended after project path

optional args:
- `context_path`: build context directory, default `.`
- `dockerfile`: path to Dockerfile relative to context
- `project`: override project segment in image path
- `username`: override registry username
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
- `registry_username`: username used for registry login (defaults to `username`)
- `registry_password`: personal access token or password piped to `docker login`

returns build and push logs together with the published image references

before invoking confirm docker cli is installed, the build context contains the intended Dockerfile, and credentials for ghcr are configured or provided
avoid exposing secrets in conversation history; supply `registry_password` only when necessary

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
