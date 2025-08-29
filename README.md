# How the Barbershop Bot Works: A Comprehensive Guide

## Introduction & High-Level Architecture

Welcome to this guide on building a Telegram bot for managing a barbershop queue. This document will walk you through the entire project, explaining the concepts and structure so you can understand how it works and how to build something similar.

The application is an asynchronous Telegram bot written in Python. It uses the `aiogram` library to handle interactions with the Telegram API and the `asyncpg` library for high-performance, asynchronous communication with a PostgreSQL database.

The project is broken down into several logical components:

1.  **Database Layer (`db.py`)**: The foundation that manages the connection to the database and defines the structure of our data tables.
2.  **Data Models (`user.py`, `service.py`, `queue_entry.py`)**: A set of classes that represent the data in our tables. These classes contain the logic for creating, reading, updating, and deleting records (CRUD operations).
3.  **State Management (`states.py`)**: Defines the different "states" or steps in a conversation with the user, which is essential for multi-part interactions like registering for a service.
4.  **Handlers (`admin_handler.py`, `user_handler.py`)**: These are the brains of the bot. They contain the logic that defines how the bot responds to user commands and messages. The logic is split between what a regular user can do and what an administrator can do.
5.  **Configuration and Entry Point (`config.py`, `bot.py`)**: These files configure the bot (like setting the API token) and start the application.

Let's dive into each part.

---

## Part 1: The Database Foundation (`db.py`)

Every application that stores data needs a database. This bot uses PostgreSQL, a powerful open-source relational database. The `db.py` file is responsible for all direct interaction with it.

The key library here is `asyncpg`. It's an asynchronous library, which means it can perform database operations without blocking the rest of the program. This is crucial for a bot that needs to be responsive to many users at once.

The `DatabaseConfig` class holds all the logic for managing the database connection.

*   **`__init__(self, user, password, db_name, port, host)`**: The constructor simply stores the database credentials (username, password, etc.) as instance attributes.
*   **`async def connect(self)`**: This method doesn't just create a single connection; it creates a **connection pool** using `asyncpg.create_pool()`. A connection pool is a collection of ready-to-use database connections. When the application needs to talk to the database, it borrows a connection from the pool and returns it when done. This is much more efficient than opening and closing a new connection for every single query.
*   **`async def create_tables(self)`**: This is one of the most important methods. It executes SQL commands to create the database tables if they don't already exist. Let's look at the tables:
    *   **`users`**: Stores information about each person who interacts with the bot.
        *   `id`: A unique, auto-incrementing number for each user (Primary Key).
        *   `telegram_id`: The user's unique ID from Telegram. This is used to identify them.
        *   `is_staff`: A boolean (`TRUE` or `FALSE`) flag to determine if a user is an administrator.
    *   **`services`**: Stores the list of services the barbershop offers.
        *   `name`, `duration`, `price`: Self-explanatory details about each service.
    *   **`queue_entries`**: This table connects users and services. It represents a single appointment or entry in the queue.
        *   `user_id` and `service_id`: These are **Foreign Keys**. They link to the `id` in the `users` and `services` tables, respectively, creating a relationship. This ensures that every queue entry is associated with a real user and a real service.
        *   `status`: Can be 'waiting', 'completed', or 'cancelled'.
        *   `position`: The user's current place in the 'waiting' queue.

---

## Part 2: Data Models - The Rules of avery Part

Models are classes that represent the business logic for interacting with a specific database table. Instead of writing raw SQL queries in our bot logic, we call methods on these model classes.

**`user.py` (The `User` class)**
This class handles everything related to the `users` table.

*   **`save()`**: Inserts a new user into the database. It uses `INSERT INTO ... RETURNING id` to get the ID of the newly created user.
*   **`get_user()`**: Fetches a single user's data based on their `telegram_id`.
*   **`check_status()`**: A specific method to check if a user is an admin. This is used for authorization.
*   **`@classmethod`**: You'll notice methods like `get_all_users`. These are *class methods*, meaning you can call them on the class itself (e.g., `User.get_all_users(db)`) rather than on an instance of a user. This makes sense for actions that concern the whole table, not just one user.

**`service.py` (The `Service` class)**
This class provides full CRUD (Create, Read, Update, Delete) functionality for the `services` table.

*   `save()`: Adds a new service.
*   `get_services()`: Retrieves all available services.
*   `update_service()`: Modifies an existing service.
*   `delete_service()`: Removes a service.

**`queue_entry.py` (The `QueueEntry` class)**
This is the most complex model because it manages the core queue logic.

