/**
 * Real-time Messaging Application
 * Features: WebSocket messaging, typing indicators, calls, read receipts
 * Theme: Modern with pink/rose primary color
 */

class MessagingApp {
    constructor() {
        // Get conversation ID from data attribute instead of global var
        const messageInput = document.getElementById('messageInput');
        this.conversationId = messageInput ? messageInput.getAttribute('data-conversation-id') : null;
        this.otherUserId = otherUserId;
        this.currentUserId = currentUserId;
        this.socket = null;
        this.callState = {
            isActive: false,
            callId: null,
            startTime: null,
            isInitiator: false,
        };
        this.typingTimeout = null;
        this.isTyping = false;
        this.messageCache = new Map();
        this.init();
    }

    /**
     * Initialize the application
     */
    init() {
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.connectWebSocket();
        this.loadConversationsList();
        this.scrollToBottom();
        this.setupResponsiveUI();
        this.checkInitialUserStatus();
    }
    
    /**
     * Check initial user status when conversation loads
     */
    checkInitialUserStatus() {
        // Fetch user online status on page load
        fetch(`/message/api/user/${this.otherUserId}/status/`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status) {
                this.updateUserStatusUI(data.status);
            }
        })
        .catch(error => console.log('[Status] Could not fetch initial status:', error));
    }

    /**
     * Setup WebSocket connection for real-time messaging
     */
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/${this.conversationId}/`;
        
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('[WebSocket] Connected to chat server');
            this.updateConnectionStatus(true);
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleSocketMessage(data);
        };

        this.socket.onclose = () => {
            console.log('[WebSocket] Disconnected from chat server');
            this.updateConnectionStatus(false);
            // Reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };

        this.socket.onerror = (error) => {
            console.error('[WebSocket] Error:', error);
        };
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleSocketMessage(data) {
        const { type } = data;

        switch (type) {
            case 'message':
                this.handleNewMessage(data);
                break;
            case 'typing':
                this.handleTypingIndicator(data);
                break;
            case 'user_status':
                this.handleUserStatus(data);
                break;
            case 'message_read':
                this.handleMessageRead(data);
                break;
            case 'batch_messages_read':
                this.handleBatchMessagesRead(data);
                break;
            case 'call_initiated':
                this.handleIncomingCall(data);
                break;
            case 'call_ringing':
                this.handleCallRinging(data);
                break;
            case 'call_answered':
                this.handleCallAnswered(data);
                break;
            case 'call_declined':
                this.handleCallDeclined(data);
                break;
            case 'call_ended':
                this.handleCallEnded(data);
                break;
            case 'call_missed':
                this.handleCallMissed(data);
                break;
            case 'webrtc_offer':
                this.handleWebRTCOffer(data);
                break;
            case 'webrtc_answer':
                this.handleWebRTCAnswer(data);
                break;
            case 'ice_candidate':
                this.handleICECandidate(data);
                break;
            case 'error':
                this.showError(data.message);
                break;
            default:
                console.warn('[WebSocket] Unknown message type:', type);
        }
    }

    /**
     * ==================== MESSAGE HANDLING ====================
     */

    /**
     * Handle new message from WebSocket
     */
    handleNewMessage(data) {
        // Add message to DOM
        this.addMessageToDOM(data, false);
        
        // Mark as read if not sent by current user
        if (data.sender_id !== this.currentUserId) {
            this.markMessageAsRead(data.message_id);
        }
        
        // Play notification sound
        this.playNotificationSound();
    }

    /**
     * Add message to DOM
     */
    addMessageToDOM(data, isSent = false) {
        const messagesContainer = document.getElementById('messagesContent');
        
        // Create message group
        const messageGroup = document.createElement('div');
        messageGroup.className = `message-group ${isSent ? 'sent' : 'received'}`;
        messageGroup.setAttribute('data-message-id', data.message_id || data.id);

        // Create message element
        const message = document.createElement('div');
        message.className = 'message message-bubble';

        // Message content
        const content = document.createElement('div');
        content.className = 'message-content';
        content.textContent = data.content;

        // Message time with read receipt
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        const time = new Date(data.created_at).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        let readReceipt = '';
        if (isSent) {
            const checkClass = data.is_read ? 'read' : '';
            const checkIcon = data.is_read ? 'bi-check-all' : 'bi-check';
            readReceipt = `<span class="read-receipt ${checkClass}"><i class="bi ${checkIcon} check-icon"></i></span>`;
        }
        
        timeDiv.innerHTML = `${time}${readReceipt}`;

        message.appendChild(content);
        message.appendChild(timeDiv);
        messageGroup.appendChild(message);
        messagesContainer.appendChild(messageGroup);

        // Scroll to bottom
        this.scrollToBottom();
    }

    /**
     * Send message
     */
    sendMessage() {
        const input = document.getElementById('messageInput');
        if (!input) return;

        const content = input.value.trim();
        if (!content) return;

        // Disable send button
        const sendBtn = document.getElementById('sendBtn');
        if (sendBtn) {
            sendBtn.disabled = true;
        }

        // Create optimistic message
        const message = {
            message_id: 'temp-' + Date.now(),
            sender_id: this.currentUserId,
            sender: currentUsername,
            content: content,
            created_at: new Date().toISOString(),
            is_read: false,
        };

        // Add to DOM immediately
        this.addMessageToDOM(message, true);

        // Send via WebSocket
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'message',
                content: content,
            }));
        }

        // Clear input and reset typing
        input.value = '';
        input.style.height = 'auto';
        this.notifyTypingStatus(false);
        if (sendBtn) {
            sendBtn.disabled = false;
        }

        // Resize textarea
        this.autoResizeTextarea(input);
    }

    /**
     * Mark message as read
     */
    markMessageAsRead(messageId) {
        // Send read receipt via WebSocket
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'read_receipt',
                message_id: messageId,
            }));
        }
    }

    /**
     * Handle message read receipt
     */
    handleMessageRead(data) {
        const messageId = data.message_id;
        const messageGroup = document.querySelector(`[data-message-id="${messageId}"]`);
        
        if (!messageGroup) {
            console.warn(`[Read Receipt] Message element not found for ID: ${messageId}`);
            return;
        }

        // Update read receipt icon
        const readReceipt = messageGroup.querySelector('.read-receipt');
        if (readReceipt) {
            readReceipt.classList.add('read');
            const checkIcon = readReceipt.querySelector('.check-icon');
            if (checkIcon) {
                checkIcon.classList.remove('bi-check');
                checkIcon.classList.add('bi-check-all');
                console.log(`[Read Receipt] Message ${messageId} marked as read by ${data.read_by}`);
            }
        } else {
            console.warn(`[Read Receipt] No read-receipt element found in message ${messageId}`);
        }
    }

    /**
     * Handle batch read receipt for multiple messages
     */
    handleBatchMessagesRead(data) {
        console.log(`[Read Receipt] Batch update: ${data.count} messages marked as read by ${data.read_by}`);
        
        data.message_ids.forEach(messageId => {
            // Try different selectors to find the message
            let messageGroup = document.querySelector(`[data-message-id="${messageId}"]`);
            
            if (!messageGroup) {
                console.warn(`[Read Receipt] Message element not found for ID: ${messageId}`);
                return;
            }

            // Update read receipt icon
            const readReceipt = messageGroup.querySelector('.read-receipt');
            if (readReceipt) {
                // Add read class
                readReceipt.classList.add('read');
                
                // Update check icon
                const checkIcon = readReceipt.querySelector('.check-icon');
                if (checkIcon) {
                    checkIcon.classList.remove('bi-check');
                    checkIcon.classList.add('bi-check-all');
                    console.log(`[Read Receipt] Updated icon for message ${messageId}`);
                }
            } else {
                console.warn(`[Read Receipt] No read-receipt element found in message ${messageId}`);
            }
        });
    }

    /**
     * ==================== TYPING INDICATOR ====================
     */

    /**
     * Handle typing indicator
     */
    handleTypingIndicator(data) {
        const indicator = document.getElementById('typingIndicator');
        
        if (data.is_typing) {
            indicator.style.display = 'flex';
        } else {
            indicator.style.display = 'none';
        }
    }

    /**
     * Handle user online/offline status
     */
    handleUserStatus(data) {
        const { user_id, status } = data;
        
        // Only update if it's the other user (not current user)
        if (user_id !== this.currentUserId) {
            this.updateUserStatusUI(status);
        }
    }

    /**
     * Update user status UI
     */
    updateUserStatusUI(status) {
        const statusElement = document.getElementById('statusText');
        const statusDot = document.querySelector('.status-dot');
        
        if (statusElement) {
            statusElement.textContent = status;
        }
        
        if (statusDot) {
            if (status === 'online') {
                statusDot.classList.add('online');
                statusElement.style.color = '#22c55e';
            } else {
                statusDot.classList.remove('online');
                statusElement.style.color = '#6b7280';
            }
        }
        
        console.log(`[Status] User is now ${status}`);
    }

    /**
     * Notify other user of typing status
     */
    notifyTypingStatus(isTyping) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'typing',
                is_typing: isTyping,
            }));
        }
    }

    /**
     * ==================== CALL HANDLING ====================
     */

    /**
     * Initiate call
     */
    initiateCall(callType) {
        fetch('/message/api/initiate-call/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken'),
            },
            body: JSON.stringify({
                conversation_id: this.conversationId,
                call_type: callType,
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showCallModal({
                    id: data.call_id,
                    type: callType,
                }, true);

                // Notify other user
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                    this.socket.send(JSON.stringify({
                        type: 'call',
                        action: 'initiate',
                        call_type: callType,
                        call_id: data.call_id,
                    }));
                }
            }
        })
        .catch(error => this.showError('Error initiating call: ' + error.message));
    }

    /**
     * Handle incoming call
     */
    handleIncomingCall(data) {
        this.callState.callId = data.call_id;
        this.callState.isInitiator = false;

        this.showCallModal({
            id: data.call_id,
            type: data.call_type,
            initiator: data.initiator,
        }, false);
    }

    /**
     * Show call modal
     */
    showCallModal(callData, isInitiator) {
        const modal = document.getElementById('callModal');
        
        // Update call info
        document.getElementById('callUserName').textContent = otherUserName;
        document.getElementById('callTypeBadge').textContent = 
            (callData.type === 'audio' ? 'Audio Call' : 'Video Call');
        document.getElementById('callStatusText').textContent = 
            (isInitiator ? 'Calling...' : 'Incoming call...');

        // Update buttons
        const answerBtn = document.getElementById('answerCallBtn');
        const declineBtn = document.getElementById('declineCallBtn');
        const endBtn = document.getElementById('endCallBtn');

        if (isInitiator) {
            answerBtn.style.display = 'none';
            declineBtn.style.display = 'block';
            endBtn.style.display = 'none';
        } else {
            answerBtn.style.display = 'block';
            declineBtn.style.display = 'block';
            endBtn.style.display = 'none';
        }

        // Show modal
        modal.style.display = 'flex';
        this.callState.isActive = true;
        this.callState.callId = callData.id;
        this.callState.isInitiator = isInitiator;
    }

    /**
     * Answer call
     */
    answerCall() {
        if (!this.callState.callId) return;

        fetch('/message/api/answer-call/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken'),
            },
            body: JSON.stringify({
                call_id: this.callState.callId,
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.handleCallAnswered();
            }
        })
        .catch(error => this.showError('Error answering call: ' + error.message));
    }

    /**
     * Decline call
     */
    declineCall() {
        if (!this.callState.callId) return;

        fetch('/message/api/decline-call/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken'),
            },
            body: JSON.stringify({
                call_id: this.callState.callId,
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.handleCallDeclined();
            }
        })
        .catch(error => this.showError('Error declining call: ' + error.message));
    }

    /**
     * End call
     */
    endCall() {
        if (!this.callState.callId) return;

        fetch('/message/api/end-call/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken'),
            },
            body: JSON.stringify({
                call_id: this.callState.callId,
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.handleCallEnded();
            }
        })
        .catch(error => this.showError('Error ending call: ' + error.message));
    }

    /**
     * Handle call answered
     */
    handleCallAnswered() {
        const modal = document.getElementById('callModal');
        document.getElementById('callStatusText').textContent = 'Connected';
        document.getElementById('answerCallBtn').style.display = 'none';
        document.getElementById('declineCallBtn').style.display = 'none';
        document.getElementById('callTimer').style.display = 'inline';
        document.getElementById('endCallBtn').style.display = 'block';

        this.startCallTimer();
    }

    /**
     * Handle call declined
     */
    handleCallDeclined() {
        this.closeCallModal();
        this.showNotification('Call declined');
    }

    /**
     * Handle call ended
     */
    handleCallEnded() {
        this.closeCallModal();
        this.callState.isActive = false;
    }

    /**
     * Handle call ringing notification - trigger WebRTC handler
     */
    handleCallRinging(data) {
        console.log('[Messaging] Call ringing:', data);
        
        // Use WebRTC handler if available
        if (window.webrtcCallHandler) {
            window.webrtcCallHandler.showIncomingCall({
                call_id: data.call_id,
                caller_name: data.caller_name,
                call_type: data.call_type,
            });
        }
    }

    /**
     * Handle missed/auto-declined call
     */
    handleCallMissed(data) {
        console.log('[Messaging] Call missed:', data);
        this.closeCallModal();
        this.callState.isActive = false;
        
        if (data.reason === 'no_answer') {
            this.showNotification('Call was not answered', 'info');
        } else {
            this.showNotification('Call missed', 'info');
        }
    }

    /**
     * Handle WebRTC SDP offer
     */
    handleWebRTCOffer(data) {
        console.log('[Messaging] WebRTC offer received:', data.call_id);
        
        if (window.webrtcCallHandler && window.webrtcCallHandler.peerConnection) {
            window.webrtcCallHandler.peerConnection.setRemoteDescription(
                new RTCSessionDescription(data.offer)
            ).catch(error => {
                console.error('Error setting remote description:', error);
            });
        }
    }

    /**
     * Handle WebRTC SDP answer
     */
    handleWebRTCAnswer(data) {
        console.log('[Messaging] WebRTC answer received:', data.call_id);
        
        if (window.webrtcCallHandler && window.webrtcCallHandler.peerConnection) {
            window.webrtcCallHandler.peerConnection.setRemoteDescription(
                new RTCSessionDescription(data.answer)
            ).catch(error => {
                console.error('Error setting remote description:', error);
            });
        }
    }

    /**
     * Handle ICE candidate
     */
    handleICECandidate(data) {
        console.log('[Messaging] ICE candidate received:', data.call_id);
        
        if (window.webrtcCallHandler && window.webrtcCallHandler.peerConnection) {
            if (data.candidate) {
                window.webrtcCallHandler.peerConnection.addIceCandidate(
                    new RTCIceCandidate(data.candidate)
                ).catch(error => {
                    console.error('Error adding ICE candidate:', error);
                });
            }
        }
    }

    /**
     * Close call modal
     */
    closeCallModal() {
        const modal = document.getElementById('callModal');
        modal.style.display = 'none';
        
        if (this.callState.startTime) {
            clearInterval(this.callState.startTime);
        }
    }

    /**
     * Start call timer
     */
    startCallTimer() {
        const startTime = Date.now();
        const timerEl = document.getElementById('callTimer');
        
        const interval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            
            timerEl.textContent = 
                `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }, 1000);

        this.callState.startTime = interval;
    }

    /**
     * ==================== CONVERSATIONS LIST ====================
     */

    /**
     * Load conversations list
     */
    loadConversationsList() {
        fetch('/message/api/conversations/', {
            headers: {
                'X-CSRFToken': this.getCookie('csrftoken'),
            },
        })
        .then(response => response.json())
        .then(data => {
            const list = document.getElementById('conversationsList');
            list.innerHTML = '';

            if (data.conversations && data.conversations.length > 0) {
                data.conversations.forEach(conv => {
                    const item = this.createConversationItem(conv);
                    list.appendChild(item);
                });
            } else {
                list.innerHTML = '<div class="empty-state" style="padding: 20px;"><p>No conversations yet</p></div>';
            }
        })
        .catch(error => console.error('Error loading conversations:', error));
    }

    /**
     * Create conversation item element
     */
    createConversationItem(conv) {
        const link = document.createElement('a');
        link.href = `/message/conversation/${conv.id}/`;
        link.className = `conversation-item ${conv.id === this.conversationId ? 'active' : ''}`;

        const time = new Date(conv.updated_at).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });

        link.innerHTML = `
            <div class="conversation-item-content">
                <div class="conversation-header-row">
                    <span class="conversation-name">${this.escapeHtml(conv.other_user)}</span>
                    <span class="conversation-time">${time}</span>
                </div>
                <div class="conversation-preview">
                    <span class="preview-text">${this.escapeHtml(conv.last_message || 'No messages')}</span>
                    ${conv.unread_count > 0 ? `<span class="unread-badge">${conv.unread_count}</span>` : ''}
                </div>
            </div>
        `;

        return link;
    }

    /**
     * ==================== EVENT LISTENERS ====================
     */

    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        // Message sending
        const sendBtn = document.getElementById('sendBtn');
        const messageInput = document.getElementById('messageInput');

        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            // Auto-resize textarea
            messageInput.addEventListener('input', (e) => {
                this.autoResizeTextarea(e.target);
                this.handleTypingInput();
            });
        }

        // Call buttons
        const audioCallBtn = document.getElementById('audioCallBtn');
        const videoCallBtn = document.getElementById('videoCallBtn');

        if (audioCallBtn) {
            audioCallBtn.addEventListener('click', () => this.initiateCall('audio'));
        }
        if (videoCallBtn) {
            videoCallBtn.addEventListener('click', () => this.initiateCall('video'));
        }

        // Call modal buttons
        const answerBtn = document.getElementById('answerCallBtn');
        const declineBtn = document.getElementById('declineCallBtn');
        const endBtn = document.getElementById('endCallBtn');

        if (answerBtn) {
            answerBtn.addEventListener('click', () => this.answerCall());
        }
        if (declineBtn) {
            declineBtn.addEventListener('click', () => this.declineCall());
        }
        if (endBtn) {
            endBtn.addEventListener('click', () => this.endCall());
        }

        // Mobile sidebar toggle
        const mobileToggle = document.getElementById('mobileSidebarToggle');
        if (mobileToggle) {
            mobileToggle.addEventListener('click', () => {
                const sidebar = document.getElementById('conversationsSidebar');
                if (sidebar) {
                    sidebar.classList.toggle('active');
                }
            });
        }

        // Close sidebar when clicking conversation
        const conversations = document.querySelectorAll('.conversation-item');
        conversations.forEach(conv => {
            conv.addEventListener('click', () => {
                const sidebar = document.getElementById('conversationsSidebar');
                if (sidebar) {
                    sidebar.classList.remove('active');
                }
            });
        });

        // Attach file button
        const attachBtn = document.getElementById('attachBtn');
        const fileInput = document.getElementById('fileInput');

        if (attachBtn && fileInput) {
            attachBtn.addEventListener('click', () => fileInput.click());
        }

        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileSelection(e));
        }

        // Search conversations
        const searchInput = document.getElementById('conversationSearch');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.searchConversations(e.target.value));
        }

        // User search for new conversations
        const userSearchInput = document.getElementById('userSearchInput');
        if (userSearchInput) {
            userSearchInput.addEventListener('input', (e) => this.searchUsers(e.target.value));
        }
    }

    /**
     * Handle typing input
     */
    handleTypingInput() {
        if (!this.isTyping) {
            this.isTyping = true;
            this.notifyTypingStatus(true);
        }

        clearTimeout(this.typingTimeout);
        this.typingTimeout = setTimeout(() => {
            this.isTyping = false;
            this.notifyTypingStatus(false);
        }, 3000);
    }

    /**
     * Auto-resize textarea
     */
    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 100) + 'px';
    }

    /**
     * Handle file selection
     */
    handleFileSelection(event) {
        const files = event.target.files;
        if (files.length === 0) return;

        for (let file of files) {
            this.uploadFile(file);
        }
    }

    /**
     * Upload file
     */
    uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('conversation_id', this.conversationId);

        fetch('/message/api/upload-file/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCookie('csrftoken'),
            },
            body: formData,
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showNotification(`File "${file.name}" uploaded successfully`);
            }
        })
        .catch(error => this.showError('Error uploading file: ' + error.message));
    }

    /**
     * Search conversations
     */
    searchConversations(query) {
        const list = document.getElementById('conversationsList');
        const items = list.querySelectorAll('.conversation-item');

        items.forEach(item => {
            const name = item.querySelector('.conversation-name').textContent.toLowerCase();
            item.style.display = name.includes(query.toLowerCase()) ? '' : 'none';
        });
    }

    /**
     * Search users
     */
    searchUsers(query) {
        const resultsContainer = document.getElementById('userSearchResults');
        if (resultsContainer) {
            resultsContainer.innerHTML = '';
        }

        if (query.trim().length < 2) return;

        try {
            fetch(`/user/search/?q=${encodeURIComponent(query)}`, {
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken'),
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.results && data.results.length > 0 && resultsContainer) {
                    data.results.forEach(user => {
                        const userEl = document.createElement('a');
                        userEl.href = `/message/new/${user.username}/`;
                        userEl.className = 'conversation-item';
                        userEl.innerHTML = `
                            <div class="conversation-item-content">
                                <div class="conversation-header-row">
                                    <span class="conversation-name">${this.escapeHtml(user.first_name || user.username)}</span>
                                </div>
                                <div class="conversation-preview">
                                    <span class="preview-text">@${this.escapeHtml(user.username)}</span>
                                </div>
                            </div>
                        `;
                        resultsContainer.appendChild(userEl);
                    });
                }
            })
            .catch(error => console.error('Error searching users:', error));
        } catch (error) {
            console.error('Error in searchUsers:', error);
        }
    }

    /**
     * ==================== UI UTILITIES ====================
     */

    /**
     * Setup responsive UI
     */
    setupResponsiveUI() {
        // Close sidebar when window is resized to desktop size
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                document.getElementById('conversationsSidebar').classList.remove('active');
            }
        });
    }

    /**
     * Scroll to bottom of messages
     */
    scrollToBottom() {
        const container = document.getElementById('messagesContent');
        if (container) {
            setTimeout(() => {
                container.scrollTop = container.scrollHeight;
            }, 0);
        }
    }

    /**
     * Update connection status
     */
    updateConnectionStatus(isConnected) {
        // You can update a visual indicator here if needed
        console.log('[Connection]', isConnected ? 'Connected' : 'Disconnected');
    }

    /**
     * Show notification
     */
    showNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'alert alert-info alert-dismissible fade show';
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '1000';
        notification.innerHTML = `
            ${this.escapeHtml(message)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }

    /**
     * Show error
     */
    showError(message) {
        const error = document.createElement('div');
        error.className = 'alert alert-danger alert-dismissible fade show';
        error.style.position = 'fixed';
        error.style.top = '20px';
        error.style.right = '20px';
        error.style.zIndex = '1000';
        error.innerHTML = `
            ${this.escapeHtml(message)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(error);
        setTimeout(() => error.remove(), 5000);
    }

    /**
     * Play notification sound (optional)
     */
    playNotificationSound() {
        try {
            const audio = new Audio('data:audio/wav;base64,UklGRiYAAABXQVZFZm10IBAAAAABAAEAQB8AAAB9AAACABAAZGF0YQIAAAAAAA==');
            audio.play().catch(() => {});
        } catch (e) {
            // Silent failure for notification sound
        }
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Get cookie value
     */
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    /**
     * Enhanced Features: Notifications, Gestures, Advanced Features
     */

    /**
     * Show browser notification for new messages
     */
    showNotificationBrowser(title, options = {}) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, {
                icon: '/static/images/favicon.png',
                badge: '/static/images/favicon.png',
                ...options,
            });
        }
    }

    /**
     * Request notification permission
     */
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }

    /**
     * Debounce search input to prevent excessive requests
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Format timestamp to readable format
     */
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
        });
    }

    /**
     * Highlight text in search results
     */
    highlightMatch(text, query) {
        if (!query) return text;
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    /**
     * Get emoji reaction summary
     */
    getReactionSummary(message) {
        // Placeholder for emoji reactions feature
        // Will be implemented in future updates
        return null;
    }

    /**
     * Detect message type (emoji, URL, etc.)
     */
    detectMessageType(content) {
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        const emojiRegex = /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu;
        
        return {
            hasUrl: urlRegex.test(content),
            hasEmoji: emojiRegex.test(content),
            length: content.length,
            isLong: content.length > 200,
            isShort: content.length < 5,
        };
    }

    /**
     * Generate message preview for list display
     */
    getMessagePreview(content, maxLength = 50) {
        if (!content) return 'Image or media';
        const preview = content.replace(/\n/g, ' ').substring(0, maxLength);
        return content.length > maxLength ? preview + '...' : preview;
    }

    /**
     * Archive conversation
     */
    archiveConversation() {
        // Placeholder for archive feature
        console.log('Archive conversation feature coming soon');
    }

    /**
     * Mute conversation notifications
     */
    muteConversation(duration = 3600000) {
        const muteUntil = new Date(Date.now() + duration);
        localStorage.setItem(`mute_${this.conversationId}`, muteUntil.toISOString());
        this.showSuccess('Conversation muted');
    }

    /**
     * Clear conversation history (local only)
     */
    clearLocalHistory() {
        if (confirm('Clear all messages from this conversation?')) {
            const messageElements = document.querySelectorAll('.message-bubble');
            messageElements.forEach(el => el.remove());
            this.messageCache.clear();
            this.showSuccess('Local history cleared');
        }
    }

    /**
     * Export conversation as text
     */
    exportConversation() {
        const messages = Array.from(this.messageCache.values());
        let text = `Conversation Export\nDate: ${new Date().toLocaleString()}\n\n`;
        
        messages.forEach(msg => {
            const sender = msg.sender_id === this.currentUserId ? 'You' : 'Other';
            const time = new Date(msg.created_at).toLocaleString();
            text += `${sender} (${time}): ${msg.content}\n`;
        });

        const blob = new Blob([text], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `conversation_${this.conversationId}.txt`;
        a.click();
        window.URL.revokeObjectURL(url);
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        const div = document.createElement('div');
        div.className = 'alert alert-success position-fixed top-0 start-50 translate-middle-x mt-3';
        div.textContent = message;
        document.body.appendChild(div);
        setTimeout(() => div.remove(), 3000);
    }

    /**
     * Keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+Enter to send message
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                const textarea = document.querySelector('.message-input');
                if (document.activeElement === textarea) {
                    this.sendMessage();
                    e.preventDefault();
                }
            }
            
            // Escape to close modal
            if (e.key === 'Escape') {
                const modals = document.querySelectorAll('.modal.show');
                modals.forEach(modal => {
                    const bsModal = new bootstrap.Modal(modal);
                    bsModal.hide();
                });
            }
        });
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.messagingApp = new MessagingApp();
    
    // Request notification permission
    if ('Notification' in window) {
        window.messagingApp.requestNotificationPermission();
    }
});

