import redis
import uuid
import json
from config import REDIS_URL , REDIS_PORT, REDIS_DECODE, REDIS_HOST, REDIS_PASSWORD, REDIS_USERNAME
from postgres_persistence import save_session_to_postgres
import time

"""r = redis.Redis(
    #host=REDIS_HOST,
    #port=REDIS_PORT,
    #decode_responses=REDIS_DECODE,
    #username=REDIS_USERNAME,
    #password=REDIS_PASSWORD,
    url=REDIS_URL
)"""

r = redis.from_url(REDIS_URL, decode_responses=True)

SESSION_TTL_SECONDS = 86400

def create_session():
    session_id = str(uuid.uuid4())
    r.set(f"session:{session_id}", json.dumps([]))
    return session_id


def append_message(session_id, role, message):
    history = json.loads(r.get(f"session:{session_id}") or "[]")
    history.append({"role": role, "message": message})
    r.set(f"session:{session_id}",json.dumps(history), ex=SESSION_TTL_SECONDS)
    save_session_to_postgres(session_id, history)

def get_history(session_id):
    return json.loads(r.get(f"session:{session_id}") or "[]")

def delete_session(session_id):        
    r.delete(f"session:{session_id}")