<div align="center">

# ⚡ SONICBULK

### The Ultimate Bulk Music Downloader for Desktop & Terminal

**Turn any PDF, Word document, CSV, or messy text list into a pristine, fully-tagged offline music library in seconds.**

[![GitHub Stars](https://img.shields.io/github/stars/aradhyags7/SONICBULK?style=for-the-badge&logo=github&color=F59E0B)](https://github.com/aradhyags7/SONICBULK/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-3B82F6.svg?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-10B981.svg?style=for-the-badge)](https://github.com/aradhyags7/SONICBULK)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-8B5CF6.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

<br/>

<p align="center">
  <b>Stop wasting hours manually downloading songs from YouTube, battling ad-filled converter sites, or fixing broken tags.</b><br/>
  Just drag & drop your playlist file &mdash; SONICBULK does all the heavy lifting in the background.
</p>

[**🚀 Quick Start**](#-quick-start-in-60-seconds) &bull;
[**✨ Killer Features**](#-why-sonicbulk) &bull;
[**🥊 Comparison**](#-sonicbulk-vs-the-alternatives) &bull;
[**💻 Desktop App**](#-the-desktop-experience) &bull;
[**⌨️ CLI Guide**](#-power-user-cli) &bull;
[**⭐ Star on GitHub**](https://github.com/aradhyags7/SONICBULK)

</div>

---

## 😫 The Problem with Downloading Music Today

* ❌ **Ad-filled sketchy websites**: Slow, spammy, full of popups and malware risks.
* ❌ **Wrong versions**: You want the original studio song, but get a shaky smartphone live concert recording, a terrible cover, or a sped-up "Nightcore" version.
* ❌ **Messy tracklists**: You have a setlist in a PDF or a song list texted to you on WhatsApp, but manually searching 50+ songs takes all evening.
* ❌ **Missing tags & covers**: Downloaded files named `videoplayback (1).mp3` with no artist, album, or metadata.
* ❌ **Throttled snail speeds**: Downloads capped at 40 KB/s that take hours to finish.

---

## ✨ Why SONICBULK?

SONICBULK was engineered from the ground up to be the **fastest, cleanest, and smartest music downloader on the planet**.

```
   Drop File (PDF / DOCX / TXT / CSV)
                   │
                   ▼
       ⚡ Smart Auto-Cleaner & Matcher
                   │
                   ▼
     🚀 High-Speed Bounded Download Engine
                   │
                   ▼
   🎵 Pristine, Tagged Audio Library (Ready for iPhone, Android, Spotify Local Files)
```

### 🔥 Highlights You'll Love:

* 📄 **Feed It Any Document**: Drop a concert setlist PDF, a wedding playlist Word doc (`.docx`), a Spotify CSV export, or paste raw text. SONICBULK auto-cleans timestamps, track numbers, bracket noise (`[Official Video]`, `[Lyrics]`), and messy formatting.
* 🎯 **Guaranteed Original Studio Tracks**: Our intelligent matching engine cross-references artist and title metrics, checks official "Topic" channels, and penalizes covers, karaoke, 8D audio, and live rips. You always get the real song.
* ⚡ **Unthrottled Line-Speed Downloads**: Bypasses YouTube/CDN playback throttling using high-speed bounded chunk streaming. Songs download in **1 to 2 seconds flat**, not minutes.
* 🏷️ **Studio-Grade Auto-Tagging**: Injects ID3 / M4A / FLAC metadata (Title, Artist, Album, Cover Art) directly into the files. Open them in Apple Music, Spotify Local Files, VLC, or your car stereo and everything looks beautiful.
* 🛡️ **Zero Corrupted Files**: Downloads stream to temporary `.part` files with byte-level resume and physical kernel disk flushing before an atomic rename. Even if your Wi-Fi drops, your library stays clean.
* 🌙 **Sleek Modern Dark UI**: A gorgeous, fluid PySide6 desktop interface built with dark mode aesthetics, real-time speedometers, and system tray notifications.
* 🤖 **Polite by Default, Fast When You Want**: Downloads 1-by-1 sequentially out of the box to keep your network smooth and prevent rate-limiting, or toggle up to 16 parallel downloads in Settings!

---

## 🥊 SONICBULK vs. The Alternatives

| Feature | Sketchy Web Downloaders | Spotify Rippers | Standard yt-dlp CLI | ⚡ SONICBULK |
| :--- | :---: | :---: | :---: | :---: |
| **Price** | Free (with malware/ads) | Often Paid / Banned | Free | **100% Free & Open Source** |
| **Drop PDF & Word Docs** | ❌ No | ❌ No | ❌ No | **✅ Yes (PDF, DOCX, CSV, TXT)** |
| **Anti-Cover Matcher** | ❌ None | ⚠️ Hit or Miss | ❌ Grabs first result | **✅ Smart Multi-Factor Heuristics** |
| **Download Speeds** | 🐌 Throttled | 🐢 Slow | ⚡ Fast (if tuned) | **🚀 Blazing (1-2s per track)** |
| **Automatic ID3 Tagging** | ❌ Rarely | ⚠️ Basic | ⚠️ Requires manual flags | **✅ Built-in & Automatic** |
| **Beautiful Desktop GUI** | ❌ No | ⚠️ Clunky | ❌ CLI Only | **✅ Modern Dark Theme (Qt6)** |
| **Batch Resumption** | ❌ Restarts whole file | ❌ Flaky | ⚠️ Manual | **✅ Automatic Byte-Exact Resume** |
| **Privacy & Security** | 🚨 Tracking & Ads | 🚨 Requires Account | ✅ Local | **🛡️ 100% Local & Private** |

---

## 🚀 Quick Start in 60 Seconds

### Windows (One-Click Launch)

1. **Clone or Download** this repository:
   ```powershell
   git clone https://github.com/aradhyags7/SONICBULK.git
   cd SONICBULK
   ```
2. **Install requirements**:
   ```powershell
   python -m pip install -r requirements.txt
   ```
3. **Double-click `run.bat`** (or run `.\run.bat` in PowerShell). That's it!

### macOS & Linux

```bash
git clone https://github.com/aradhyags7/SONICBULK.git
cd SONICBULK
python3 -m pip install -r requirements.txt
python3 -m src.app
```

---

## 🖥️ The Desktop Experience

SONICBULK is built for flow and ease of use:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 🎵 SONICBULK                                               ⚙️ Settings │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   📥 STEP 1: IMPORT                                                    │
│   Drop your PDF, DOCX, CSV, TXT here or paste your tracklist           │
│   [ Choose Output Folder: Downloads/MusicDownloader ]                  │
│                                                                        │
│   📝 STEP 2: REVIEW                                                    │
│   Auto-cleaned tracklist with live duplicate indicators                │
│   [ ▶️ Start Download ]                                                │
│                                                                        │
│   ⚡ STEP 3: SIT BACK & RELAX                                          │
│   Watch real-time speed gauges (5+ MB/s) & individual progress bars     │
│   Minimizes cleanly to your system tray with completion alerts         │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

1. **📥 Import in Seconds**: Drag and drop any document or paste raw text. The parser handles two-column PDFs, tables, numbered playlists, and Romanized songs with ease.
2. **📝 Quick Review Screen**: Clean, editable table lets you tweak track names, add/remove songs, or see detected duplicates before starting.
3. **⏳ Live Speed & Progress Dashboard**: Real-time download speeds, aggregate progress bars, and accurate ETAs.
4. **🏆 Audit & Export**: Full post-download report. Did a track have a weird spelling? Easily swap candidates with one click or export a neat CSV report.
5. **🔔 Background Freedom**: Minimize SONICBULK to your system tray. It automatically prevents your computer from sleeping while downloading and pops a native notification when your batch is done!

---

## ⌨️ Power User CLI

Prefer the terminal or want to automate downloads in your scripts? SONICBULK includes a blistering headless CLI that shares the exact same engine.

```bash
# Download an entire PDF playlist into your music folder
python -m src.app run playlist.pdf --out ./music

# Download with 4 concurrent workers and auto-convert to MP3
python -m src.app run party_songs.docx --out ./music --workers 4 --format mp3 --report summary.csv

# Inspect and clean a messy playlist without downloading
python -m src.app inspect messy_list.txt

# Resume or retry failed tracks from a previous batch
python -m src.app retry <batch_id> --out ./music
```

### CLI Cheat Sheet

| Option | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `--out` | `-o` | Target music destination folder | `./music` |
| `--workers` | `-w` | Number of simultaneous download workers | `1` (Sequential) |
| `--format` | `-f` | Desired audio format (`native`, `mp3`, `m4a`, `flac`) | `native` (Highest fidelity) |
| `--layout` | `-l` | Library structure (`flat` or `artist_album`) | `flat` |
| `--report` | | Export comprehensive run results to CSV | None |
| `--dry-run`| | Parse and validate tracklist without downloading | `false` |

---

## 🧹 Smart Auto-Cleaning in Action

No need to clean up messy tracklists before importing. SONICBULK's normalization engine strips out all the junk automatically:

| What You Paste / Import | What SONICBULK Searches & Saves | Magic Applied |
| :--- | :--- | :--- |
| `01. Jhoome Jo Pathaan (Official 4K Video) 03:28` | **Jhoome Jo Pathaan** | Stripped track numbering, video quality tags, & duration |
| `Coldplay - Yellow (Live in São Paulo) 128 BPM` | **Coldplay &mdash; Yellow** | Removed live concert flags and audio metadata |
| `Agar Tum Saath Ho - Bollywood Hits - Hindi - Agar Tum Saath Ho` | **Agar Tum Saath Ho** | Auto-detected and stripped repeated category sandwich |
| `Kesariya by Arijit Singh` | **Arijit Singh &mdash; Kesariya** | Natural language artist/title decomposition |
| `12) Blinding Lights [Lyrics] HQ` | **Blinding Lights** | Cleaned bracket noise & parenthesis garbage |

---

## 💡 Frequently Asked Questions

#### 💸 Is SONICBULK completely free?
**Yes!** 100% free and open-source under the permissive MIT license. No subscriptions, no ads, no paywalls, and no hidden telemetry.

#### 🎵 What audio quality do I get?
By default, SONICBULK keeps the **highest native bitrate** audio stream (typically 256 kbps AAC or 160 kbps Opus) with **zero transcoding loss**. If you prefer universal compatibility, you can optionally enable high-quality conversion to MP3 or FLAC in Settings.

#### 🌍 Does it work with international & regional songs?
**Yes!** SONICBULK has dedicated heuristic support for Romanized titles, Bollywood, K-Pop, Latin, Anime OSTs, and non-English music, matching against major global label channels (`T-Series`, `Sony Music`, `Universal`, `Warner`, etc.).

#### 🔒 Is my data private?
Everything runs locally on your machine. Your files, tracklists, and downloads never pass through any third-party telemetry servers.

---

## 🤝 Contributing & Community

Contributions make the open-source community an incredible place to learn, inspire, and create. Any contributions you make are **greatly appreciated**!

1. **Fork the Project**
2. **Create your Feature Branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit your Changes** (`git commit -m 'Add some AmazingFeature'`)
4. **Push to the Branch** (`git push origin feature/AmazingFeature`)
5. **Open a Pull Request**

---

## ⭐ Show Your Support

If SONICBULK saved you hours of time or helped you build your dream music collection, **please star this repository**! It helps more music lovers discover the project.

<div align="center">

[![Star on GitHub](https://img.shields.io/badge/⭐_Star_on_GitHub-SONICBULK-yellow?style=for-the-badge&logo=github)](https://github.com/aradhyags7/SONICBULK)

Distributed under the **MIT License**. Created with ❤️ by music lovers, for music lovers.

</div>
