# Message App - Implementation Guide for Critical Fixes

## Quick Start: Apply These Fixes Immediately

### Fix #1: Security - Validate Conversation on Read Receipt (HIGH PRIORITY)

**File:** `message/consumers.py`

Replace the `mark_message_as_read()` method:

```python
@database_sync_to_async
def mark_message_as_read(self, message_id):
    """Mark a message as read - with conversation validation"""
    try:
        # CRITICAL: Verify message belongs to this conversation
        message = Message.objects.get(
            id=message_id,
            conversation_id=self.room_name
        )
        
        # Only mark as read if the current user is not the sender
        if message.sender.id != self.user.id:
            message.mark_as_read()
            logger.info(f"Message {message_id} marked as read by {self.user.username}")
        else:
            logger.warning(f"User {self.user.username} tried to mark own message as read")
    except Message.DoesNotExist:
        logger.warning(f"Message {message_id} not found in conversation {self.room_name}")
```

---

### Fix #2: MarkAsReadAPIView - Add Conversation Validation

**File:** `message/views.py`

Add security check to the `MarkAsReadAPIView`:

```python
@method_decorator(login_required, name='dispatch')
class MarkAsReadAPIView(View):
    """API endpoint to mark a message as read"""
    
    def post(self, request, message_id):
        user = request.user
        message = get_object_or_404(Message, id=message_id)
        
        # CRITICAL: Verify user is part of the conversation
        conversation = message.conversation
        if not (conversation.participant1 == user or conversation.participant2 == user):
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        # Check if user is not the sender
        if message.sender == user:
            return JsonResponse({'error': 'Cannot mark your own message as read'}, status=400)
        
        message.mark_as_read()
        
        return JsonResponse({
            'success': True,
            'is_read': message.is_read,
            'read_at': message.read_at.isoformat(),
        })
```

---

### Fix #3: Broadcast Bulk Read Receipts on Page Load

**File:** `message/views.py`

Update the `conversation_detail_view()` to broadcast read receipts:

```python
@login_required
def conversation_detail_view(request, conversation_id):
    """
    Display detailed conversation with all messages between two users.
    Handles message sending and read receipts.
    """
    user = request.user
    try:
        conversation = Conversation.objects.get(
            Q(participant1=user, id=conversation_id) | Q(participant2=user, id=conversation_id)
        )
    except Conversation.DoesNotExist:
        raise Http404("Conversation not found")
    
    # Get other user
    other_user = conversation.get_other_user(user)
    
    # Mark all unread messages from other user as read
    unread_messages = Message.objects.filter(
        conversation=conversation,
        sender=other_user,
        is_read=False
    ).select_related('sender')
    
    # Get list of message IDs before updating
    unread_message_ids = list(unread_messages.values_list('id', flat=True))
    
    # Update database
    unread_messages.update(is_read=True, read_at=timezone.now())
    
    # Broadcast read receipts via WebSocket to notify sender
    from channels.layers import get_channel_layer
    import json
    from asgiref.sync import async_to_sync
    
    channel_layer = get_channel_layer()
    room_group_name = f'chat_{conversation_id}'
    
    # Send a batch read notification
    if unread_message_ids:
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'batch_messages_read',
                'message_ids': [str(msg_id) for msg_id in unread_message_ids],
                'read_by': user.username,
                'read_by_id': user.id,
                'read_at': timezone.now().isoformat(),
            }
        )
        logger.info(f"Marked {len(unread_message_ids)} messages as read for {user.username}")
    
    # ... rest of existing code ...
```

**Add handler in `consumers.py`:**

```python
async def batch_messages_read(self, event):
    """Handle batch read receipt event"""
    # Only send to the sender (not the reader)
    if event['read_by_id'] != self.user.id:
        await self.send(text_data=json.dumps({
            'type': 'batch_messages_read',
            'message_ids': event['message_ids'],
            'read_by': event['read_by'],
            'read_by_id': event['read_by_id'],
            'read_at': event['read_at'],
            'count': len(event['message_ids']),
        }))
```

