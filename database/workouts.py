from typing import Any
from database.methods import _extract_data, _effective_client
from models.workout_model import Workout

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