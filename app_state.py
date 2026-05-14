bot = None        # aiogram Bot instance
storage = None    # MemoryStorage instance
scheduler = None  # AsyncIOScheduler instance
admin_ids = []    # list[int] of admin Telegram IDs
user_messages: dict = {}  # user_id → [msg_id, ...] tracked for deletion