**Update JavaScript handler in `messaging.js`:**

```javascript
handleSocketMessage(data) {
    const { type } = data;

    switch (type) {
        case 'message':
            this.handleNewMessage(data);
            break;
        case 'typing':
            this.handleTypingIndicator(data);
            break;
        case 'message_read':
            this.handleMessageRead(data);
            break;
        case 'batch_messages_read':  // NEW
            this.handleBatchMessagesRead(data);
            break;
        case 'call_initiated':
            this.handleIncomingCall(data);
            break;
        // ... rest of cases
    }
}

/**
 * Handle batch read receipt for multiple messages
 */
handleBatchMessagesRead(data) {
    console.log(`Received batch read receipt: ${data.count} messages marked as read by ${data.read_by}`);
    
    data.message_ids.forEach(messageId => {
        const messageGroup = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageGroup) {
            const readReceipt = messageGroup.querySelector('.read-receipt');
            if (readReceipt) {
                readReceipt.classList.add('read');
                const checkIcon = readReceipt.querySelector('.check-icon');
                if (checkIcon) {
                    checkIcon.classList.remove('bi-check');
                    checkIcon.classList.add('bi-check-all');
                }
            }
        }
    });
}
```

---

### Fix #4: Add Message Acknowledgments (ACK)

**File:** `message/consumers.py`

Update `handle_message()` method:

```python
async def handle_message(self, data):
    """Handle new message with proper acknowledgment"""
    try:
        content = data.get('content', '').strip()
        
        if not content:
            await self.send_error("Message cannot be empty")
            return
        
        # Get temp ID from client for correlation
        temp_id = data.get('temp_id')
        
        # Save message to database
        message = await self.save_message(content)
        
        # Remove typing status when message is sent
        await self.remove_typing_status()
        
        # Send ACK FIRST - directly to sender
        await self.send(text_data=json.dumps({
            'type': 'message_ack',
            'temp_id': temp_id,
            'message_id': str(message.id),
            'created_at': message.created_at.isoformat(),
            'status': 'sent',  # Message successfully persisted
        }))
        
        # Broadcast message to OTHER clients in room (not back to sender)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': str(message.id),
                'sender': message.sender.username,
                'sender_id': message.sender.id,
                'content': message.content,
                'created_at': message.created_at.isoformat(),
                'is_read': message.is_read,
            }
        )
        
        logger.info(f"Message {message.id} from {message.sender.username} saved and broadcasted")
        
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await self.send_error(f"Error sending message: {str(e)}")
```

---

### Fix #5: Implement Read Receipt Retries in JavaScript

**File:** `static/js/messaging.js`

Replace `markMessageAsRead()` method:

```javascript
/**
 * Mark message as read with retry mechanism
 */
markMessageAsRead(messageId, retries = 3) {
    if (!messageId) return;
    
    const attempt = (retriesLeft) => {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'read_receipt',
                message_id: messageId,
            }));
            console.log(`[Read Receipt] Sent for message ${messageId}`);
        } else if (retriesLeft > 0) {
            console.warn(`[Read Receipt] WebSocket not ready, retrying... (${retriesLeft} left)`);
            setTimeout(() => attempt(retriesLeft - 1), 500);
        } else {
            console.error(`[Read Receipt] Failed to send after retries for message ${messageId}`);
            
            // Store for later retry when connection is restored
            this.failedReadReceipts = this.failedReadReceipts || [];
            if (!this.failedReadReceipts.includes(messageId)) {
                this.failedReadReceipts.push(messageId);
            }
        }
    };
    
    attempt(retries);
}
```

**Update connection status handler:**

