from .db import DatabaseConfig
from datetime import datetime


class QueueEntry:
    def __init__(self, user_id, service_id, scheduled_time, db: DatabaseConfig):
        self.user_id = user_id
        self.service_id = service_id
        self.scheduled_time = scheduled_time
        self.db = db
    
    async def save(self):
        try:
            async with self.db.pool.acquire() as conn:
                position_result = await conn.fetchrow("""
                    SELECT COALESCE(MAX(position), 0) + 1 as next_position 
                    FROM queue_entries 
                    WHERE status = 'waiting'
                """)
                next_position = position_result['next_position']
                
                entry_id = await conn.fetchrow("""
                    INSERT INTO queue_entries (user_id, service_id, scheduled_time, status, position)
                    VALUES ($1, $2, $3, 'waiting', $4) 
                    RETURNING id
                """, self.user_id, self.service_id, self.scheduled_time, next_position)
                return entry_id['id']
        except Exception as e:
            print('Error from queue entry save:', e)
    
    @classmethod
    async def get_user_queue(cls, user_id: int, db: DatabaseConfig):
        try:
            async with db.pool.acquire() as conn:
                entries = await conn.fetch("""
                    SELECT qe.*, s.name as service_name, s.duration, s.price
                    FROM queue_entries qe
                    JOIN services s ON qe.service_id = s.id
                    WHERE qe.user_id = $1 AND qe.status = 'waiting'
                    ORDER BY qe.position
                """, user_id)
                return entries
        except Exception as e:
            print('Error from get user queue:', e)
            return []
    
    @classmethod
    async def get_all_queue(cls, db: DatabaseConfig):
        try:
            async with db.pool.acquire() as conn:
                entries = await conn.fetch("""
                    SELECT qe.*, u.full_name, u.username, s.name as service_name, s.duration, s.price
                    FROM queue_entries qe
                    JOIN users u ON qe.user_id = u.id
                    JOIN services s ON qe.service_id = s.id
                    WHERE qe.status = 'waiting'
                    ORDER BY qe.position
                """)
                return entries
        except Exception as e:
            print('Error from get all queue:', e)
            return []
    
    @classmethod
    async def update_status(cls, entry_id: int, status: str, db: DatabaseConfig):
        try:
            async with db.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE queue_entries 
                    SET status = $2
                    WHERE id = $1
                """, entry_id, status)
                
                if status in ['completed', 'cancelled']:
                    await cls._reorder_positions(db)
                
                return True
        except Exception as e:
            print('Error from update status:', e)
            return False
    
    @classmethod
    async def cancel_entry(cls, entry_id: int, user_id: int, db: DatabaseConfig):
        try:
            async with db.pool.acquire() as conn:

                entry = await conn.fetchrow("""
                    SELECT * FROM queue_entries 
                    WHERE id = $1 AND user_id = $2 AND status = 'waiting'
                """, entry_id, user_id)
                
                if entry:
                    await conn.execute("""
                        UPDATE queue_entries 
                        SET status = 'cancelled'
                        WHERE id = $1
                    """, entry_id)
                    
                    await cls._reorder_positions(db)
                    return True
                return False
        except Exception as e:
            print('Error from cancel entry:', e)
            return False
    
    @classmethod
    async def change_position(cls, entry_id: int, direction: str, db: DatabaseConfig):
        try:
            async with db.pool.acquire() as conn:
                current_entry = await conn.fetchrow("""
                    SELECT * FROM queue_entries WHERE id = $1 AND status = 'waiting'
                """, entry_id)
                
                if not current_entry:
                    return False
                
                current_position = current_entry['position']
                
                if direction == 'up' and current_position > 1:
                    new_position = current_position - 1
                elif direction == 'down':
                    max_position = await conn.fetchval("""
                        SELECT MAX(position) FROM queue_entries WHERE status = 'waiting'
                    """)
                    if current_position < max_position:
                        new_position = current_position + 1
                    else:
                        return False
                else:
                    return False
                
              
                target_entry = await conn.fetchrow("""
                    SELECT id FROM queue_entries 
                    WHERE position = $1 AND status = 'waiting'
                """, new_position)
                
                if target_entry:
                    await conn.execute("""
                        UPDATE queue_entries 
                        SET position = $1
                        WHERE id = $2
                    """, current_position, target_entry['id'])
                
                await conn.execute("""
                    UPDATE queue_entries 
                    SET position = $1
                    WHERE id = $2
                """, new_position, entry_id)
                
                return True
        except Exception as e:
            print('Error from change position:', e)
            return False
    
    @classmethod
    async def _reorder_positions(cls, db: DatabaseConfig):
        try:
            async with db.pool.acquire() as conn:
                entries = await conn.fetch("""
                    SELECT id FROM queue_entries 
                    WHERE status = 'waiting' 
                    ORDER BY position
                """)
                
                for i, entry in enumerate(entries, 1):
                    await conn.execute("""
                        UPDATE queue_entries 
                        SET position = $2
                        WHERE id = $1
                    """, entry['id'], i)
        except Exception as e:
            print('Error from reorder positions:', e)
