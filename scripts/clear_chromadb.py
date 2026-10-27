import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))

from backend.app.services.chroma_service import ChromaStorageService
from backend.app.core.config import settings
from backend.app.core.logging_config import logger

def clear_all_knowledge_data():
    print("=" * 60)
    print("STARTING COMPLETE CHROMADB & KNOWLEDGE BASE PURGE")
    print("=" * 60)

    # 1. Connect to ChromaDB (Cloud or Local)
    cs = ChromaStorageService()
    coll = cs.collection
    print(f"Connected to ChromaDB Collection: '{coll.name}'")
    print(f"Chroma Mode: {settings.CHROMA_MODE}")
    
    # 2. Delete all records from ChromaDB collection
    try:
        all_records = coll.get()
        all_ids = all_records.get("ids", [])
        if all_ids:
            print(f"Found {len(all_ids)} chunks in ChromaDB. Deleting in batches...")
            # Delete in batches of 100 to avoid payload limits
            batch_size = 100
            for i in range(0, len(all_ids), batch_size):
                batch_ids = all_ids[i:i + batch_size]
                coll.delete(ids=batch_ids)
                print(f"  Deleted batch {i // batch_size + 1} ({len(batch_ids)} records)...")
            print("Successfully deleted all records from ChromaDB.")
        else:
            print("ChromaDB collection was already empty.")
    except Exception as e:
        print(f"Error deleting records by ID: {e}. Attempting collection recreate...")
        try:
            cs.client.delete_collection(name=coll.name)
            cs.collection = cs.client.create_collection(
                name=coll.name,
                metadata={"description": "AI Insurance Assistant Knowledge Base"}
            )
            print("Successfully recreated ChromaDB collection.")
        except Exception as e2:
            print(f"Failed to recreate collection: {e2}")

    final_count = coll.count()
    print(f"ChromaDB Collection Count is now: {final_count}")

    # 3. Clear data/parent_store.json
    if settings.PARENT_STORE_PATH.exists():
        with open(settings.PARENT_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        print(f"Cleared parent store at: {settings.PARENT_STORE_PATH}")
    else:
        print("Parent store file does not exist; nothing to reset.")

    # 4. Clear data/ingestion_history.json
    if settings.HISTORY_STORE_PATH.exists():
        with open(settings.HISTORY_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        print(f"Cleared ingestion history at: {settings.HISTORY_STORE_PATH}")
    else:
        print("Ingestion history file does not exist; nothing to reset.")

    # 5. Clear SQLite document_records and ingestion_jobs
    try:
        from backend.app.db.sqlite_manager import sqlite_db
        with sqlite_db._get_connection() as conn:
            conn.execute("DELETE FROM ingestion_jobs;")
            conn.execute("DELETE FROM document_records;")
            conn.commit()
        print("Cleared SQLite tables 'ingestion_jobs' and 'document_records'.")
    except Exception as e:
        print(f"Note: Could not clear SQLite document tables: {e}")

    # 6. Rebuild in-memory BM25 index
    try:
        from backend.app.services.bm25_service import BM25SearchService
        bm25_svc = BM25SearchService(cs)
        print(f"BM25 index refreshed. Active documents in BM25: {len(bm25_svc.chunk_ids)}")
    except Exception as e:
        print(f"Note on BM25 refresh: {e}")

    print("=" * 60)
    print("PURGE COMPLETE: ChromaDB and parent stores are ready for fresh ingestion.")
    print("=" * 60)

if __name__ == "__main__":
    clear_all_knowledge_data()
