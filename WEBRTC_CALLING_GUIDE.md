# WebRTC Calling Features - Implementation Guide

## 🎉 What's Been Implemented (Phase 1-3 Critical Features)

### ✅ **1. Database Enhancements**
- Added WebRTC signaling fields to Call model:
  - `webrtc_offer`: Stores SDP offer
  - `webrtc_answer`: Stores SDP answer  
  - `ice_candidates`: Stores ICE candidates (JSON array)
  - `ringing_until`: Tracks call timeout
  - `is_answered`: Tracks if call was ever answered
  - `is_missed`: Tracks if call expired without answer

### ✅ **2. Call Timeout Logic (30 seconds)**
**File**: [message/consumers.py](message/consumers.py)

Features:
- Auto-decline calls after 30 seconds of ringing
- Timeout task created when call initiates
- Task cancelled when call is answered/declined
- Status changed to 'missed' if timeout occurs
- Both users notified when call times out

**Implementation**:
```python
# In ChatConsumer
CALL_TIMEOUT_SECONDS = 30

async def handle_call_timeout(self, call_id):
    """Auto-decline call after timeout"""
    await asyncio.sleep(CALL_TIMEOUT_SECONDS)
    # Auto-decline logic...
```

### ✅ **3. Ringing Notifications**
**Files**: 
- [message/templates/message/components/call_modal.html](message/templates/message/components/call_modal.html)
- [static/js/webrtc_calls.js](static/js/webrtc_calls.js)

Features:
- Visual incoming call alert with caller name & photo
- Animated ringing dots animation
- Ringtone audio playback
- Accept/Decline/Mute/Speaker buttons
- Real-time call duration display
- Toast notifications for call events

**Ringing Animation** - Custom CSS animations for:
- Bouncing dots
- Pulse effects
- Smooth transitions

### ✅ **4. WebRTC Signaling Framework**
**File**: [message/consumers.py](message/consumers.py)

Implemented handlers for:
- `handle_webrtc_offer()` - Receive & relay SDP offer
- `handle_webrtc_answer()` - Receive & relay SDP answer
- `handle_ice_candidate()` - Receive & relay ICE candidates
- `store_webrtc_offer()` - Persist offer to DB
- `store_webrtc_answer()` - Persist answer to DB
- `store_ice_candidate()` - Persist ICE candidates to DB

**WebSocket Message Types**:
```javascript
{
    type: 'webrtc_offer',
    call_id: '...',
    offer: { type: 'offer', sdp: '...' }
}

{
    type: 'webrtc_answer', 
    call_id: '...',
    answer: { type: 'answer', sdp: '...' }
}

{
    type: 'ice_candidate',
    call_id: '...',
    candidate: { candidate: '...', sdpMLineIndex: 0, ... }
}
```

### ✅ **5. Frontend Integration**
**Files**:
- [static/js/webrtc_calls.js](static/js/webrtc_calls.js) - WebRTC call handler class
- [static/js/messaging.js](static/js/messaging.js) - Updated with new message handlers
- [message/templates/message/conversation_detail.html](message/templates/message/conversation_detail.html) - Added WebRTC script

**WebRTC Handler Class** - Manages:
- Local media stream acquisition
- Call state management
- Ringtone playback/stopping
- Call duration tracking
- Microphone muting
- Speaker toggling
- Modal display/hide

**Message Handlers** in messaging.js:
- `handleCallRinging()` - Trigger incoming call alert
- `handleCallMissed()` - Handle timed-out calls
- `handleWebRTCOffer()` - Set remote SDP offer
- `handleWebRTCAnswer()` - Set remote SDP answer  
- `handleICECandidate()` - Add ICE candidate

---

## 📋 How to Use

### For Users:
1. **Initiate Call**: Click audio/video call button in chat header
2. **Receive Call**: When called, modal appears with caller info
3. **Answer**: Click green phone button to accept
4. **Decline**: Click red X button to reject
5. **During Call**:
   - Click mute button to toggle microphone
   - Click speaker button to toggle speaker
   - Click red phone button to end call

### For Developers:

#### Initiate a Call:
```javascript
messagingApp.initiateCall('audio'); // or 'video'
```

#### Handle Incoming Ringing:
```javascript
// Automatically handled by messaging.js
// When 'call_ringing' event received, shows UI alert
```

