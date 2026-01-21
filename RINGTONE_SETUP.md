# Ringtone Setup Instructions

## 📱 Quick Setup

The ringtone feature is fully implemented. You just need to add an audio file!

### Step 1: Get a Ringtone Audio File

**Options:**
1. **Download Free** (Recommended):
   - https://freepd.com/ringtones
   - https://soundbible.com
   - https://www.notification-sounds.com
   
2. **Create Your Own**:
   - Use Audacity (free: https://www.audacityteam.org)
   - Generate tone: Generate > Tone... (frequency: 440 Hz, duration: 2-3 seconds)
   - Export as MP3

3. **Use Existing**:
   - iPhone ringtone
   - Android ringtone
   - Any MP3 file

### Step 2: Place File in Project

1. **Create directory** if needed:
   ```bash
   mkdir -p static/sounds
   ```

2. **Add ringtone file**:
   ```bash
   # Copy your file to:
   static/sounds/ringtone.mp3
   ```

### Step 3: Verify It Works

1. Start Django server:
   ```bash
   python manage.py runserver
   ```

2. Navigate to conversation:
   ```
   http://localhost:8000/message/inbox/
   ```

3. Test call:
   - Open browser console (F12)
   - Verify no errors loading ringtone
   - Initiate call and verify sound plays

### Step 4: (Optional) Adjust Volume

Edit [static/js/webrtc_calls.js](static/js/webrtc_calls.js) line 217:

```javascript
playRingtone() {
    if (this.ringtone) {
        this.ringtone.loop = true;
        this.ringtone.volume = 0.5;  // Change 0.5 (0-1 scale)
        this.ringtone.play()...
    }
}
```

- `0.1` = Very quiet
- `0.5` = Normal (default)
- `1.0` = Maximum volume

---

## 🎵 Recommended Ringtones

### Short & Professional (2-3 seconds):
- Classic phone ring
- Gentle chime
- Musical notification
- Bell tone

### File Format:
- **Best**: MP3 (most compatible)
- **Good**: WAV, OGG
- **Size**: 50-500 KB
- **Duration**: 2-5 seconds

---

## 📁 Project Structure After Setup

```
KonnectAble-Website/
├── static/
│   ├── sounds/
│   │   ├── README.md
│   │   └── ringtone.mp3  ← Add here
│   ├── css/
│   ├── images/
│   └── js/
└── ...
```

---

## ✅ Verification Checklist

After adding ringtone:

- [ ] File exists at `static/sounds/ringtone.mp3`
- [ ] File is readable (permissions: 644)
- [ ] File is under 1 MB
- [ ] File is valid MP3/WAV/OGG format
- [ ] Django serves static files correctly
- [ ] Browser console shows no 404 errors
- [ ] Audio plays when receiving call
- [ ] Audio stops when call ends or is declined
- [ ] Volume is appropriate (not too loud)

---

## 🧪 Quick Test Script

Open browser console (F12) and run:

```javascript
// Test ringtone playback
const audio = new Audio('/static/sounds/ringtone.mp3');
audio.volume = 0.5;
audio.play().then(() => {
    console.log('✅ Ringtone plays successfully');
    setTimeout(() => audio.pause(), 3000);
}).catch(err => {
    console.error('❌ Ringtone error:', err);
});
```

Expected output: ✅ Ringtone plays successfully

---

## 🔧 Troubleshooting

### Issue: Audio Not Playing
**Solution**: 
- Check file path: `/static/sounds/ringtone.mp3`
- Verify browser allows audio
- Check browser console for errors
- Try different browser (Chrome, Firefox, etc)

### Issue: 404 Error for ringtone.mp3
**Solution**:
- Verify file exists at `static/sounds/ringtone.mp3`
- Run: `python manage.py collectstatic`
- Restart Django server

### Issue: Volume Too Loud/Quiet
**Solution**:
- Adjust `ringtone.volume` in [static/js/webrtc_calls.js](static/js/webrtc_calls.js)
- Range: 0.0 to 1.0

---

## 🎯 Status

| Component | Status | Notes |
|-----------|--------|-------|
| Frontend Code | ✅ Complete | webrtc_calls.js ready |
| WebSocket Integration | ✅ Complete | call_ringing event ready |
| Modal UI | ✅ Complete | Animated & styled |
| Database | ✅ Complete | Migrations applied |
| Ringtone File | ⏳ **TODO** | Add MP3 file |

---

## 📝 Notes

- Ringtone auto-loops until stopped
- Volume adjustable 0-100% in code
- Loops only during ringing phase (first 30 seconds)
- Automatically stops when call answered
- Browser must allow audio (check permissions)

---

**Once ringtone file is added, calling feature is 100% complete!** 🎉

For questions, see [WEBRTC_CALLING_GUIDE.md](WEBRTC_CALLING_GUIDE.md)
