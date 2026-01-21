# Testing Guide - Real-Time Messaging App

## Pre-Testing Checklist

- [ ] Python environment activated
- [ ] Requirements installed: `pip install -r requirements.txt`
- [ ] Database migrated: `python manage.py migrate`
- [ ] At least 2 test user accounts created
- [ ] Daphne installed: `pip install daphne`

---

## Test Scenario 1: Basic Messaging

### Setup
1. Open two browser windows/tabs
2. Log in with User A in first window
3. Log in with User B in second window

### Steps
1. **User A**: Navigate to `/message/inbox/`
2. **User A**: Click "Start New Chat"
3. **User A**: Search for User B and click to start conversation
4. **User A**: Type a message: "Hello User B!"
5. **User A**: Click send button or press Enter

### Expected Results
- ✅ Message appears immediately in User A's chat
- ✅ Message has single check (✓) - sent
- ✅ User B's inbox shows new unread message count
- ✅ User B clicks conversation, message appears
- ✅ User A's check changes to double check (✓✓) - read

---

## Test Scenario 2: Typing Indicator

### Setup
- Both users in same conversation

### Steps
1. **User A**: Start typing a message (but don't send yet)
2. **User B**: Observe typing indicator

### Expected Results
- ✅ Animated dots appear in User B's chat
- ✅ Text shows "User A is typing..."
- ✅ Indicator disappears after User A stops typing for 3 seconds
- ✅ OR indicator disappears when message is sent

---

## Test Scenario 3: Message Read Receipts

### Setup
- Both users in same conversation
- User A sends a message

### Steps
1. **User A**: Send message: "Test read receipt"
2. **User A**: Observe check icon (should be single ✓)
3. **User B**: Read the message (it auto-marks as read)
4. **User A**: Observe check icon changes

### Expected Results
- ✅ Single check (✓) appears when sent
- ✅ Double check (✓✓) appears when read
- ✅ Both checks are blue/colored
- ✅ Timestamp is correct

---

## Test Scenario 4: Conversation List

### Setup
- Both users with multiple conversations

### Steps
1. **User A**: Go to inbox
2. **User A**: See list of conversations sorted by recent
3. **User A**: Send message in one conversation
4. **User A**: Check that conversation moves to top
5. **User A**: Use search to filter conversations

### Expected Results
- ✅ Conversations sorted by updated_at (most recent first)
- ✅ Last message preview shows in each conversation
- ✅ Unread count badge shows
- ✅ Search filters conversations by name
- ✅ Time shows in HH:MM format

---

## Test Scenario 5: Call Initiation

### Setup
- Both users in same conversation

### Steps
1. **User A**: Click phone icon (audio call)
2. **User B**: Observe incoming call notification

### Expected Results
- ✅ Call modal appears on User A with "Calling..." status
- ✅ User A sees decline button
- ✅ User B sees incoming call notification
- ✅ User B sees answer/decline buttons

---

## Test Scenario 6: Mobile Responsiveness

### Setup
- Desktop browser with dev tools

### Steps
1. Open `/message/conversation/<id>/`
2. Open DevTools (F12)
3. Toggle device toolbar
4. Test at different screen sizes:
   - Mobile: 375px
   - Tablet: 768px
   - Desktop: 1024px+

### Expected Results
- ✅ Mobile (375px):
  - Full-width chat
  - Sidebar hidden with toggle button
  - Message input fills width
  - Buttons touch-friendly
  
- ✅ Tablet (768px):
  - Split layout works
  - Responsive grid
  - Touch gestures work
  
- ✅ Desktop (1024px+):
  - 360px sidebar + chat area
  - All features visible
  - Desktop-optimized

---

## Test Scenario 7: Error Handling

### Steps
1. **Disconnect WebSocket**: Close browser DevTools connection
2. Try sending message
3. **Reload page**: Refresh during active conversation
4. **Network offline**: Toggle airplane mode
5. **Invalid input**: Try sending empty message

### Expected Results
- ✅ Error messages display clearly
- ✅ App attempts to reconnect
- ✅ No data loss on reload
- ✅ Graceful handling of network errors
- ✅ Empty message not sent

---

## Test Scenario 8: Emoji & Special Characters

### Setup
- Both users in conversation

### Steps
1. **User A**: Send message with emoji: "Hello 👋 😊"
2. **User A**: Send message with special chars: "<script>alert('test')</script>"
3. **User B**: View messages

### Expected Results
- ✅ Emojis display correctly
- ✅ Special characters are escaped/safe
- ✅ No code injection possible
- ✅ HTML entities handled properly

---

## Test Scenario 9: Conversation Isolation

### Setup
- User A has conversations with User B and User C

### Steps
1. **User A**: Open conversation with User B
2. **User A**: Send message to User B
3. **User A**: Open conversation with User C
4. **User A**: Check messages (should only see messages with User C)

### Expected Results
- ✅ Messages isolated per conversation
- ✅ Can't see User B's messages in User C's chat
- ✅ Each conversation is separate
- ✅ Permissions verified

---

## Test Scenario 10: Multiple Conversations

### Setup
- User A with 5+ conversations

### Steps
1. **User A**: Go to inbox
2. **User A**: Scroll through conversation list
3. **User A**: Click different conversations
4. **User A**: Send messages in different conversations
5. **User A**: Verify message isolation

### Expected Results
- ✅ List scrolls smoothly
- ✅ Clicking conversation shows correct messages
- ✅ Messages don't mix between conversations
- ✅ Unread counts update correctly
- ✅ No performance issues

---

## Performance Tests

### Load Test
```bash
# Send many messages rapidly
# Monitor browser DevTools → Performance
```

Expected Results:
- ✅ Messages send within 100ms
- ✅ No memory leaks
- ✅ CPU usage reasonable
- ✅ Smooth 60fps animations

### Pagination Test
```bash
# Load conversation with 100+ messages
# Scroll through history
```

Expected Results:
- ✅ Initial load fast (first 50 messages)
- ✅ Scrolling to older messages loads more
- ✅ No freezing or lag
- ✅ Smooth scroll experience

---

## Browser Compatibility Tests

Test on each browser:
- [ ] Chrome/Chromium (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Chrome
- [ ] Mobile Safari

Expected Results:
- ✅ All features work
- ✅ Styling looks good
- ✅ WebSocket connects
- ✅ No console errors

---

## Admin Panel Tests

### Access Admin
1. Go to `/admin/`
2. Log in as superuser

### Tests
1. **Conversation Admin**:
   - ✅ List all conversations
   - ✅ View conversation details
   - ✅ Search by username
   - ✅ Filter by date

2. **Message Admin**:
   - ✅ List all messages
   - ✅ Filter by type/read status
   - ✅ Search by content
   - ✅ View timestamps

3. **Call Admin**:
   - ✅ List all calls
   - ✅ Filter by type/status
   - ✅ View duration
   - ✅ Check participants

4. **Typing Admin**:
   - ✅ View typing statuses
   - ✅ Identify which users were typing

---

## Security Tests

- [ ] Try accessing other user's conversations (should fail)
- [ ] Try marking someone else's message as read (should fail)
- [ ] Try calling someone without conversation (should fail)
- [ ] Try CSRF attack without token (should fail)
- [ ] Try SQL injection in search (should escape)
- [ ] Try XSS in message content (should escape)

Expected Results:
- ✅ All permission checks pass
- ✅ All security measures work
- ✅ No unauthorized access

---

## Test Results Template

```markdown
# Test Run: [Date]

## Browser: [Chrome/Firefox/Safari/etc]
## Device: [Desktop/Tablet/Mobile]

### Basic Messaging
- [ ] Send message
- [ ] Receive message
- [ ] Read receipt
- [ ] Typing indicator

### Calls
- [ ] Initiate call
- [ ] Receive call notification
- [ ] Accept call
- [ ] Decline call

### Search
- [ ] Search users
- [ ] Search conversations

### Responsive
- [ ] Mobile layout
- [ ] Touch interactions
- [ ] Sidebar toggle

### Performance
- [ ] Message send time
- [ ] Memory usage
- [ ] CPU usage
- [ ] Animation smoothness

### Issues Found
- [ ] Issue 1
- [ ] Issue 2

## Overall Status: ✅ PASS / ❌ FAIL
```

---

## Known Test Limitations

⚠️ **Video/Audio Calls**
- Signaling works (WebRTC infrastructure ready)
- Actual media streaming requires additional setup (STUN/TURN servers)
- Test call initiation only

⚠️ **File Uploads**
- Models support it
- API endpoint ready
- File handling tests deferred

---

## Reporting Issues

When reporting a bug, include:
1. Browser and version
2. Device (desktop/mobile)
3. Steps to reproduce
4. Expected vs actual behavior
5. Browser console errors (if any)
6. Network tab WebSocket status

---

**Happy Testing!** 🧪
