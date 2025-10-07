"""Database operations for ReolinkANPR."""

import aiosqlite
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from src.logger import logger


class Database:
    """SQLite database for storing ANPR events."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Create database tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            # Events table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    plate_number TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    image_path TEXT,
                    plate_crop_path TEXT,
                    box_coordinates TEXT,
                    frame_count INTEGER DEFAULT 1
                )
            ''')

            # Create index on timestamp for faster queries
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON events(timestamp DESC)
            ''')

            # Create index on plate_number for search
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_plate_number
                ON events(plate_number)
            ''')

            await db.commit()

    async def add_event(self, event_data: Dict) -> int:
        """Add a new ANPR event to database with deduplication."""
        async with aiosqlite.connect(self.db_path) as db:
            plate_number = event_data.get('plate_number')
            
            # Check for duplicate within last 30 seconds
            cursor = await db.execute('''
                SELECT id, timestamp FROM events
                WHERE plate_number = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (plate_number,))
            
            last_event = await cursor.fetchone()
            
            if last_event:
                # Parse timestamp and check if within 30 seconds
                last_time = datetime.fromisoformat(last_event[1])
                time_diff = (datetime.now() - last_time).total_seconds()
                
                if time_diff < 30:
                    logger.info(f"Duplicate plate {plate_number} detected within 30s - skipping")
                    return last_event[0]  # Return existing event ID
            
            # No duplicate found - insert new event
            cursor = await db.execute('''
                INSERT INTO events
                (plate_number, confidence, image_path, plate_crop_path,
                 box_coordinates, frame_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                plate_number,
                event_data.get('confidence'),
                event_data.get('image_path'),
                event_data.get('plate_crop_path'),
                json.dumps(event_data.get('box_coordinates', {})),
                event_data.get('frame_count', 1)
            ))
            await db.commit()
            return cursor.lastrowid

    async def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get recent ANPR events."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM events
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_paginated_events(
        self,
        limit: int,
        offset: int,
        search: str = '',
        filter_type: str = 'all'
    ) -> tuple[List[Dict], int]:
        """Get paginated events with optional search and filter."""
        where_clause, params = self._build_where_clause(search, filter_type)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Get total count
            count_query = f'SELECT COUNT(*) as count FROM events {where_clause}'
            cursor = await db.execute(count_query, params)
            row = await cursor.fetchone()
            total = row['count']

            # Get paginated results
            query = f'''
                SELECT * FROM events
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            '''
            params.extend([limit, offset])
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            events = [dict(row) for row in rows]

            return events, total

    def _build_where_clause(self, search: str = '', filter_type: str = 'all') -> tuple[str, list]:
        """Build WHERE clause for search and filter."""
        conditions = []
        params = []

        # Search condition
        if search:
            search_term = f'%{search}%'
            conditions.append('plate_number LIKE ?')
            params.append(search_term)

        # Date filter
        if filter_type == 'today':
            conditions.append("DATE(timestamp) = DATE('now')")
        elif filter_type == 'week':
            conditions.append("DATE(timestamp) >= DATE('now', '-7 days')")
        elif filter_type == 'month':
            conditions.append("DATE(timestamp) >= DATE('now', '-30 days')")

        # Build WHERE clause
        if conditions:
            where_clause = 'WHERE ' + ' AND '.join(conditions)
        else:
            where_clause = ''

        return where_clause, params
