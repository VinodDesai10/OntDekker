import uuid

def generate_uuid() -> uuid.UUID:
    return uuid.uuid4()

def generate_uuid_str() -> str:
    return str(uuid.uuid4())
