# TODO: Implement Real-Time Read Receipts (Ticks) for Message App

## Tasks
- [x] Modify message/consumers.py to broadcast read receipts when messages are marked as read
- [x] Update message/templates/message/chat.html to listen for read receipt messages and update ticks in UI
- [x] Test WebSocket connection and real-time updates
- [x] Advise on running server with Daphne for WebSocket support

## Notes
- WebSocket connection error: 'ws://127.0.0.1:8000/ws/chat/1/' failed - ensure server is running with WebSocket support (use Daphne)
- Ticks represent read receipts: single tick for sent, double for read
- For development: Use `python manage.py runserver` (supports Channels)
- For production: Use `daphne KonnectAble.asgi:application --port 8001 `
