from .db import DatabaseConfig

class User:
    def __init__(self, telegram_id, username, full_name, db: DatabaseConfig):
        self.telegram_id = telegram_id
        self.username = username
        self.full_name = full_name
        self.db = db
    
    async def save(self):
        try:
            async with self.db.pool.acquire() as conn:
                user_id = await conn.fetchrow("""
                    INSERT INTO users (telegram_id, username, full_name)
                    VALUES ($1, $2, $3) 
                    RETURNING id
                """, self.telegram_id, self.username, self.full_name)
                return user_id['id']
        except Exception as e:
            print('Error from user save:', e)
    

    async def get_user(self):
        try:
            async with self.db.pool.acquire() as conn:
                user = await conn.fetchrow("""
                    SELECT * FROM users WHERE telegram_id = $1
                """, self.telegram_id)
                return user
        except Exception as e:
            print('Error from get user:', e)
            return None
    
    async def check_status(self):
        try:
            async with self.db.pool.acquire() as conn:
                user = await conn.fetchrow("""
                    SELECT is_staff FROM users WHERE telegram_id = $1
                """, self.telegram_id)
                return user['is_staff'] if user else False
        except Exception as e:
            print('Error from check status:', e)
            return False
    
    @classmethod
    async def get_all_users(cls, db: DatabaseConfig):
        try:
            async with db.pool.acquire() as conn:
                users = await conn.fetch("""
                    SELECT * FROM users
                """)
                return users
        except Exception as e:
            print('Error from get all users:', e)
            return []
    
    @classmethod
    async def make_admin(cls, telegram_id: int, db: DatabaseConfig):
        try:
            async with db.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE users SET is_staff = TRUE WHERE telegram_id = $1
                """, telegram_id)
                return True
        except Exception as e:
            print('Error from make admin:', e)
            return False
