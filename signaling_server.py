import json
import httpx
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel

app = FastAPI()

# Store connections from Flutter app and video processing server
connected_clients = {}

# URL of the video processing server
VIDEO_PROCESSING_SERVER_URL = "http://13.234.216.197:9000"

class Offer(BaseModel):
    offer: str

class Candidate(BaseModel):
    candidate: str

# Handle WebSocket connections
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            
            if data['type'] == 'offer':
                # Flutter sends the offer, relay it to the video processing server
                if 'flutter' not in connected_clients:
                    connected_clients['flutter'] = websocket
                
                print(f"Received offer from Flutter: {data['sdp']}")
                
                # Forward the offer to the video processing server
                offer_response = await send_offer_to_processing_server(data['sdp'])
                
                # Once you receive the answer from the processing server, forward it back to Flutter
                if 'flutter' in connected_clients:
                    answer = offer_response.get("sdp", "")
                    print(f"Sending answer back to Flutter to {connected_clients['flutter']}: {answer}")
                    await connected_clients['flutter'].send_json({
                        'type': 'answer',
                        'sdp': answer
                    })
            
            elif data['type'] == 'candidate':
                # Flutter sends its ICE candidate
                print(f"Received ICE candidate from Flutter: {data['candidate']}")
                
                # Forward the ICE candidate to the video processing server
                await send_ice_candidate_to_processing_server(data['candidate'])
                print("ICE candidate sent to server for storing")
            
            # elif data['type'] == 'answer':
            #     # The video processing server sends an answer, relay it back to Flutter
            #     if 'flutter' in connected_clients:
            #         print(f"Sending answer to Flutter: {data['sdp']}")
            #         await connected_clients['flutter'].send_json({
            #             'type': 'answer',
            #             'sdp': data['sdp']
            #         })
            
            elif data['type'] == 'processing_candidate':
                # Video processing server sends its ICE candidate
                if 'flutter' in connected_clients:
                    print(f"Sending processing ICE candidate to Flutter for storing")
                    await connected_clients['flutter'].send_json({
                        'type': 'candidate',
                        'candidate': data['candidate']
                    })
    
    except WebSocketDisconnect:
        print("Client disconnected")

# Send the WebRTC offer to the video processing server
async def send_offer_to_processing_server(offer: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{VIDEO_PROCESSING_SERVER_URL}/process_offer", json={"offer": offer})
            response.raise_for_status()
            return response.json()  # Expected to return answer SDP
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {"error": str(e)}

# Forward the ICE candidate to the video processing server
async def send_ice_candidate_to_processing_server(candidate: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{VIDEO_PROCESSING_SERVER_URL}/process_candidate", json={"candidate": candidate})
            response.raise_for_status()
            print("ICE candidate forwarded to video processing server")
            return response.json()
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Route to test FastAPI app
@app.get("/")
async def home():
    return {"message": "WebRTC Signaling Server is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
