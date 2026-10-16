from database import init_db
from app import EventHub

if __name__ == "__main__":
    init_db()
    app = EventHub()
    app.mainloop()
