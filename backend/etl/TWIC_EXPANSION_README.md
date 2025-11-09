# TWIC Complete Archive Expansion

This system downloads all available chess games from **The Week in Chess (TWIC)** archive and integrates them into your existing Weaviate chess database, creating the most comprehensive chess games database possible.

## 🎯 **What This Does**

- **Discovers** all available TWIC archives automatically (from TWIC #1 to latest)
- **Downloads** PGN files in parallel for maximum speed
- **Processes** and extracts games from ZIP/GZIP archives
- **Removes duplicates** using intelligent game signatures
- **Sorts chronologically** to maintain proper game ordering
- **Integrates** seamlessly with your existing Weaviate chess database
- **Resumes** interrupted downloads automatically

## 📊 **Expected Results**

- **~6+ million chess games** from professional tournaments
- **Historical coverage** from 1990s to present
- **Master-level games** from FIDE-rated tournaments worldwide
- **Rich metadata** including player ratings, titles, opening classifications

---

## 🚀 **Quick Start**

### **Complete Expansion (Recommended)**
```bash
cd mvp1/backend/etl
python run_twic_expansion.py
```

This will:
1. Download all TWIC archives
2. Process and combine them chronologically  
3. Load everything into your Weaviate database

**Estimated time:** 2-6 hours depending on internet speed

---

## 📋 **Detailed Usage Options**

### **Download Only (No Weaviate Loading)**
```bash
python run_twic_expansion.py --download-only
```
Perfect for:
- Testing the download process
- Creating backups before loading
- Running on a different machine than your Weaviate instance

### **Load Existing Combined File**
```bash
python run_twic_expansion.py --load-only
```
Use when you already have a combined PGN file and want to load it into Weaviate.

### **Load Specific Combined File**
```bash
python run_twic_expansion.py --load-only --combined-file /path/to/twic_complete_20241201.pgn
```

### **Download Specific Range**
```bash
# Download TWIC 1000-1500 only
python run_twic_expansion.py --start-twic 1000 --end-twic 1500
```

### **Adjust Parallel Downloads**
```bash
# Use 8 parallel downloads (faster but more bandwidth intensive)
python run_twic_expansion.py --max-workers 8

# Use 2 parallel downloads (slower but gentler on the server)
python run_twic_expansion.py --max-workers 2
```

---

## 📁 **File Structure**

The system creates organized directories under your `PGN_DATA_DIR`:

```
mvp1/backend/data/twic_pgn/
├── twic_downloads/          # Raw downloaded archives
│   ├── twic0001g.zip
│   ├── twic0002g.zip
│   └── ...
├── twic_processed/          # Extracted PGN files
│   ├── twic0001.pgn
│   ├── twic0002.pgn
│   └── ...
├── twic_combined/           # Final combined files
│   └── twic_complete_20241201.pgn
└── twic_download_state.json # Progress tracking
```

---

## 🔄 **Resume Capability**

The system automatically saves progress and can resume interrupted downloads:

```bash
# If download was interrupted, just run again
python run_twic_expansion.py
```

The system will:
- ✅ Skip already downloaded archives
- ✅ Resume from where it left off
- ✅ Preserve existing processed files
- ✅ Continue building the combined file

---

## 📈 **Progress Monitoring**

### **Real-time Progress**
The script provides detailed progress information:
```
🔍 Discovering TWIC archives...
✅ Discovered 1547 archives
📥 Downloading archives...
INFO - Downloading TWIC 1: twic0001g.zip
INFO - Downloading TWIC 2: twic0002g.zip
...
✅ Downloaded 1547 archives
⚙️ Processing and combining archives...
INFO - TWIC 1: 234 games, date range 1990-1991
...
✅ Created combined file: twic_complete_20241201.pgn
```

### **Check Progress**
View the state file for detailed progress:
```bash
cat mvp1/backend/data/twic_pgn/twic_download_state.json
```

### **Log Files**
Detailed logs are saved to:
```bash
tail -f twic_downloader.log
```

---

## 🛠 **Troubleshooting**

### **Download Issues**

**Problem:** Some archives fail to download
```
ERROR - Failed to download TWIC 1234 after 3 attempts
```
**Solution:** The script automatically retries failed downloads. Very old TWIC files might not be available. This is normal.

**Problem:** Slow download speeds
```bash
# Reduce parallel workers to avoid overwhelming the server
python run_twic_expansion.py --max-workers 2
```

### **Processing Issues**

**Problem:** Archive extraction fails
```
ERROR - Failed to extract twic1234g.zip: Bad zipfile
```
**Solution:** The script will skip corrupted archives and continue. Check the log for details.

**Problem:** Out of disk space
**Solution:** Each TWIC file is ~50-500KB compressed, ~1-5MB uncompressed. Ensure you have at least 10GB free space.

### **Weaviate Issues**

**Problem:** Cannot connect to Weaviate
```
ERROR - Weaviate client connected but not ready/live
```
**Solution:** 
1. Ensure Weaviate is running: `docker ps`
2. Check connection in config.py
3. Verify OpenAI API key if using text2vec-openai

**Problem:** Duplicate games in database
**Solution:** The script has built-in duplicate detection. If you need to clean up, delete the collection and reload:
```python
# In Python console
import weaviate
client = weaviate.connect_to_local()
client.collections.delete("ChessGame")
```

### **Memory Issues**

**Problem:** Out of memory during processing
**Solution:** The script processes files individually to minimize memory usage. For very large datasets, consider:
```bash
# Process in smaller chunks
python run_twic_expansion.py --start-twic 1 --end-twic 500
python run_twic_expansion.py --start-twic 501 --end-twic 1000
# etc.
```

---

## 🔧 **Advanced Configuration**

### **Custom Base URL**
If TWIC changes their URL structure:
```python
# In twic_downloader.py
downloader = TWICDownloader(base_url="https://new-twic-url.com/archives")
```

### **Custom File Patterns**
The script tries multiple URL patterns automatically:
- `twic{NNNN}g.zip` (modern 4-digit format)
- `twic{NNN}g.zip` (3-digit format)  
- `twic{N}g.zip` (variable digits)
- `twic{NNNN}.zip` (no 'g' suffix)

### **Batch Size Adjustment**
For Weaviate loading, adjust batch size in `games_loader.py`:
```python
BATCH_SIZE = 100  # Reduce if getting timeouts
```

---

## 📊 **Performance Expectations**

### **Download Phase**
- **Time:** 1-4 hours (depending on internet speed)
- **Bandwidth:** ~500MB-1GB total
- **CPU:** Low (mostly I/O bound)
- **Memory:** <200MB

### **Processing Phase**  
- **Time:** 30-60 minutes
- **CPU:** Moderate (parsing PGN files)
- **Memory:** 500MB-2GB (for large combined file)
- **Disk:** 5-10GB temporary space

### **Loading Phase**
- **Time:** 2-4 hours (depending on Weaviate performance)
- **CPU:** Moderate
- **Memory:** 1-2GB
- **Network:** High (if Weaviate is remote)

---

## 🎯 **Integration with Existing Database**

The expansion seamlessly integrates with your existing chess database:

1. **Preserves existing games** (no duplicates added)
2. **Uses same schema** as your current ChessGame collection
3. **Maintains all metadata** (player ratings, titles, opening classifications)
4. **Enhances search capabilities** with historical games

### **Verify Integration**
After loading, verify your expanded database:
```python
import weaviate
client = weaviate.connect_to_local()
collection = client.collections.get("ChessGame")

# Check total games
result = collection.aggregate.over_all(total_count=True)
print(f"Total games in database: {result.total_count}")

# Check date range
result = collection.query.fetch_objects(limit=5, return_metadata=['creation_time'])
print("Sample games loaded:")
for obj in result.objects:
    print(f"- {obj.properties['white_player']} vs {obj.properties['black_player']} ({obj.properties['date_utc']})")
```

---

## 🏁 **Success Indicators**

When the expansion completes successfully, you should see:

```
🎉 Complete Expansion Finished!
📁 Combined file: /path/to/twic_complete_20241201.pgn
🎲 Games loaded: 6,234,567
💡 Your Weaviate database now contains the complete TWIC archive!
```

Your chess database is now ready with:
- ✅ Complete TWIC historical archive
- ✅ Chronologically ordered games
- ✅ Duplicate-free dataset
- ✅ Rich metadata for advanced searching
- ✅ Seamless integration with existing data

Enjoy exploring decades of master-level chess games! 🎲♟️ 