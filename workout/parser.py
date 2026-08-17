from __future__ import annotations

import logging
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from database.workouts import upload_parsed_file
from database.admin_client import get_admin_supabase
admin_client = get_admin_supabase()

ZwoValue = Union[str, int, float, bool, None]
ZwoNode = Dict[str, Any]

logger = logging.getLogger(__name__)


def _set_workout_name(parsed: ZwoNode | List[ZwoNode], name: str) -> None:
    def _replace_name_node(node: ZwoNode) -> None:
        if node.get("type") == "name":
            node["text"] = name
            return

        children = node.get("children")
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    _replace_name_node(child)

    if isinstance(parsed, dict):
        _replace_name_node(parsed)
        return parsed

    for item in parsed:
        if isinstance(item, dict):
            _replace_name_node(item)
    return parsed


def _parse_value(value: Optional[str]) -> ZwoValue:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower == "none":
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _extract_interval_info(element: ET.Element) -> Optional[Dict[str, ZwoValue]]:
    attrs = {key: _parse_value(val) for key, val in element.attrib.items()}
    duration = attrs.get("Duration") or attrs.get("OnDuration") or attrs.get("OffDuration")
    power = attrs.get("Power") or attrs.get("OnPower") or attrs.get("OffPower")
    cadence = attrs.get("Cadence")
    if duration is None and power is None and cadence is None:
        return None
    return {"duration": duration, "power": power, "cadence": cadence}


def _parse_element(element: ET.Element) -> ZwoNode:
    node: ZwoNode = {
        "type": element.tag,
        "attrs": {key: _parse_value(val) for key, val in element.attrib.items()},
    }

    interval = _extract_interval_info(element)
    if interval is not None:
        node["interval"] = interval

    children = [_parse_element(child) for child in element]
    if children:
        node["children"] = children

    text = element.text.strip() if element.text and element.text.strip() else None
    if text:
        node["text"] = text

    return node


def _collect_tags(workout_element: ET.Element) -> List[str]:
    tags = []
    for tag in workout_element.findall("Tags/Tag"):
        name = tag.attrib.get("Name")
        if name:
            tags.append(name)
    return tags


def _get_child_text(parent: ET.Element, child_tag: str) -> Optional[str]:
    child = parent.find(child_tag)
    if child is not None and child.text:
        return child.text.strip()
    return None


def _parse_workout_element(workout_element: ET.Element) -> ZwoNode:
    workout = {
        "type": "Workout",
        "name": workout_element.attrib.get("Name"),
        "author": workout_element.attrib.get("Author"),
        "sport_type": _parse_value(workout_element.attrib.get("SportType")),
        "tags": _collect_tags(workout_element),
        "description": _get_child_text(workout_element, "Description"),
        "children": [],
    }

    for child in workout_element:
        if child.tag in {"Description", "Tags"}:
            continue
        workout["children"].append(_parse_element(child))

    return workout


def parse_zwo_string(content: str) -> Union[ZwoNode, List[ZwoNode]]:
    root = ET.fromstring(content)
    if root.tag == "Workouts":
        return [_parse_workout_element(workout) for workout in root.findall("Workout")]
    if root.tag == "Workout":
        return _parse_workout_element(root)
    return _parse_element(root)


def parse_zwo_file(path: Union[str, Path]) -> Union[ZwoNode, List[ZwoNode]]:
    path_obj = Path(path)
    with path_obj.open("r", encoding="utf-8") as file:
        parsed = parse_zwo_string(file.read())
        source = Path(path)
        parsed = _set_workout_name(parsed, source.stem)
        upload_parsed_file(parsed, client=admin_client)
        return parsed


def _default_asset_dirs() -> tuple[Path, Path]:
    base = Path(__file__).resolve().parents[1] / "assets"
    return base / "raw_workouts", base / "parsed_workouts"


def parse_all_workouts(
    raw_dir: Optional[Union[str, Path]] = None,
    parsed_dir: Optional[Union[str, Path]] = None,
    force: bool = False,
) -> List[Path]:
    if raw_dir is None or parsed_dir is None:
        raw_dir, parsed_dir = _default_asset_dirs()
    raw_dir = Path(raw_dir)
    parsed_dir = Path(parsed_dir)
    parsed_dir.mkdir(parents=True, exist_ok=True)

    parsed_paths: List[Path] = []
    for source in sorted(raw_dir.glob("*.zwo")):
        target_path = parsed_dir / f"{source.stem}.json"
        if target_path.exists() and not force:
            continue
        parse_zwo_file(source)
        parsed_paths.append(target_path)
    return parsed_paths