```javascript
updateConnectionStatus(isConnected) {
    const statusEl = document.getElementById('connectionStatus');
    if (statusEl) {
        statusEl.textContent = isConnected ? 'Connected' : 'Disconnected';
        statusEl.className = isConnected ? 'status-connected' : 'status-disconnected';
    }
    
    this.isConnected = isConnected;
    
    // Process failed read receipts when connection is restored
    if (isConnected && this.failedReadReceipts && this.failedReadReceipts.length > 0) {
        console.log(`[Read Receipts] Retrying ${this.failedReadReceipts.length} failed read receipts`);
        const failedIds = [...this.failedReadReceipts];
        this.failedReadReceipts = [];
        
        failedIds.forEach(messageId => {
            setTimeout(() => this.markMessageAsRead(messageId), 100);
        });
    }
}
```

---

### Fix #6: Enhanced Message ACK Handler in JavaScript

**File:** `static/js/messaging.js`

Add new method:

```javascript
/**
 * Handle message acknowledgment from server
 */
handleMessageAck(data) {
    const { temp_id, message_id, created_at, status } = data;
    
    // Find optimistic message by temp ID
    const tempElement = document.querySelector(`[data-message-id="${temp_id}"]`);
    
    if (tempElement) {
        // Update from temporary ID to actual message ID
        tempElement.setAttribute('data-message-id', message_id);
        tempElement.classList.remove('message-pending');
        tempElement.classList.add('message-sent');
        
        // Update timestamp if needed
        const timeDiv = tempElement.querySelector('.message-time');
        if (timeDiv) {
            const actualTime = new Date(created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
            });
            // Update time but preserve read receipt
            const readReceipt = timeDiv.querySelector('.read-receipt');
            timeDiv.innerHTML = actualTime;
            if (readReceipt) {
                timeDiv.appendChild(readReceipt);
            }
        }
        
        // Cache the actual message ID for future operations
        if (!this.messageCache.has(message_id)) {
            this.messageCache.set(message_id, {
                id: message_id,
                tempId: temp_id,
                status: status,
                createdAt: created_at,
            });
        }
        
        logger.info(`Message ACK: temp=${temp_id} → actual=${message_id}`);
    } else {
        console.warn(`[Message ACK] Could not find element with temp ID ${temp_id}`);
    }
}
```

Update `handleSocketMessage()` to include the new case:

```javascript
handleSocketMessage(data) {
    const { type } = data;

    switch (type) {
        case 'message_ack':          // NEW
            this.handleMessageAck(data);
            break;
        case 'message':
            this.handleNewMessage(data);
            break;
        // ... rest of cases
    }
}
```

---

### Fix #7: Update `sendMessage()` to Use Temp IDs

**File:** `static/js/messaging.js`

```javascript
/**
 * Send message with temp ID for tracking
 */
sendMessage() {
    const input = document.getElementById('messageInput');
    const content = input.value.trim();

    if (!content) return;

    // Disable send button
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;

    // Create unique temp ID
    const tempId = `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Create optimistic message
    const message = {
        message_id: tempId,
        sender_id: this.currentUserId,
        sender: currentUsername,
        content: content,
        created_at: new Date().toISOString(),
        is_read: false,
    };

    // Add to DOM immediately
    this.addMessageToDOM(message, true);

    // Send via WebSocket with temp ID for correlation
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({
            type: 'message',
            temp_id: tempId,  // NEW: Send temp ID so server can ACK
            content: content,
        }));
    } else {
        // Queue message if not connected
        this.queuedMessages = this.queuedMessages || [];
        this.queuedMessages.push({ tempId, content });
        console.warn('[Message] WebSocket not connected, message queued');
    }

    // Clear input and reset typing
    input.value = '';
    input.style.height = 'auto';
    this.notifyTypingStatus(false);
    sendBtn.disabled = false;

    // Resize textarea
    this.autoResizeTextarea(input);
}
```

---

### Fix #8: Add Database Indexes

**File:** `message/models.py`

Update the `Message` model's `Meta` class:

```python
class Meta:
    ordering = ['created_at']
    indexes = [
        models.Index(fields=['conversation', 'created_at']),
        models.Index(fields=['sender', 'created_at']),
        models.Index(fields=['is_read']),
        # NEW INDEXES:
        models.Index(fields=['is_read', 'created_at']),
        models.Index(fields=['conversation', 'is_read']),
        models.Index(fields=['conversation', '-created_at']),  # For recent messages
        models.Index(fields=['sender', 'is_read']),
    ]
