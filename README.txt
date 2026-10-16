EVENTHUB – UI + REGISTRATION + PHOTO SYSTEM

This version is based on the uploaded EventHub project.

NEW:
1. Customer registration from the Customer Login screen.
2. New accounts are saved to SQLite and immediately enter the customer dashboard.
3. Duplicate usernames are blocked.
4. Password confirmation is checked.
5. Added photo_manager.py.
6. Added a photos/ folder where you can add your own photos without editing Python.
7. Event and package cards automatically display matching photos when present.

RUN:
  C:\Python314\python.exe -m pip install Pillow
  C:\Python314\python.exe main.py

CUSTOMER DEMO:
  username: customer
  password: 1234

ADMIN DEMO:
  username: admin
  password: admin123

PHOTO FILES:
  photos/README.txt explains exactly where to place photos.

MAIN FILES:
  main.py          starts the application and database
  app.py           UI, navigation, login, registration, booking, admin
  database.py      SQLite tables, accounts, packages, reservations
  photo_manager.py photo folders and automatic photo loading
  config.py        colors, categories and event types
  auth/login.py    reserved authentication module for future separation
