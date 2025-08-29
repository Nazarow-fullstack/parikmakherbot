import asyncpg

class DatabaseConfig:
    def __init__(self,user,password,db_name,port=5432,host='localhost'):
        self.user=user
        self.password=password
        self.db_name=db_name
        self.port=port
        self.host=host
        self.pool=None
    async def connect(self):
        try:
            self.pool=await asyncpg.create_pool(
            user=self.user ,
            password=self.password,
            database=self.db_name,
            port=self.port,
            host=self.host
            )
        except Exception as e:
            print('Erorr in connect to database',e)
    async def close(self):
        await self.pool.close()
    async def create_tables(self):
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    full_name VARCHAR(255),
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    duration INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS queue_entries (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    service_id INT NOT NULL,
    scheduled_time TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('waiting', 'completed', 'cancelled')),
    position INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (service_id) REFERENCES services(id)
);
''')
        except Exception as e:
            print('Error when creating tables ',e)
