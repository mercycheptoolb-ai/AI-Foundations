# data/

The course data isn't in this repository. To run the app, unzip the course's `data.zip` here so the folder looks like this:

```
data/
├── campus_customs.db   # SQLite: catalogue, inventory, users, chat_messages
└── products/           # 102 product photos (*.jpg)
```

The backend adds its own tables and columns (`sessions`, page context on `chat_messages`) the first time it starts. Existing rows aren't changed.
