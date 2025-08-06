# Deployment

1. Install dependencies: `pip install -r requirements.txt`.
2. Set environment variables in `.env` (see README).
3. Initialize database: `python database.py`.
4. Run the bot: `python main.py`.

The container module `infrastructure.container.Container` wires all components and should be configured before starting the bot.