*   **`save()`**: When a user books an appointment, this method calculates their position in the queue. It finds the current maximum position (`MAX(position)`) and adds 1, ensuring the new user is placed at the end of the line.
*   **`get_user_queue()` & `get_all_queue()`**: These methods use SQL `JOIN` to combine data from all three tables. When an admin views the queue, they need to see the user's name and the service name, not just IDs. A `JOIN` allows us to fetch all this related information in a single, efficient query.
*   **`update_status()` & `cancel_entry()`**: These methods change the `status` of a queue entry. When an entry is 'completed' or 'cancelled', it's effectively removed from the active queue.
*   **`_reorder_positions()`**: This is a crucial private helper method. If someone at position 3 cancels, everyone at positions 4, 5, 6, etc., needs to move up. This method re-calculates and updates the positions for all 'waiting' entries to keep the queue order consistent.
*   **`change_position()`**: This contains the logic for an admin to manually move a user up or down in the queue. It works by swapping the `position` values of the selected entry and its neighbor.

---

## Part 3: State Management (`states.py`)

Imagine you want to add a new service. The bot needs to ask you for the name, then the duration, then the price. This is a multi-step conversation. How does the bot remember where you are in the process? The answer is a **Finite State Machine (FSM)**.

The `states.py` file defines the "memory" of the bot for these conversations.

*   **`ServiceState`**: Defines the states for adding a new service (`name`, `duration`, `price`) and for updating one. When the admin starts adding a service, the bot enters the `ServiceState.name` state. After the admin provides a name, the bot transitions to the `ServiceState.duration` state, and so on.
*   **`QueueState`**: Defines the states for a user joining the queue (`select_service`, `select_time`, `confirm_booking`).

---

## Part 4: The Bot's Brain - Handlers

Handlers are functions that are triggered by user actions (like sending a message or clicking a button). The project neatly divides these into `admin_handler.py` and `user_handler.py`. Both use an `aiogram.Router` to group their respective handlers.

**`admin_handler.py`**
This file contains all the functionality available only to administrators.

*   **Authorization Check**: Almost every function starts with a check: `if not await user.check_status():`. This ensures that only users with `is_staff=TRUE` can perform admin actions.
*   **Adding a Service (FSM in Action)**:
    1.  The `add_service_handler` is triggered when an admin sends the message "➕ Добавить услугу".
    2.  It sets the state to `ServiceState.name` using `await state.set_state(...)`.
    3.  The next message the admin sends will be caught by `service_name_handler` because it's specifically listening for messages while in the `ServiceState.name` state.
    4.  This handler saves the name using `await state.update_data(name=msg.text)` and transitions to the next state, `ServiceState.duration`.
    5.  This process continues until the final step (`service_price_handler`), where all the collected data is retrieved with `await state.get_data()` and used to create and save a new `Service` object. Finally, `await state.clear()` ends the conversation and clears the state.
*   **Viewing and Managing Data**: Functions like `view_services_admin_handler` and `view_queue_handler` fetch data using the models (`Service.get_services(db)`) and then loop through the results. For each item, they create an `InlineKeyboardMarkup`—a set of buttons attached to a message.
*   **Callback Queries**: When an admin clicks a button (like "Удалить" or "Вверх"), Telegram sends a `CallbackQuery`. Handlers decorated with `@admin_router.callback_query(...)` catch these. They parse the `callback.data` (e.g., `'delete_service=123'`) to get the relevant ID and then call the appropriate model method (`Service.delete_service(123, db)`).

**`user_handler.py`**
This file handles the logic for regular users.

*   **Start Command**: The `start_handler` is the first point of contact. It checks if the user exists in the database. If not, it creates a new user record.
*   **Joining the Queue (FSM)**: This flow is very similar to the admin's "add service" flow but uses `QueueState`. It guides the user through selecting a service, then a time slot, and finally confirming their booking. The buttons are generated dynamically based on the available services and time slots.
*   **Viewing "My Queue"**: The `my_queue_handler` fetches only the queue entries for the specific user who sent the command, using `QueueEntry.get_user_queue()`.

---

## Part 5: Configuration and Assembly (`config.py`, `bot.py`)

**`config.py`**
This file's purpose is to keep configuration details separate from the application logic. This is a very good practice.

*   It initializes the `Bot` object from `aiogram` with the secret API token.
*   It creates the `DatabaseConfig` instance with all the necessary credentials. This way, if you need to change the database password, you only need to change it in this one file.

**`bot.py`**
This is the main entry point that ties everything together and starts the bot.

*   **`Dispatcher`**: The `Dispatcher` is the central object in `aiogram` that routes incoming updates (messages, button clicks) to the correct handlers. `MemoryStorage()` is used to store the FSM state data in the computer's RAM.
*   **`dp.include_router(...)`**: This is where the handlers from `admin_handler.py` and `user_handler.py` are registered with the main dispatcher.
*   **`async def main()`**: This is the main asynchronous function that runs the bot.
    1.  It first connects to the database pool: `await db.connect()`.
    2.  It ensures the tables are created: `await db.create_tables()`.
    3.  `await dp.start_polling(Bot_Tokken)` starts the bot. The bot now continuously "polls" or asks Telegram for any new updates.
    4.  The `finally` block ensures that `await db.close()` is called when the bot shuts down, gracefully closing the database connections.
*   **`if __name__ == '__main__':`**: This is standard Python syntax that ensures the `asyncio.run(main())` code only runs when the script is executed directly.