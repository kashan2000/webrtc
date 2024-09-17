import json
import asyncio
import traceback
import re
from aiortc import RTCIceCandidate, RTCIceGatherer, RTCConfiguration, RTCIceServer
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
import os
from PIL import Image
import numpy as np

app = FastAPI()

# Store peer connections for multiple users
peer_connections = {}

# WebRTC configuration (STUN servers can be added if needed)
WEBRTC_CONFIG = {
    'iceServers': [
    {
      'url': 'stun:stun.l.google.com:19302'
    },
    {
      'url': 'turn:192.158.29.39:3478?transport=udp',
      'credential': 'JZEOEt2V3Qb0y27GRntt2u2PAYA=',
      'username': '28224511:1379330808'
    },
    {
      'url': 'turn:192.158.29.39:3478?transport=tcp',
      'credential': 'JZEOEt2V3Qb0y27GRntt2u2PAYA=',
      'username': '28224511:1379330808'
    }
  ]
}

ice_servers = [
    RTCIceServer(urls=['stun:stun.l.google.com:19302']),
    # RTCIceServer(urls=['stun:stun2.l.google.com:19302']),
    # RTCIceServer(
    #     urls=['turn:192.158.29.39:3478?transport=udp'],
    #     credential='JZEOEt2V3Qb0y27GRntt2u2PAYA=',
    #     username='28224511:1379330808'
    # ),
    # RTCIceServer(
    #     urls=['turn:192.158.29.39:3478?transport=tcp'],
    #     credential='JZEOEt2V3Qb0y27GRntt2u2PAYA=',
    #     username='28224511:1379330808'
    # )
]

# Dummy video processing (converting frame to grayscale)
async def process_frame(frame, frame_count):
    # Convert the frame to an RGB image using numpy
    img = frame.to_ndarray(format="rgb24")  # Convert the frame to a numpy array
    
    # Convert the numpy array to an image
    image = Image.fromarray(img)
    
    # Save the image as PNG in the "video" folder with a unique name
    image.save(f"video/frame_{frame_count:05d}.png")
    print("iamge saved")

    # Add actual video processing logic here (for object detection or pose estimation)
    return {"object_detected": "person", "pose": "running"}

@app.post("/process_offer")
async def process_offer(request: Request):
    try:
        data = await request.json()
        offer_sdp = data.get("offer")

        if not offer_sdp:
            print("Error: Offer SDP not provided")
            raise HTTPException(status_code=400, detail="Offer SDP not provided")

        rtc_config = RTCConfiguration(iceServers=ice_servers)
        pc = RTCPeerConnection(configuration=rtc_config)
        peer_connections[pc] = pc
        # print(f"peer connection {peer_connections}")
        
        async def on_track(track):
            frame_count = 0
            if track.kind == "video":
                print("Video track received, starting to process video frames")
                while True:
                    try:
                        frame = await track.recv()
                        frame_count += 1
                        processed_data = await process_frame(frame,frame_count)
                        print(f"Processed data: {processed_data}")
                    except Exception as e:
                        print(f"Error receiving video frame: {e}")
                        break

        @pc.on("track")
        def on_track_event(track):
            asyncio.ensure_future(on_track(track))


        offer_desc = RTCSessionDescription(sdp=offer_sdp, type="offer")
        await pc.setRemoteDescription(offer_desc)

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        @pc.on("icegatheringstatechange")
        def on_ice_gathering_state_change():
            print(f"ICE gathering state changed: {pc.iceGatheringState}")

        @pc.on("iceconnectionstatechange")
        def on_ice_gathering_state_change():
            print(f"ICE connection state changed: {pc.iceConnectionState}")  

        @pc.on("connectionstatechange")
        def on_ice_gathering_state_change():
            print(f"PC connection state changed: {pc.connectionState}")        

        # print(f"offer sdk {offer_sdp}")
        # print(f"answer sdk {pc.localDescription}")

        # @pc.on("icecandidate")
        # async def on_ice_candidate_event(candidate):
        #     print("ice candidate received")
        #     if candidate:
        #         print("ICE candidate received:", candidate)
        #         await send_ice_candidate_to_signaling(candidate)
        #     else:
        #         print("ICE gathering completed (no more candidates).")


        return JSONResponse(content={"sdp": pc.localDescription.sdp})

    except Exception as e:
        print(f"Error processing offer: {e}")
        print("Stack trace:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")



def parse_ice_candidate(candidate_str, sdp_mid, sdp_mline_index):
    pattern = r"candidate:(\d+) (\d+) (\w+) (\d+) ([\da-fA-F\:\.]+) (\d+) typ (\w+)(?: raddr ([\da-fA-F\:\.]+) rport (\d+))?"
    match = re.match(pattern, candidate_str)

    if match:
        foundation = match.group(1)
        component = int(match.group(2))
        protocol = match.group(3)
        priority = int(match.group(4))
        ip = match.group(5)  # This will now match both IPv4 and IPv6 addresses
        port = int(match.group(6))
        candidate_type = match.group(7)
        related_address = match.group(8) if match.group(8) else None
        related_port = int(match.group(9)) if match.group(9) else None

        return {
            "foundation": foundation,
            "component": component,
            "protocol": protocol,
            "priority": priority,
            "ip": ip,
            "port": port,
            "type": candidate_type,
            "relatedAddress": related_address,
            "relatedPort": related_port,
            "sdpMid": sdp_mid,
            "sdpMLineIndex": sdp_mline_index
        }
    else:
        raise ValueError("Invalid ICE candidate string format")


@app.post("/process_candidate")
async def process_candidate(request: Request):
    try:
        data = await request.json()
        candidate_dict = data.get("candidate")

        if not candidate_dict:
            print("Error: ICE candidate not provided")
            raise HTTPException(status_code=400, detail="ICE candidate not provided")

        if not peer_connections:
            print("Error: No peer connection available")
            raise HTTPException(status_code=400, detail="No peer connection available")

        # Extract the relevant fields from the candidate dictionary
        sdp_mid = candidate_dict.get("sdpMid")
        sdp_mline_index = candidate_dict.get("sdpMLineIndex")
        candidate_sdp = candidate_dict.get("candidate")

        # Parse the candidate string to create an RTCIceCandidate object
        parsed_candidate = parse_ice_candidate(candidate_sdp, sdp_mid, sdp_mline_index)
        candidate = RTCIceCandidate(
            component=parsed_candidate["component"],
            foundation=parsed_candidate["foundation"],
            ip=parsed_candidate["ip"],
            port=parsed_candidate["port"],
            priority=parsed_candidate["priority"],
            protocol=parsed_candidate["protocol"],
            type=parsed_candidate["type"],
            relatedAddress=parsed_candidate.get("relatedAddress"),
            relatedPort=parsed_candidate.get("relatedPort"),
            sdpMid=parsed_candidate["sdpMid"],
            sdpMLineIndex=parsed_candidate["sdpMLineIndex"]
        )

        # Get the first peer connection (for simplicity)
        pc = next(iter(peer_connections.values()))
        # print(f"peer connection here {pc}")
        await pc.addIceCandidate(candidate)

        return JSONResponse(content={"status": "candidate processed"})

    except Exception as e:
        print(f"Error processing candidate: {e}")
        print("Stack trace:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def send_ice_candidate_to_signaling(candidate):
    try:
        import httpx
        response = await httpx.post("http://13.234.216.197:8080", json={"type": "processing_candidate", "candidate": candidate.to_map()})
        print("ICE candidate sent to signaling server")
    except Exception as e:
        print(f"Error sending ICE candidate to signaling server: {e}")
        print("Stack trace:")
        traceback.print_exc()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="debug")
