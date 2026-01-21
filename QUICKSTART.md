# 🚀 Quick Start Guide - Real-Time Messaging App

## 5-Minute Setup

### Step 1: Install Dependencies
```bash
cd KonnectAble-Website
pip install -r requirements.txt
```

### Step 2: Run Migrations
```bash
python manage.py migrate
```

### Step 3: Start Development Server
```bash
# With WebSocket support (recommended):
daphne -b 0.0.0.0 -p 8000 KonnectAble.asgi:application

# OR use Django dev server:
python manage.py runserver
```

### Step 4: Access the App
1. Open browser: `http://localhost:8000`
2. Log in with your account
3. Navigate to: `http://localhost:8000/message/inbox/`
4. Click "Start New Chat" to begin messaging!

---

## 🎯 Features Overview

### 💬 Send & Receive Messages
- Real-time messaging with WebSocket
- Messages appear instantly without refresh
- See typing status in real-time

### ✅ Read Receipts
- Single check (✓) = message sent
- Double check (✓✓) = message read
- Automatic tracking of read status

### 📞 Make Calls
- Click phone icon for audio call
- Click camera icon for video call
- See call duration during active calls

### 🔍 Search & Filter
- Search conversations by name
- Search users to start new chats
- Find people instantly

---

## 📱 Mobile & Responsive

✅ Works perfectly on:
- Desktop (Chrome, Firefox, Safari, Edge)
- Tablet (iPad, Android tablets)
- Mobile (iPhone, Android phones)

---

## 🎨 Theme Colors

The app uses your project's pink/rose theme:
- Primary: `#e85d75` (Pink/Rose)
- Accent: `#667eea` (Purple)
- Success: `#22c55e` (Green for online)

To customize, edit `static/css/messaging.css` at the top:
```css
:root {
    --primary-color: #your-color;
}
```

---

## 🔧 Common Tasks

### Change Primary Color
Edit `static/css/messaging.css` line 9-13:
```css
--primary-color: #e85d75;      /* Change this */
--primary-hover: #d44d65;       /* And this */
```

### Add More Styling
Add custom CSS to `static/css/messaging.css`

### Add New Features
Edit `static/js/messaging.js` or `message/views.py`

---

## 🐛 Troubleshooting

### "WebSocket connection failed"
- Make sure you're using `daphne` or ASGI server
- Check port 8000 is available
- Clear browser cache

### "Can't send messages"
- Ensure you're logged in
- Check browser console for errors
- Verify conversation exists

### "Messages not real-time"
- Check WebSocket connection (DevTools → Network)
- Restart development server
- Clear browser cache

---

## 📚 Documentation

For detailed documentation, see:
- **MESSAGING_GUIDE.md** - Complete feature guide
- **IMPLEMENTATION_SUMMARY.md** - Technical details
- Inline code comments in `message/` folder

---

## ✨ What's Included

✅ Real-time messaging  
✅ Read receipts  
✅ Typing indicators  
✅ Audio/video call signaling  
✅ Message history  
✅ User search  
✅ Responsive design  
✅ Mobile support  
✅ Security & authentication  
✅ Performance optimized  

---

## 🎓 Next Steps

1. **Test messaging** - Send messages between accounts
2. **Try calls** - Test call initiation (WebRTC needed for actual media)
3. **Mobile test** - Open on phone/tablet
4. **Customize** - Change colors, add features
5. **Deploy** - Set up production server with Daphne/Gunicorn

---

## 📞 Need Help?

Check these files:
- `MESSAGING_GUIDE.md` - All features explained
- `message/views.py` - API endpoints
- `message/consumers.py` - WebSocket logic
- `static/js/messaging.js` - Frontend logic
- `static/css/messaging.css` - Styling

---

**Ready to chat!** 🎉

Start the server and navigate to `/message/inbox/` to begin.