#### Send WebRTC Offer:
```javascript
chatSocket.send(JSON.stringify({
    type: 'webrtc_offer',
    call_id: callId,
    offer: { type: 'offer', sdp: '...' }
}));
```

#### Send ICE Candidate:
```javascript
chatSocket.send(JSON.stringify({
    type: 'ice_candidate',
    call_id: callId,
    candidate: iceCandidate
}));
```

---

## 🔧 Configuration

### Call Timeout:
- Default: 30 seconds
- Location: [message/consumers.py](message/consumers.py) line 14
- Change: `CALL_TIMEOUT_SECONDS = 30`

### Ringtone Volume:
- Location: [static/js/webrtc_calls.js](static/js/webrtc_calls.js) line 217
- Change: `this.ringtone.volume = 0.5` (0-1)

---

## 📱 Next Steps - Simple-Peer Integration (Optional)

To enable actual audio/video streaming, you'll need:

1. **Install simple-peer**:
```bash
npm install simple-peer
```

2. **Add to webrtc_calls.js**:
```javascript
import SimplePeer from 'simple-peer';

// In WebRTCCallHandler:
this.peer = new SimplePeer({
    initiator: isInitiator,
    trickle: true,
    stream: this.localStream
});

this.peer.on('signal', data => {
    // Send SDP offer/answer & ICE candidates
});
```

3. **Handle stream**:
```javascript
this.peer.on('stream', stream => {
    // Display remote video/audio
    remoteVideo.srcObject = stream;
});
```

---

## 🎵 Adding Ringtone Audio

1. **Get or create ringtone**:
   - Options: Record, download from free source, use generator
   - Format: MP3 (recommended), WAV, OGG

2. **Place in project**:
   ```
   static/sounds/ringtone.mp3
   ```

3. **Verify in template**:
   ```html
   <audio id="ringtoneAudio" preload="auto">
       <source src="{% static 'sounds/ringtone.mp3' %}" type="audio/mpeg">
   </audio>
   ```

---

## 🧪 Testing Checklist

- [ ] Call timeout auto-declines after 30s
- [ ] Ringing animation displays correctly
- [ ] Ringtone plays when receiving call
- [ ] Accept button shows incoming call interface
- [ ] Decline button closes modal & notifies sender
- [ ] Mute button toggles microphone state
- [ ] Call duration timer updates
- [ ] End call closes modal & notifies peer
- [ ] Browser console shows no errors

---

## 📊 Database Schema Updates

**Call Model Changes**:
```python
class Call(models.Model):
    # ... existing fields ...
    
    # NEW - WebRTC Fields
    ringing_until = models.DateTimeField(null=True, blank=True)
    webrtc_offer = models.JSONField(null=True, blank=True)
    webrtc_answer = models.JSONField(null=True, blank=True)
    ice_candidates = models.JSONField(default=list, blank=True)
    is_answered = models.BooleanField(default=False)
    is_missed = models.BooleanField(default=False)
```

**Migration Applied**: `0002_webrtc_call_improvements.py`

---

## 🚀 Performance Notes

- Call timeout handled asynchronously (no blocking)
- ICE candidates stored in DB for call history
- WebRTC signaling is peer-to-peer (after initial WebSocket handshake)
- Ringtone loops until stopped (saves memory)

---

## 🔐 Security Notes

- All WebRTC signaling validated through authenticated WebSocket
- Call participants verified before WebRTC exchange
- Offer/answer/candidates validated in database
- Timeout prevents indefinite resource allocation

---

## 📚 Related Files

- [message/models.py](message/models.py) - Call model definition
- [message/consumers.py](message/consumers.py) - WebSocket consumer with call logic
- [message/views.py](message/views.py) - Call API views
- [README_MESSAGING_APP.md](README_MESSAGING_APP.md) - General messaging guide

---

## 🎯 Future Enhancements (Phase 4+)

- [ ] Video streaming integration
- [ ] Call recording
- [ ] Group calling
- [ ] Call transfer
- [ ] Call hold/resume
- [ ] Call quality monitoring
- [ ] Network diagnostics
- [ ] Advanced codecs support

---

**Status**: ✅ Ready to Test  
**Last Updated**: 2026-01-21  
**Version**: 1.0
