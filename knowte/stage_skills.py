"""File-backed stage guidance with application-owned contracts."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

BUILTINS = Path(__file__).resolve().parent / "skills"
CONTRACT_VERSION = "1"
MAX_SKILL_BYTES = 128 * 1024


def _error(message):
    from .ai import AIError
    return AIError("invalid_skill", message)


def _folder(stage):
    if not isinstance(stage, str) or stage not in stage_ids():
        raise _error("Unknown Knowte stage.")
    return BUILTINS / stage


def stage_ids():
    return sorted(p.name for p in BUILTINS.iterdir() if (p / "SKILL.md").is_file())


def _read(path):
    try:
        if path.stat().st_size > MAX_SKILL_BYTES:
            raise _error("Skill file is too large (maximum 128 KiB).")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise _error(f"Cannot read Skill file: {path.name}. {error}") from error


def _parse(text, stage):
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        raise _error("SKILL.md requires YAML frontmatter with stage and contract_version.")
    metadata = dict(
        (key.strip(), value.strip().strip('\"\''))
        for line in parts[1].splitlines() if ":" in line
        for key, value in [line.split(":", 1)]
    )
    if metadata.get("stage") != stage:
        raise _error(f"This Skill is not for stage {stage}.")
    if metadata.get("contract_version") != CONTRACT_VERSION:
        raise _error(f"Skill needs updating: {stage} requires contract version {CONTRACT_VERSION}.")
    if not metadata.get("name") or not metadata.get("description") or not parts[2].strip():
        raise _error("Skill name, description and instructions must not be empty.")
    return metadata, parts[2].strip()


class SkillPrompt(str):
    def __new__(cls, system, guidance, stage, contract):
        obj = str.__new__(cls, system)
        obj.guidance, obj.stage, obj.contract = guidance, stage, contract
        return obj


def skill_info(stage, directory=None, examples=()):
    builtin = _folder(stage)
    directory = Path(directory) if directory is not None else None
    custom = directory / stage if directory is not None else None
    active = bool(custom and custom.exists() and not (custom / ".disabled").exists())
    selected = custom if active else builtin
    text = _read(selected / "SKILL.md")
    metadata, body = _parse(text, stage)
    example_texts = []
    for name in examples:
        if not name.replace("_", "").isalnum():
            raise _error("Invalid example name.")
        path = selected / "examples" / f"{name}.md"
        if path.exists():
            example_texts.append(_read(path))
    if example_texts:
        body += "\n\nRelevant examples:\n" + "\n\n".join(example_texts)
    rules = _read(BUILTINS / "rules.md")
    contract = json.loads(_read(builtin / "contract.json"))
    system = rules + "\n\nStage: " + stage + "\nOutput contract (JSON Schema):\n" + json.dumps(contract, ensure_ascii=False)
    return {
        "id": stage, "label": _parse(_read(builtin / "SKILL.md"), stage)[0]["description"],
        "mode": "custom" if active else "built-in", "path": str(selected / "SKILL.md"),
        "custom_exists": bool(custom and custom.exists()),
        "contract_version": CONTRACT_VERSION, "rules": rules,
        "skill": text, "guidance": body, "contract": contract,
        "system": system, "error": "",
    }


def skill_prompt(stage, directory=None, examples=(), preferences=""):
    info = skill_info(stage, directory, examples)
    guidance = info["guidance"]
    if preferences.strip():
        guidance += "\n\nUser preferences:\n" + preferences.strip()
    return SkillPrompt(info["system"], guidance, stage, info["contract"])


def prepare_skill_request(system, user):
    if not isinstance(system, SkillPrompt):
        return system, user
    text = "Stage guidance (subject to system rules):\n" + system.guidance + "\n\nTask input:\n"
    if isinstance(user, str):
        user = text + user
    else:
        user = [{"type": "text", "text": text}, *user]
    return str(system), user


def validate_skill_result(prompt, result):
    if not isinstance(prompt, SkillPrompt) or (isinstance(result, dict) and result.get("_structured_output_degraded")):
        return result

    def check(value, schema, path):
        kind = schema.get("type")
        types = {"object": dict, "array": list, "string": str, "number": (int, float)}
        if kind in types and (not isinstance(value, types[kind]) or (kind == "number" and isinstance(value, bool))):
            raise ValueError(f"{path} must be {kind}")
        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"{path} has an unsupported value")
        if kind == "object":
            for key in schema.get("required", []):
                if key not in value:
                    raise ValueError(f"{path}.{key} is required")
            for key, item in value.items():
                if key in schema.get("properties", {}):
                    check(item, schema["properties"][key], f"{path}.{key}")
        if kind == "array":
            if len(value) > schema.get("maxItems", len(value)):
                raise ValueError(f"{path} contains too many items")
            for index, item in enumerate(value):
                check(item, schema["items"], f"{path}[{index}]")
        if kind == "number" and not schema.get("minimum", float("-inf")) <= value <= schema.get("maximum", float("inf")):
            raise ValueError(f"{path} is outside the allowed range")
    try:
        check(result, prompt.contract, "response")
    except ValueError as error:
        from .ai import AIError
        raise AIError("invalid_model_json", f"Stage output failed validation: {error}. Nothing was saved.\n\nOriginal response:\n{json.dumps(result, ensure_ascii=False)}") from error
    return result


def skill_catalog(directory):
    entries = []
    for stage in stage_ids():
        try:
            entries.append(skill_info(stage, directory, ("general",) if stage == "search_strategy" else ()))
        except Exception as error:
            from .ai import AIError
            if not isinstance(error, AIError):
                raise
            info = skill_info(stage)
            info.update(mode="custom", error=str(error), path=str(Path(directory) / stage / "SKILL.md"), custom_exists=True, skill="", guidance="")
            entries.append(info)
    return entries


def manage_skill(stage, action, directory):
    builtin = _folder(stage)
    root = Path(directory).resolve()
    custom = root / stage
    if custom.is_symlink() or (custom.exists() and not custom.is_dir()):
        raise _error("The custom Skill folder must be a regular directory.")
    if custom.exists() and any(p.is_symlink() for p in custom.rglob("*")):
        raise _error("Custom Skill folders cannot contain symbolic links.")
    if action == "customize":
        root.mkdir(parents=True, exist_ok=True)
        if not custom.exists():
            shutil.copytree(builtin, custom, ignore=shutil.ignore_patterns("contract.json"))
        _parse(_read(custom / "SKILL.md"), stage)
        (custom / ".disabled").unlink(missing_ok=True)
    elif action == "builtin":
        if custom.exists():
            (custom / ".disabled").touch()
    elif action == "reload":
        return skill_info(stage, root)
    elif action == "reveal":
        target = custom / "SKILL.md" if custom.exists() and not (custom / ".disabled").exists() else builtin / "SKILL.md"
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(target)])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target.parent)])
    else:
        raise _error("Unknown Skill action.")
    return skill_info(stage, root)
