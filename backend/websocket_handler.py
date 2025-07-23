from fastapi import WebSocket, WebSocketDisconnect
from rag_pipeline import generate_answer
from chat_manager import get_history, append_message
import asyncio


active_connection = {}

async def handle_websocket(websocket: WebSocket,session_id:str):
    await websocket.accept()
    
    if session_id not in active_connection:
        active_connection[session_id]  = []
    active_connection[session_id].append(websocket)
    
    try:
        history =get_history(session_id)
        await websocket.send_json({"history":history})
        
        while True:
            data = await websocket.receive_text()
            append_message(session_id, 'user', data)
            
            # Run blocking answer generation off the event loop
            bot_response = await asyncio.to_thread(generate_answer, data)
        
            append_message(session_id, 'bot', bot_response)
            
            for connection in active_connection[session_id]:
                await connection.send_json({'role': 'bot', 'message': bot_response})
        
                
    except WebSocketDisconnect:
        active_connection[session_id].remove(websocket)
        if not active_connection[session_id]:
            del active_connection[session_id]
        
