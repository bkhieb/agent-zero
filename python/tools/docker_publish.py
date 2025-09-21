import asyncio
import os
from datetime import datetime
from shutil import which
from typing import Any

from python.helpers.tool import Tool, Response


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _normalize_kv_pairs(raw: Any) -> dict[str, str]:
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items()}

    if isinstance(raw, (list, tuple, set)):
        result: dict[str, str] = {}
        for item in raw:
            if isinstance(item, str) and "=" in item:
                key, value = item.split("=", 1)
                result[key.strip()] = value.strip()
        return result

    if isinstance(raw, str):
        result: dict[str, str] = {}
        for item in raw.split(","):
            item = item.strip()
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            result[key.strip()] = value.strip()
        return result

    return {}


def _normalize_collection(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(",") if item.strip()]
    if isinstance(raw, dict):
        return [str(value) for value in raw.values()]
    if isinstance(raw, (list, tuple, set)):
        return [str(item).strip() for item in raw if str(item).strip()]
    return [str(raw).strip()]


def _clean_path_segment(segment: str | None) -> str:
    if segment is None:
        return ""
    return str(segment).strip().strip("/")


def _truncate(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


class DockerPublish(Tool):
    async def execute(self, **kwargs) -> Response:
        if which("docker") is None:
            return Response(
                message="Docker CLI is not available on this system. Install Docker Desktop or the Docker engine before using this tool.",
                break_loop=False,
            )

        context_path = os.path.abspath(str(self.args.get("context_path", ".")))
        if not os.path.isdir(context_path):
            return Response(
                message=f"Build context '{context_path}' does not exist or is not a directory.",
                break_loop=False,
            )

        dockerfile = self.args.get("dockerfile")
        if dockerfile:
            dockerfile_path = dockerfile
            if not os.path.isabs(dockerfile_path):
                dockerfile_path = os.path.join(context_path, dockerfile_path)
            if not os.path.isfile(dockerfile_path):
                return Response(
                    message=f"Dockerfile '{dockerfile_path}' was not found.",
                    break_loop=False,
                )

        registry = _clean_path_segment(self.args.get("registry", "ghcr.io"))
        username = _clean_path_segment(self.args.get("username", "bkhieb"))
        project = _clean_path_segment(self.args.get("project", "trailherotv"))
        image = _clean_path_segment(self.args.get("image"))

        if not image:
            return Response(message="The 'image' argument is required (for example: nginx-hls).", break_loop=False)

        repository_parts = [registry, username]
        if project:
            repository_parts.append(project)
        repository_parts.append(image)
        repository = "/".join(part for part in repository_parts if part)

        explicit_tag = self.args.get("tag")
        if explicit_tag:
            primary_tag = str(explicit_tag).strip()
        else:
            date_value = str(self.args.get("date", datetime.utcnow().strftime("%Y%m%d"))).strip()
            iteration_value = str(self.args.get("iteration", 1)).strip()
            if not iteration_value:
                iteration_value = "1"
            primary_tag = f"{date_value}-{iteration_value}"

        image_reference = f"{repository}:{primary_tag}"

        additional_tags = _normalize_collection(self.args.get("additional_tags"))
        if _to_bool(self.args.get("tag_latest", False)) and "latest" not in additional_tags:
            additional_tags.append("latest")

        normalized_additional_refs: list[str] = []
        for tag in additional_tags:
            tag = tag.strip()
            if not tag:
                continue
            if ":" in tag or tag.startswith(registry):
                normalized_additional_refs.append(tag)
            else:
                normalized_additional_refs.append(f"{repository}:{tag}")

        build_args = _normalize_kv_pairs(self.args.get("build_args"))
        labels = _normalize_kv_pairs(self.args.get("labels"))
        target = self.args.get("target")
        platforms = _normalize_collection(self.args.get("platforms"))
        push_image = _to_bool(self.args.get("push", True), default=True)

        registry_password = self.args.get("registry_password")
        registry_username = _clean_path_segment(
            self.args.get("registry_username", username if username else None)
        )

        steps_output: list[str] = []

        if registry_password:
            login_cmd = ["docker", "login", registry or "ghcr.io", "-u", registry_username or username, "--password-stdin"]
            login_result = await self._run_command(login_cmd, cwd=context_path, input_text=str(registry_password))
            steps_output.append(self._format_result("docker login", login_result))
            if login_result[0] != 0:
                return Response(
                    message="\n\n".join(steps_output) or "Docker login failed.",
                    break_loop=False,
                )

        build_cmd: list[str] = ["docker", "build", "-t", image_reference]
        if dockerfile:
            build_cmd.extend(["-f", dockerfile if os.path.isabs(str(dockerfile)) else str(dockerfile)])

        for key, value in build_args.items():
            build_cmd.extend(["--build-arg", f"{key}={value}"])

        for key, value in labels.items():
            build_cmd.extend(["--label", f"{key}={value}"])

        if target:
            build_cmd.extend(["--target", str(target)])

        if platforms:
            build_cmd.extend(["--platform", ",".join(platforms)])

        build_cmd.append(".")

        build_result = await self._run_command(build_cmd, cwd=context_path)
        steps_output.append(self._format_result("docker build", build_result))
        if build_result[0] != 0:
            return Response(
                message="\n\n".join(steps_output) or "Docker build failed.",
                break_loop=False,
            )

        tag_commands: list[tuple[str, tuple[int, str, str]]] = []
        for extra_ref in normalized_additional_refs:
            tag_cmd = ["docker", "tag", image_reference, extra_ref]
            tag_result = await self._run_command(tag_cmd, cwd=context_path)
            tag_commands.append((extra_ref, tag_result))
            steps_output.append(self._format_result(f"docker tag -> {extra_ref}", tag_result))
            if tag_result[0] != 0:
                return Response(
                    message="\n\n".join(steps_output) or f"Failed to tag image as {extra_ref}.",
                    break_loop=False,
                )

        if push_image:
            references_to_push = [image_reference] + [ref for ref, _ in tag_commands]
            seen_refs: set[str] = set()
            for ref in references_to_push:
                if ref in seen_refs:
                    continue
                seen_refs.add(ref)
                push_cmd = ["docker", "push", ref]
                push_result = await self._run_command(push_cmd, cwd=context_path)
                steps_output.append(self._format_result(f"docker push {ref}", push_result))
                if push_result[0] != 0:
                    return Response(
                        message="\n\n".join(steps_output) or f"Failed to push {ref}.",
                        break_loop=False,
                    )

        summary_lines = [
            f"Repository: {repository}",
            f"Primary tag: {primary_tag}",
        ]
        if normalized_additional_refs:
            summary_lines.append("Additional tags: " + ", ".join(normalized_additional_refs))
        if not push_image:
            summary_lines.append("Push skipped (push=false)")

        steps_output.insert(0, "\n".join(summary_lines))

        return Response(message="\n\n".join(steps_output), break_loop=False)

    async def _run_command(
        self,
        command: list[str],
        cwd: str,
        input_text: str | None = None,
    ) -> tuple[int, str, str]:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if input_text is not None else None,
        )

        stdout_bytes, stderr_bytes = await process.communicate(
            input=input_text.encode() if input_text is not None else None
        )

        stdout = stdout_bytes.decode(errors="replace") if stdout_bytes else ""
        stderr = stderr_bytes.decode(errors="replace") if stderr_bytes else ""

        return process.returncode, stdout, stderr

    def _format_result(self, label: str, result: tuple[int, str, str]) -> str:
        code, stdout, stderr = result
        segments = [f"{label} (exit code {code})"]
        stdout = stdout.strip()
        stderr = stderr.strip()
        if stdout:
            segments.append("stdout:\n" + _truncate(stdout))
        if stderr:
            segments.append("stderr:\n" + _truncate(stderr))
        return "\n".join(segments)
