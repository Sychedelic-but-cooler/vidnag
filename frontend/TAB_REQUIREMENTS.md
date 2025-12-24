# Vidnag Tab Content Requirements

## 📥 Tab 1: Video Downloads

### Layout: 30/70 Split

```
┌──────────────────┬─────────────────────────────────────────────────┐
│ LEFT (30%)       │ RIGHT (70%)                                     │
│                  │                                                 │
│ ┌──────────────┐ │ ┌─────────────────────────────────────────────┐ │
│ │ URL Input    │ │ │ Past Downloads History                      │ │
│ │ (Multi-line) │ │ │                                             │ │
│ │              │ │ │ ┌──────────────────────────────────────────┐│ │
│ │              │ │ │ │ Download #1                              ││ │
│ │              │ │ │ │ Title: Video Name                        ││ │
│ │              │ │ │ │ Source: youtube.com                      ││ │
│ │ [Download]   │ │ │ │ Size: 150MB | Duration: 10:25            ││ │
│ └──────────────┘ │ │ │ Date: 2024-12-24 12:30                   ││ │
│                  │ │ │ Status: ✓ Completed                       ││ │
│ ┌──────────────┐ │ │ └──────────────────────────────────────────┘│ │
│ │ Active       │ │ │                                             │ │
│ │ Downloads    │ │ │ ┌──────────────────────────────────────────┐│ │
│ │              │ │ │ │ Download #2                              ││ │
│ │ ━━━━━━ 45%   │ │ │ │ ...                                      ││ │
│ │ Video 1      │ │ │ └──────────────────────────────────────────┘│ │
│ └──────────────┘ │ │                                             │ │
│                  │ │ [Pagination or infinite scroll]              │ │
│ ┌──────────────┐ │ └─────────────────────────────────────────────┘ │
│ │ Queue (5)    │ │                                                 │
│ │              │ │                                                 │
│ │ • Video 2    │ │                                                 │
│ │ • Video 3    │ │                                                 │
│ │ • Video 4    │ │                                                 │
│ └──────────────┘ │                                                 │
└──────────────────┴─────────────────────────────────────────────────┘
```

### Left Panel (30%)

#### 1. URL Input Area
- **Multi-line textarea**
- Accepts multiple URLs (one per line)
- Delimiter: Newline (`\n`)
- Placeholder: "Enter video URLs (one per line)..."
- Glass-styled card
- **[Download]** button below textarea

#### 2. Active Downloads Section
- Shows currently downloading videos
- Display for each active download:
  - Video title/filename
  - Progress bar with percentage
  - Download speed (MB/s)
  - ETA (estimated time)
  - Cancel button
- If empty: "No active downloads"

#### 3. Queued Downloads Section
- Header: "Queue (5)" - shows count
- Compact list of queued items:
  - Video title or URL
  - Small icon/indicator
- If empty: "Queue is empty"
- Maybe: Drag to reorder?

### Right Panel (70%)

#### Past Downloads History
- **List/cards of completed downloads**
- Each download shows:
  - ✓ Status indicator (completed, failed, cancelled)
  - Video title
  - Thumbnail (if available)
  - Source (youtube.com, vimeo.com, etc.)
  - File size (e.g., "150 MB")
  - Duration (e.g., "10:25")
  - Download date/time
  - Actions:
    - View in File Browser
    - Re-download
    - Delete
- **Pagination or infinite scroll**
- **Filter/search options:**
  - By date
  - By source
  - By status

---

## 🛠️ Tab 2: Media Tools (Video & Audio)

### Layout: 30/70 Split

```
┌──────────────────┬─────────────────────────────────────────────────┐
│ LEFT (30%)       │ RIGHT (70%)                                     │
│                  │                                                 │
│ ┌──────────────┐ │ ┌─────────────────────────────────────────────┐ │
│ │ Tool Select  │ │ │ Completed Conversions                       │ │
│ │ [Dropdown ▼] │ │ │                                             │ │
│ └──────────────┘ │ │ ┌──────────────────────────────────────────┐│ │
│                  │ │ │ ✓ video.mp4 → video.webm                 ││ │
│ ┌──────────────┐ │ │ │   Size: 150MB → 120MB                    ││ │
│ │ Dynamic      │ │ │ │   Completed: 2 mins ago                  ││ │
│ │ Tool Options │ │ │ └──────────────────────────────────────────┘│ │
│ │              │ │ │                                             │ │
│ │ (Changes     │ │ │ ┌──────────────────────────────────────────┐│ │
│ │  based on    │ │ │ │ ✓ audio.mp3 → audio.flac                ││ │
│ │  selected    │ │ │ │   Size: 5MB → 12MB                       ││ │
│ │  tool)       │ │ │ └──────────────────────────────────────────┘│ │
│ │              │ │ └─────────────────────────────────────────────┘ │
│ │              │ │                                                 │
│ │ [Process]    │ │ ┌─────────────────────────────────────────────┐ │
│ └──────────────┘ │ │ Active & Queued                             │ │
│                  │ │                                              │ │
│                  │ │ 🔄 video2.avi → mp4  ━━━━━ 65%              │ │
│                  │ │                                              │ │
│                  │ │ ⏳ Queue (2):                                │ │
│                  │ │  • audio.wav → mp3                          │ │
│                  │ │  • video3.mkv → webm                        │ │
│                  │ └─────────────────────────────────────────────┘ │
└──────────────────┴─────────────────────────────────────────────────┘
```

