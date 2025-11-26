# TWIC Loader Interruption & Resume Behavior

## 🔄 What Happens During Interruption

### ✅ Data That Survives Interruption:
1. **Completed Files**: Any files marked in `processed_files` are fully loaded
   - TWIC 1574: 9,607 games ✅ SAFE (marked as processed)
   - All games from completed files remain in Weaviate permanently

2. **Partial Batches**: Completed batches from the current file
   - Each batch of 100 games is committed immediately to Weaviate
   - If TWIC 1575 was interrupted after loading 3,000 games, those 3,000 games remain in database

### ⚠️ What Gets Lost/Repeated:
1. **Progress Tracking**: Only updates after complete file processing
   - If interrupted mid-file, that file is NOT marked as processed
   - Current file will be reprocessed from the beginning on restart

2. **Potential Duplication**: 
   - TWIC 1575 games already inserted will remain in database
   - On restart, TWIC 1575 will be loaded again from the beginning
   - Could result in duplicate games in database

## 🔧 Resume Behavior

### On Restart:
```python
# Loader checks processed_files list
remaining_files = [f for f in twic_files if f.name not in self.progress["processed_files"]]

# Example after interruption:
# processed_files: ["twic1574_twic1574.pgn"]  ✅ Skip this one
# remaining_files: ["twic1575_twic1575.pgn", "twic1576_twic1576.pgn", ...]  🔄 Process these
```

### File-Level Resume:
- ✅ **Completed files are skipped** (no duplication for completed files)
- ⚠️ **Interrupted file is reprocessed** (potential duplication for partial file)

## 🛡️ Current Safeguards

1. **Batch Commits**: Games are saved in 100-game batches
2. **File-Level Tracking**: Prevents reprocessing completed files  
3. **Progress Logging**: Detailed logs show exactly what was processed
4. **Resume Capability**: Automatic resume from last completed file

## 🎯 Recommended Actions

### If Interruption Occurs:
1. **Check database count**: `SELECT COUNT(*) FROM ChessGame WHERE source_file = 'twic1575_twic1575.pgn'`
2. **Clean duplicates if needed**: Remove partial file data before restart
3. **Or accept minor duplication**: Usually acceptable for analysis purposes

### To Minimize Risk:
1. **Monitor progress regularly**: Check log files for completion status
2. **Use stop signal**: Create `stop_2025_loading.txt` for clean shutdown
3. **Let files complete**: Wait for file completion messages before interrupting

## 📊 Current Status Protection

Based on current progress:
- ✅ **TWIC 1574**: 9,607 games safely stored (marked as processed)
- 🔄 **TWIC 1575**: In progress (potential duplication risk if interrupted)
- ⏳ **TWIC 1576-1594**: Not yet started (safe from duplication)

**Bottom Line**: Your data is safe, but interrupting mid-file may cause minor duplication for that specific file only. 