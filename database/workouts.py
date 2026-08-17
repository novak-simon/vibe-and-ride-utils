from typing import Any, List, Optional, TYPE_CHECKING, Union

from database.methods import _extract_data, _effective_client, _value_exists
from models.model_methods import _is_bike_sport
from models.workout_model import Workout

if TYPE_CHECKING:
    from workout_parsing.workout_parser import ZwoNode

def upload_workout(workout: Workout, client: Any | None = None) -> None:
    client = _effective_client(client)

    data = workout.to_record()
    response = (
        client.table("workouts")
        .insert(data)
        .select("*")
        .execute()
    )
    records = _extract_data(response)
    if not records:
        raise RuntimeError("Failed to insert workout")