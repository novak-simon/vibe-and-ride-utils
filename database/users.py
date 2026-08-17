from typing import Optional, Any

from user.model import User
from database.methods import _effective_client, _extract_data, _user_from_record

def get_user_by_id(id: int, client: Any | None = None) -> Optional[User]:
    client = _effective_client(client)
    response = (
        client.table("users")
        .select("*")
        .eq("id", id)
        .limit(1)
        .execute()
    )
    records = _extract_data(response)
    return _user_from_record(records[0]) if records else None