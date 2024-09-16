import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';

class Webrtc extends StatefulWidget {
  const Webrtc({super.key});

  @override
  State<Webrtc> createState() => _WebrtcState();
}

class _WebrtcState extends State<Webrtc> {
  late WebSocketChannel channel;
  late RTCPeerConnection peerConnection;
  late MediaStream localStream;
  final RTCVideoRenderer _localRenderer = RTCVideoRenderer();
  final RTCVideoRenderer _remoteRenderer = RTCVideoRenderer();

  @override
  void initState() {
    super.initState();
    _localRenderer.initialize();
    _remoteRenderer.initialize();
    // Initialize the WebSocket connection to the signaling server
    channel = WebSocketChannel.connect(
      Uri.parse(
          'ws://127.0.0.1:8080/ws'), // Replace with your signaling server's IP and port
    );
    print("channel>> $channel");
    // Start the WebRTC connection process
  }

  @override
  void dispose() {
    _localRenderer.dispose();
    _remoteRenderer.dispose();
    channel.sink.close();
    super.dispose();
  }

  // Function to initialize WebRTC connection
  Future<void> initWebRTC() async {
    print("init web rtc");
    // Get user media (front camera)
    localStream = await navigator.mediaDevices.getUserMedia({
      'video': {
        'width': {'min': 640, 'ideal': 1280},
        'height': {'min': 640, 'ideal': 720},
        'facingMode': 'user',
      }, // Front camera
      'audio': false,
    });
    _localRenderer.srcObject = localStream;

    // Set up the RTCPeerConnection configuration
    final Map<String, dynamic> configuration = {
      'iceServers': [
        {'urls': 'stun:stun.l.google.com:19302'}, // STUN server
      ]
    };
    peerConnection = await createPeerConnection(configuration);

    // Add the local stream (video) to the peer connection
    localStream.getTracks().forEach((track) {
      print("getting track");
      peerConnection.addTrack(track, localStream);
    });

    // Handle ICE candidates and send them to the signaling server
    peerConnection.onIceCandidate = (RTCIceCandidate candidate) {
      if (candidate != null) {
        try {
          // Serialize the candidate to JSON
          channel.sink.add(jsonEncode({
            'type': 'candidate',
            'candidate': candidate.toMap(),
          }));
        } catch (er, st) {
          print("Error in sending ICE candidate: $er and $st");
        }
        print('Sending ICE candidate: ${candidate.candidate}');
      }
    };

    // Handle remote stream and display it in the remote renderer
    peerConnection.onTrack = (RTCTrackEvent event) {
      if (event.track.kind == 'video') {
        _remoteRenderer.srcObject = event.streams[0];
      }
    };

    // Create and send an offer to the signaling server
    createOffer();
  }

  // Function to create an offer and send it to the signaling server
  Future<void> createOffer() async {
    RTCSessionDescription offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);

    try {
      // Serialize the offer to JSON
      channel.sink.add(jsonEncode({
        'type': 'offer',
        'sdp': offer.sdp,
      }));
    } catch (er, st) {
      print("Error in sending offer: $er and $st");
    }
    print('Sending offer to signaling server: ${offer.sdp}');
    setState(() {});
  }

  // Function to receive answer from the signaling server
  void handleSignalingMessage(dynamic message) {
    print("listning to ssignalling message ");
    print("mssg> $message");
    var jsonMessage = jsonDecode(message);
    print("converted msg> $message");
    try {
      if (jsonMessage['type'] == 'answer') {
        print('Received answer from signaling server:}');
        RTCSessionDescription answer =
            RTCSessionDescription(jsonMessage['sdp'], 'answer');
        peerConnection.setRemoteDescription(answer);
      }
      // Handle ICE candidates from the remote peer
      else if (jsonMessage['type'] == 'candidate') {
        RTCIceCandidate candidate = RTCIceCandidate(
          jsonMessage['candidate']['candidate'],
          jsonMessage['candidate']['sdpMid'],
          jsonMessage['candidate']['sdpMLineIndex'],
        );
        peerConnection.addCandidate(candidate);
        print(
            'Received ICE candidate from signaling server: ${candidate.candidate}');
      } else {
        print(("messae>> "));
        print("err> $jsonMessage");
      }
    } catch (er, st) {
      print("error in handle> $er and $st");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
        appBar: AppBar(
          backgroundColor: Theme.of(context).colorScheme.inversePrimary,
          title: const Text("Web RTC"),
        ),
        body: Column(
          children: [
            Expanded(
              child: RTCVideoView(
                _localRenderer,
                mirror: true,
              ),
            ),
            ElevatedButton(
              onPressed: () {
                // Handle button press, initialize WebRTC if needed

                // Listen to signaling server messages
                initWebRTC();
                channel.stream.listen(handleSignalingMessage);
              },
              child: const Text("Start Drill"),
            ),
          ],
        ));
  }
}
