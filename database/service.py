from .db import DatabaseConfig


class Service:
    def __init__(self, name, duration, price, db: DatabaseConfig):
        self.name = name
        self.duration = duration
        self.price = price
        self.db = db
    
    async def save(self):
        try:
            async with self.db.pool.acquire() as conn:
                service_id = await conn.fetchrow("""
                    INSERT INTO services (name, duration, price)
                    VALUES ($1, $2, $3) 
                    RETURNING id
                """, self.name, self.duration, self.price)
                return service_id['id']
        except Exception as e:
            print('Error from service save:', e)
    
    @classmethod
    async def get_services(cls, db: DatabaseConfig):
        try:
            async with db.pool.acquire() as conn:
                services = await conn.fetch("""
                    SELECT * FROM services ORDER BY name
                """)
                return services
        except Exception as e:
            print('Error from get services:', e)
            return []
    
    @classmethod
    async def get_service_by_id(cls, service_id: int, db: DatabaseConfig):
        try:
            async with db.pool.acquire() as conn:
                service = await conn.fetchrow("""
                    SELECT * FROM services WHERE id = $1
                """, service_id)
                return service
        except Exception as e:
            print('Error from get service by id:', e)
            return None
    
    @classmethod
    async def update_service(cls, service_id: int, name: str, duration: int, price: float, db: DatabaseConfig):
        try:
            async with db.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE services 
                    SET name = $2, duration = $3, price = $4
                    WHERE id = $1
                """, service_id, name, duration, price)
                return True
        except Exception as e:
            print('Error from update service:', e)
            return False
    
    @classmethod
    async def delete_service(cls, service_id: int, db: DatabaseConfig):
        try:
            async with db.pool.acquire() as conn:
                await conn.execute("""
                    DELETE FROM services WHERE id = $1
                """, service_id)
                return True
        except Exception as e:
            print('Error from delete service:', e)
            return False
