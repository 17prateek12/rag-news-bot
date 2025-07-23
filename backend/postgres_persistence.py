from models import SessionLocal, ChatHistory

def save_session_to_postgres(session_id: str, history: list[dict]):
    db = SessionLocal()
    try:
        for entry in history:
            db.add(ChatHistory(
                session_id=session_id,
                role=entry["role"],
                message=entry["message"]
            ))
        db.commit()
    finally:
        db.close()