```

Then create and apply migration:
```bash
python manage.py makemigrations message
python manage.py migrate message
```

---

### Fix #9: Improve Typing Status Cleanup

**File:** `message/consumers.py`

Update `remove_typing_status()`:

```python
@database_sync_to_async
def remove_typing_status(self):
    """Remove typing status with proper error logging"""
    try:
        conversation = Conversation.objects.get(id=self.room_name)
        deleted_count, _ = Typing.objects.filter(
            conversation=conversation, 
            user=self.user
        ).delete()
        
        if deleted_count > 0:
            logger.debug(f"Typing status removed for {self.user.username} in conversation {self.room_name}")
    except Conversation.DoesNotExist:
        logger.warning(f"Conversation {self.room_name} not found when removing typing status")
    except Exception as e:
        logger.error(f"Error removing typing status: {e}", exc_info=True)
```

---

### Fix #10: Add Connection State Management to JavaScript

**File:** `static/js/messaging.js`

Update the `MessagingApp` constructor and connection handler:

```javascript
class MessagingApp {
    constructor() {
        this.conversationId = conversationId;
        this.otherUserId = otherUserId;
        this.currentUserId = currentUserId;
        this.socket = null;
        this.isConnected = false;  // NEW
        this.failedReadReceipts = [];  // NEW
        this.queuedMessages = [];  // NEW
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
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/${this.conversationId}/`;
        
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('[WebSocket] Connected to chat server');
            this.updateConnectionStatus(true);
            this.processQueuedMessages();  // NEW
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
            this.updateConnectionStatus(false);
        };
    }
    
    /**
     * Process queued messages when connection is restored
     */
    processQueuedMessages() {  // NEW
        if (this.queuedMessages && this.queuedMessages.length > 0) {
            console.log(`[Queued] Processing ${this.queuedMessages.length} queued messages`);
            const queued = [...this.queuedMessages];
            this.queuedMessages = [];
            
            queued.forEach(msg => {
                this.socket.send(JSON.stringify({
                    type: 'message',
                    temp_id: msg.tempId,
                    content: msg.content,
                }));
            });
        }
    }
}
```

---

## Recommended Order of Implementation

1. **Fix #1 & #2** (Security - Do First)
   - `mark_message_as_read()` conversation validation
   - `MarkAsReadAPIView` security check
   - **Time: 10 minutes**

2. **Fix #8** (Database Indexes)
   - Add indexes to Message model
   - Run migrations
   - **Time: 5 minutes**

3. **Fix #4 & #7** (Message ACK)
   - Update `handle_message()` in consumers
   - Update `sendMessage()` in JavaScript
   - Add `handleMessageAck()` handler
   - **Time: 30 minutes**

4. **Fix #3** (Bulk Read Receipts)
   - Update conversation_detail_view()
   - Add batch_messages_read handler
   - Add JavaScript handler
   - **Time: 25 minutes**

5. **Fix #5 & #6** (Read Receipt Retries)
   - Implement retry logic in JavaScript
   - Add failed receipt tracking
   - **Time: 20 minutes**

6. **Fix #9 & #10** (State Management)
   - Improve typing cleanup
   - Add connection state management
   - **Time: 15 minutes**

---

## Testing Checklist

After implementation:

- [ ] Send message and verify ACK is received
- [ ] Verify temporary ID is replaced with actual message ID
- [ ] Mark conversation as read and verify broadcast
- [ ] Check multiple messages are updated with read receipts
- [ ] Test connection drop and recovery with queued operations
- [ ] Verify read receipt retry works
- [ ] Check no security issues: try marking unrelated conversation messages as read
- [ ] Monitor logs for any errors
- [ ] Check database query performance with new indexes

---