### Left Panel (30%)

#### 1. Tool Selection (Top)
- **Dropdown selector** for tool type:
  - Video Converter
  - Audio Converter
  - Video Trimmer
  - Audio Extractor
  - Compressor
  - Resolution Changer
  - (More tools can be added easily)

#### 2. Dynamic Tool Options (Below)
- **Content changes based on selected tool**
- Examples:

  **Video Converter:**
  - Source file selector
  - Output format dropdown (MP4, WebM, AVI, MKV, etc.)
  - Quality/bitrate settings
  - [Process] button

  **Audio Converter:**
  - Source file selector
  - Output format dropdown (MP3, FLAC, WAV, AAC, OGG, etc.)
  - Quality/bitrate settings
  - [Process] button

  **Video Trimmer:**
  - Source file selector
  - Start time input
  - End time input
  - Preview thumbnails
  - [Trim] button

  **Audio Extractor:**
  - Source video file selector
  - Output audio format
  - [Extract] button

  **Compressor:**
  - Source file selector
  - Target size or quality slider
  - [Compress] button

### Right Panel (70%)

#### 1. Completed Conversions (Top)
- **List of successfully completed operations**
- Each item shows:
  - ✓ Status icon
  - Input file → Output file
  - Original size → New size
  - Completion time
  - Actions:
    - Download
    - View in File Browser
    - Delete
- Pagination or infinite scroll

#### 2. Active & Queued (Bottom)
- **Active conversions:**
  - 🔄 Processing indicator
  - Input → Output format
  - Progress bar with percentage
  - Cancel button
  - ETA

- **Queue:**
  - Header: "Queue (2)" - shows count
  - List of pending operations
  - Input → Output format
  - Remove from queue button

---

## 📁 Tab 3: File Browser

### Layout: Full Width

```
┌─────────────────────────────────────────────────────────────────────┐
│ Upload Section                                                       │
│                                                                      │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │  📤 Drag & Drop files here or [Choose Files]                     ││
│ │                                                                   ││
│ │  Accepted formats: MP4, WebM, AVI, MKV, MOV, MP3, WAV, FLAC...  ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ File Browser                                                         │
│                                                                      │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ 📁 Name                    Size      Type     Modified           ││
│ ├──────────────────────────────────────────────────────────────────┤│
│ │ 🎬 vacation_2024.mp4       150 MB    Video    Dec 24, 12:30 PM  ││
│ │ 🎵 song.mp3                5 MB      Audio    Dec 24, 11:15 AM  ││
│ │ 🎬 tutorial.webm           85 MB     Video    Dec 23, 09:45 PM  ││
│ │ 🎵 podcast.wav             120 MB    Audio    Dec 23, 02:30 PM  ││
│ │ 🎬 movie.mkv               2.5 GB    Video    Dec 22, 08:00 AM  ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│ [Sort by: Name ▼] [Filter: All ▼] [Search...]                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Top Section: Upload

#### Upload Area
- **Large drag-and-drop zone** (glass-styled)
- Text: "📤 Drag & Drop files here or [Choose Files]"
- Shows accepted file formats
- On drag-over: Highlight/glow effect
- On drop: Upload progress indicator
- **[Choose Files]** button triggers file picker

**Note:** Upload functionality will be skeleton/placeholder for now
- No actual file processing yet
- Awaiting upload sanitization and configuration

### Bottom Section: File Browser

#### File List (Table View)
- **Columns:**
  - 📁 **Name** - Filename with icon (🎬 video, 🎵 audio)
  - **Size** - File size (MB/GB)
  - **Type** - Media type (Video/Audio)
  - **Modified** - Last modified date/time
  - **Actions** - (Download, Delete, Share, etc.)

- **Features:**
  - Sortable columns (click header to sort)
  - Row hover effect (glass glow)
  - Selection checkboxes for bulk actions
  - Click row to preview/play file

- **Excludes thumbnails** from file list

#### Controls (Above table)
- **Sort by:** Dropdown (Name, Size, Date, Type)
- **Filter:** Dropdown (All, Video only, Audio only)
- **Search:** Text input for filename search
- **View toggle:** List view / Grid view (future)

**Note:** Functionality is placeholder-only for now

---

## 📊 Tab 4: Logs

**Requirements needed:**
- What types of logs?
  - User activity?
  - Download history?
  - System events?
  - Admin actions?
- Filter options?
- Export functionality?
- Real-time updates?

---

## Next Steps

1. ✅ Video Downloads tab - Fully specified
2. ⏳ Video Tools tab - Awaiting requirements
3. ⏳ File Browser tab - Awaiting requirements
4. ⏳ Logs tab - Awaiting requirements

**Please provide details for the remaining 3 tabs!**
