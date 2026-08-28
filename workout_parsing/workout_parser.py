from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, List, Optional, Union

from database.workouts import upload_workout
from database.admin_client import get_admin_supabase
from models.workout_model import Workout, Interval
admin_client = get_admin_supabase()

logger = logging.getLogger(__name__)

class WorkoutParser:
    def __init__(self, client: Any | None = None):
        self.client = client if client is not None else admin_client

    def parse(self, limit: int = 50, stop_removal: bool = False) -> None:
        parsed_paths = self.parse_workouts(limit=limit)
        if not stop_removal:
            for path in parsed_paths:
                try:
                    path.unlink()
                except Exception as e:
                    logger.error(f"Failed to remove parsed workout file {path}: {e}")
        for path in parsed_paths: print(path)

    def parse_zwo_string(self, content: str, file_name: str = "Unnamed workout") -> Workout:
        root = ET.fromstring(content)
        intervals = []
        name = file_name
        author = "Unknown"
        sport_type = "Bike"
        description = ""
        tags = []

        for child in root:
            if child.tag == "author":
                author = str(child.text)
            elif child.tag == "name":
                if not str(child.text) == "Zwift Workout":
                    name = str(child.text)
                else:
                    name = file_name
            elif child.tag == "sportType":
                sport_type = str(child.text)
            elif child.tag == "description":
                description = str(child.text)
            elif child.tag == "tags":
                tags = [str(tag.text) for tag in child if tag.text]
            elif child.tag == "workout":
                for ch in child:
                    intervals.append(Interval(
                        duration=float(ch.attrib.get("Duration", 0)),
                        power=float(ch.attrib.get("Power", 0)),
                        power_low=float(ch.attrib.get("PowerLow", 0)),
                        power_high=float(ch.attrib.get("PowerHigh", 0)),
                        cadence=float(ch.attrib.get("Cadence", 0)),
                        cadence_low=float(ch.attrib.get("CadenceLow", 0)),
                        cadence_high=float(ch.attrib.get("CadenceHigh", 0)),
                        type=str(ch.tag),
                    ))
        return Workout(
            name=name,
            author=author,
            sport_type=sport_type,
            tags=tags,
            description=description,
            intervals=intervals,
        )

    def parse_zwo_file(self, path: Union[str, Path]) -> None:
        path_obj = Path(path)
        with path_obj.open("r", encoding="utf-8") as file:
            source = Path(path)
            workout = self.parse_zwo_string(file.read(), source.stem)
            print(workout)
            upload_workout(workout, client=admin_client)

    def _default_asset_dirs(self) -> Path:
        base = Path(__file__).resolve().parents[1] / "assets"
        return base / "raw_workouts"

    def parse_workouts(self, limit: int = 50, raw_dir: Optional[Union[str, Path]] = None) -> List[Path]:
        if raw_dir is None:
            raw_dir = self._default_asset_dirs()
        raw_dir = Path(raw_dir)

        parsed_paths: List[Path] = []
        for source in sorted(raw_dir.glob("*.zwo"))[:limit]:
            target_path = raw_dir / f"{source.stem}.zwo"
            self.parse_zwo_file(source)
            parsed_paths.append(target_path)
        return parsed_paths