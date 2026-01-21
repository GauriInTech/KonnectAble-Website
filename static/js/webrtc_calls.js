/**
 * WebRTC Call Handler - Enhanced calling features with ringing notifications
 */

class WebRTCCallHandler {
    constructor() {
        this.localStream = null;
        this.peerConnection = null;
        this.currentCallId = null;
        this.isInitiator = false;
        this.ringtone = null;
        this.callDurationInterval = null;
        this.callStartTime = null;
        
        this.initializeElements();
    }
    
    initializeElements() {
        // Call modal elements
        this.callModal = document.getElementById('callModal');
        this.incomingCallAlert = document.getElementById('incomingCallAlert');
        this.activeCallInterface = document.getElementById('activeCallInterface');
        
        // Control buttons
        this.acceptCallBtn = document.getElementById('acceptCallBtn');
        this.declineCallBtn = document.getElementById('declineCallBtn');
        this.endCallBtn = document.getElementById('endCallBtn');
        this.muteCallBtn = document.getElementById('muteCallBtn');
        this.speakerCallBtn = document.getElementById('speakerCallBtn');
        
        // Display elements
        this.callUserName = document.getElementById('callUserName');
        this.callDuration = document.getElementById('callDuration');
        this.incomingCallerName = document.getElementById('incomingCallerName');
        this.incomingCallType = document.getElementById('incomingCallType');
        
        // Ringtone
        this.ringtone = document.getElementById('ringtoneAudio');
        
        // Bind event listeners
        if (this.acceptCallBtn) this.acceptCallBtn.addEventListener('click', () => this.acceptCall());
        if (this.declineCallBtn) this.declineCallBtn.addEventListener('click', () => this.declineCall());
        if (this.endCallBtn) this.endCallBtn.addEventListener('click', () => this.endCall());
        if (this.muteCallBtn) this.muteCallBtn.addEventListener('click', () => this.toggleMute());
        if (this.speakerCallBtn) this.speakerCallBtn.addEventListener('click', () => this.toggleSpeaker());
    }
    
    /**
     * Show incoming call notification
     */
    showIncomingCall(callData) {
        this.currentCallId = callData.call_id;
        this.isInitiator = false;
        
        // Update UI
        this.incomingCallerName.textContent = callData.caller_name;
        this.incomingCallType.textContent = callData.call_type === 'video' ? 'Video' : 'Audio';
        
        // Show incoming call interface
        if (this.incomingCallAlert) {
            this.incomingCallAlert.style.display = 'block';
        }
        if (this.activeCallInterface) {
            this.activeCallInterface.style.display = 'none';
        }
        
        // Show modal
        if (this.callModal) {
            this.callModal.style.display = 'flex';
        }
        
        // Play ringtone
        this.playRingtone();
        
        // Show toast notification
        this.showNotification(`${callData.caller_name} is calling...`, 'info');
    }
    
    /**
     * Show active call interface
     */
    showActiveCall(userName) {
        this.callUserName.textContent = userName;
        
        if (this.incomingCallAlert) {
            this.incomingCallAlert.style.display = 'none';
        }
        if (this.activeCallInterface) {
            this.activeCallInterface.style.display = 'block';
        }
        
        // Start call timer
        this.startCallTimer();
        
        // Stop ringtone
        this.stopRingtone();
    }
    
    /**
     * Accept incoming call
     */
    async acceptCall() {
        try {
            this.stopRingtone();
            
            // Request media permissions
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: true,
                video: false
            });
            
            this.localStream = stream;
            
            // Send accept action through WebSocket
            if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {
                window.chatSocket.send(JSON.stringify({
                    type: 'call',
                    action: 'answer',
                    call_id: this.currentCallId,
                }));
            }
            
            // Show active call interface
            this.showActiveCall(otherUserName);
            
            this.showNotification('Call connected', 'success');
        } catch (error) {
            console.error('Error accepting call:', error);
            this.showNotification('Failed to access microphone: ' + error.message, 'error');
        }
    }
    
    /**
     * Decline incoming call
     */
    declineCall() {
        this.stopRingtone();
        
        if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {
            window.chatSocket.send(JSON.stringify({
                type: 'call',
                action: 'decline',
                call_id: this.currentCallId,
            }));
        }
        
        this.hideCallModal();
        this.showNotification('Call declined', 'info');
    }
    
    /**
     * End active call
     */
    endCall() {
        this.stopRingtone();
        this.stopCallTimer();
        
        if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {
            window.chatSocket.send(JSON.stringify({
                type: 'call',
                action: 'end',
                call_id: this.currentCallId,
            }));
        }
        
        // Stop media streams
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
        
        this.hideCallModal();
        this.showNotification('Call ended', 'info');
    }
    
    /**
     * Toggle microphone mute
     */
    toggleMute() {
        if (this.localStream) {
            const audioTracks = this.localStream.getAudioTracks();
            audioTracks.forEach(track => {
                track.enabled = !track.enabled;
            });
            
            if (this.muteCallBtn) {
                this.muteCallBtn.classList.toggle('active');
            }
        }
    }
    
    /**
     * Toggle speaker
     */
    toggleSpeaker() {
        if (this.speakerCallBtn) {
            this.speakerCallBtn.classList.toggle('active');
        }
    }
    
    /**
     * Play ringtone sound
     */
    playRingtone() {
        if (this.ringtone) {
            this.ringtone.loop = true;
            this.ringtone.volume = 0.5;
            this.ringtone.play().catch(error => {
                console.warn('Could not play ringtone:', error);
            });
        }
    }
    
    /**
     * Stop ringtone sound
     */
    stopRingtone() {
        if (this.ringtone) {
            this.ringtone.pause();
            this.ringtone.currentTime = 0;
        }
    }
    
    /**
     * Start call duration timer
     */
    startCallTimer() {
        this.callStartTime = Date.now();
        this.callDurationInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.callStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            
            if (this.callDuration) {
                this.callDuration.textContent = 
                    `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
            }
        }, 1000);
    }
    
    /**
     * Stop call duration timer
     */
    stopCallTimer() {
        if (this.callDurationInterval) {
            clearInterval(this.callDurationInterval);
            this.callDurationInterval = null;
        }
    }
    
    /**
     * Hide call modal
     */
    hideCallModal() {
        if (this.callModal) {
            this.callModal.style.display = 'none';
        }
    }
    
    /**
     * Show notification toast
     */
    showNotification(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} alert-dismissible fade show`;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            animation: slideIn 0.3s ease;
        `;
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(toast);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
}

// Initialize WebRTC call handler
const webrtcCallHandler = new WebRTCCallHandler();

// Export for use in messaging.js
window.webrtcCallHandler = webrtcCallHandler;
