import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from PIL import Image, ImageTk
import shutil
from tkinter import ttk, messagebox
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from config import *
from database import (
    connect,
    money,
    package,
    is_available,
    get_unavailable_package_ids,
    authenticate,
    create_reservation,
    register_customer,
    ensure_message_tables,
    get_unread_message_count
)
from photo_manager import (
    ensure_photo_folders,
    package_photo_path,
    event_photo_path,
    load_image,
    load_faded_image,
    hero_photo_path,
    hero1_photo_path
)

class EventHub(tk.Tk):
    
    def __init__(self):
        super().__init__()
        self.title("EventHub – Event Package Booking and Marketplace System")
        self.geometry("1400x850")
        self.minsize(1100, 700)
        self.configure(bg=LIGHT)

        self.user = None
        self.event_type = "Birthday"
        self.booking = {}
        self.selected = {}
        
        self._sidebar = None
        self._content = None

        self._photo_refs = []
        self._sidebar = None
        self._content = None

        ensure_photo_folders()
        ensure_message_tables()
        self.setup_styles()
        self.show_landing()


    def setup_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TCombobox", padding=7, fieldbackground="white")
        s.configure("Treeview", rowheight=34, font=("Segoe UI", 10))
        s.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    
    def clear(self):
        if self._content and self._content.winfo_exists():
            for widget in self._content.winfo_children():
                widget.destroy()
        else:
            for widget in self.winfo_children():
                widget.destroy()
    
    def clear_all(self):
        for widget in self.winfo_children():
            widget.destroy()

        self._sidebar = None
        self._content = None


    def label(self, parent, text, size=10, bold=False, color=TEXT, bg=CARD, **kw):
        return tk.Label(
            parent, text=text, bg=bg, fg=color,
            font=("Segoe UI", size, "bold" if bold else "normal"), **kw
        )

    def button(self, parent, text, command, primary=True, width=None):

        normal_bg = PINK if primary else "#EEE7F5"
        hover_bg = PURPLE2 if primary else "#DCCCEC"

        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=normal_bg,
            fg="white" if primary else PURPLE,
            activebackground=hover_bg,
            activeforeground="white",
            relief="flat",
            bd=0,
            font=("Segoe UI", 10, "bold"),
            padx=16,
            pady=9,
            width=width
        )

        # Mouse hover effect
        btn.bind(
            "<Enter>",
            lambda e: btn.configure(
                bg=hover_bg
            )
        )

        btn.bind(
            "<Leave>",
            lambda e: btn.configure(
                bg=normal_bg
            )
        )

        return btn

    def topbar(self, title="", admin=False):
        bar = tk.Frame(self, bg=CARD, height=72,
                       highlightbackground=BORDER, highlightthickness=1)
        self._topbar = bar
        bar.pack(fill="x")
        bar.pack_propagate(False)

        self.label(bar, "♡ EventHub", 21, True, PURPLE, CARD).pack(
            side="left", padx=28
        )

        if title:
            self.label(bar, title, 11, False, MUTED, CARD).pack(side="left")

        if self.user:
            userbox = tk.Frame(bar, bg=CARD)
            userbox.pack(side="right", padx=25)
            self.label(userbox, "●", 15, True, PINK, CARD).pack(side="left")
            self.label(userbox, self.user[0], 10, True, TEXT, CARD).pack(
                side="left", padx=7
            )
            self.button(userbox, "Logout", self.logout, False).pack(
                side="left", padx=8
            )

    
    def sidebar(self, active, admin=False):
        if self._sidebar is None or not self._sidebar.winfo_exists():
            self._sidebar = tk.Frame(self, bg="#30204F", width=220)
            self._sidebar.pack(side="left", fill="y")
            self._sidebar.pack_propagate(False)

        side = self._sidebar

        for widget in side.winfo_children():
            widget.destroy()

        self.label(
            side, "♡ EventHub", 20, True, "white", "#30204F"
        ).pack(anchor="w", padx=24, pady=(25, 4))

        self.label(
            side,
            "ADMIN" if admin else "CUSTOMER",
            9, True, "#CFC0E2", "#30204F"
        ).pack(anchor="w", padx=26, pady=(0, 25))

        if admin:
            items = [
                ("⌂", "Dashboard", self.admin_dashboard),
                ("▤", "Reservations", self.admin_reservations),
                ("▧", "Package Management", self.admin_packages),
                ("▦", "Calendar", self.admin_calendar),
                ("✉", "Messages", self.admin_messages),
            ]
        else:
            items = [
                ("⌂", "Dashboard", self.customer_dashboard),
                ("▣", "Browse Events", self.choose_event),
                ("▤", "My Reservations", self.my_reservations),
                ("✉", "Messages", self.customer_messages),
                ("♙", "Profile", self.profile),
            ]

        for symbol, name, cmd in items:
            bg = "#5C3B8D" if name == active else "#30204F"
            badge_count = 0

            if name == "Messages" and self.user:
                try:
                    if admin:
                        badge_count = get_unread_message_count("admin", "customer")
                    else:
                        badge_count = get_unread_message_count(self.user[0], "admin")
                except Exception as e:
                    print("Unread count error:", e)

            item = tk.Frame(side, bg=bg, height=48)
            item.pack(fill="x", padx=10, pady=3)
            item.pack_propagate(False)

            tk.Label(
                item,
                text=symbol,
                font=("Segoe UI Symbol", 14),
                fg="white",
                bg=bg,
                width=3,
                anchor="center"
            ).pack(side="left", padx=(7, 5))

            tk.Button(
                item,
                text=name,
                command=cmd,
                anchor="w",
                bg=bg,
                fg="white",
                activebackground="#5C3B8D",
                activeforeground="white",
                relief="flat",
                bd=0,
                font=("Segoe UI", 10, "bold" if name == active else "normal"),
                padx=5,
                pady=10
            ).pack(side="left", fill="both", expand=True)

            if name == "Messages" and badge_count > 0:
                tk.Label(
                    item,
                    text=str(badge_count),
                    bg="#E04B96",
                    fg="white",
                    font=("Segoe UI", 9, "bold"),
                    padx=6,
                    pady=2
                ).pack(side="right", padx=10)

        tk.Frame(side, bg="#30204F").pack(fill="both", expand=True)

        tk.Button(
            side,
            text="⇥   Logout",
            command=self.logout,
            anchor="w",
            bg="#432B62",
            fg="white",
            activebackground=PINK,
            activeforeground="white",
            relief="flat",
            bd=0,
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=13
        ).pack(fill="x", padx=10, pady=(5, 15))

        tk.Label(
            side,
            text="EventHub v1.0",
            bg="#30204F",
            fg="#9D8BAF",
            font=("Segoe UI", 8)
        ).pack(pady=(0, 20))

    
    def page(self, active, admin=False, title=None, transparent=False):
        if hasattr(self, "_topbar") and self._topbar:
            try:
                if self._topbar.winfo_exists():
                    self._topbar.destroy()
            except tk.TclError:
                pass

            self._topbar = None
            
        if self._sidebar is None or not self._sidebar.winfo_exists():
            self.sidebar(active, admin)
        else:
            self.sidebar(active, admin)

        if self._content is None or not self._content.winfo_exists():
            self._content = tk.Frame(self, bg=LIGHT)
            self._content.pack(side="left", fill="both", expand=True)

        for widget in self._content.winfo_children():
            widget.destroy()

        right = self._content

        if title:
            top = tk.Frame(right, bg=LIGHT)
            top.pack(fill="x", padx=35, pady=(28, 12))

            self.label(
                top, title, 24, True, PURPLE, LIGHT
            ).pack(side="left")

        return right

    # ---------------- LANDING / AUTH ----------------
    def show_landing(self):
        self.clear_all()


        # =========================
        # BACKGROUND PHOTO
        # =========================

        hero_path = hero_photo_path()
        hero_img = load_image(hero_path, 1600, 900)

        if not hero_img:
            hero = tk.Frame(self, bg=PURPLE)
            hero.pack(fill="both", expand=True)
            return

        self._photo_refs.append(hero_img)

        canvas = tk.Canvas(
            self,
            highlightthickness=0,
            bd=0
        )

        canvas.pack(
            fill="both",
            expand=True
        )

        canvas.create_image(
            0,
            0,
            image=hero_img,
            anchor="nw"
        )

        # =========================
        # EVENTHUB LOGO
        # =========================

        canvas.create_text(
            70,
            55,
            text="♡ EventHub",
            anchor="w",
            fill="white",
            font=("Segoe UI", 24, "bold")
        )

        canvas.create_text(
            72,
            92,
            text="Your Dream Event, Our Priority",
            anchor="w",
            fill="#F3EAF8",
            font=("Segoe UI", 11)
        )

        # =========================
        # MAIN HEADING
        # =========================

        canvas.create_text(
            70,
            190,
            text="Book the Perfect\nEvent, All in One Place",
            anchor="w",
            fill="white",
            font=("Segoe UI", 28, "bold")
        )

        # =========================
        # DESCRIPTION
        # =========================

        canvas.create_text(
            72,
            305,
            text=(
                "Find the best packages for your Birthday,\n"
                "Debut, or Wedding. From catering to venue,\n"
                "photography to styling — we make your\n"
                "special moments unforgettable."
            ),
            anchor="w",
            fill="white",
            font=("Segoe UI", 11)
        )

        # =========================
        # EVENT TYPES
        # =========================

        canvas.create_text(
            72,
            740,
            text="♛  Birthdays",
            anchor="w",
            fill="white",
            font=("Segoe UI", 10, "bold")
        )

        canvas.create_text(
            190,
            740,
            text="♕  Debuts",
            anchor="w",
            fill="white",
            font=("Segoe UI", 10, "bold")
        )

        canvas.create_text(
            290,
            740,
            text="♡  Weddings",
            anchor="w",
            fill="white",
            font=("Segoe UI", 10, "bold")
        )

        # =========================
        # LOGIN TYPE CARD
        # =========================

        card = tk.Frame(
            self,
            bg="white",
            width=390,
            height=300
        )

        card.place(
            relx=0.78,
            rely=0.50,
            anchor="center"
        )

        card.pack_propagate(False)

        # =========================
        # WELCOME
        # =========================

        tk.Label(
            card,
            text="Welcome to EventHub",
            bg="white",
            fg="#16213E",
            font=("Segoe UI", 20, "bold")
        ).pack(
            pady=(45, 5)
        )

        tk.Label(
            card,
            text="Choose how you want to continue",
            bg="white",
            fg="#777777",
            font=("Segoe UI", 10)
        ).pack(
            pady=(0, 30)
        )

        # =========================
        # CUSTOMER LOGIN
        # =========================

        tk.Button(
            card,
            text="Customer Login",
            command=lambda: self.login("customer"),
            bg="#8A4FFF",
            fg="white",
            activebackground="#D04F9D",
            activeforeground="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2"
        ).pack(
            fill="x",
            padx=45,
            ipady=10,
            pady=(0, 12)
        )

        # =========================
        # ADMIN LOGIN
        # =========================

        tk.Button(
            card,
            text="Admin Login",
            command=lambda: self.login("admin"),
            bg="#EDE7F5",
            fg="#30204F",
            activebackground="#DCD2E8",
            activeforeground="#30204F",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2"
        ).pack(
            fill="x",
            padx=45,
            ipady=10
        )

    # log-in area

    
    def login(self, role):
        self.clear_all()
        self.topbar("Secure Login")

        box = tk.Frame(
            self,
            bg=CARD,
            padx=50,
            pady=38,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        box.place(relx=.5, rely=.52, anchor="center")

        self.label(box, "Welcome Back!", 25, True, PURPLE, CARD).grid(
            row=0, column=0, columnspan=2, pady=(0, 5)
        )

        self.label(
            box, f"Login to your {role} account", 10, False, MUTED, CARD
        ).grid(row=1, column=0, columnspan=2, pady=(0, 25))

        self.label(box, "Username", 10, True, TEXT, CARD).grid(
            row=2, column=0, sticky="w", pady=6
        )

        u = tk.Entry(box, width=30, font=("Segoe UI", 11), relief="solid", bd=1)
        u.grid(row=2, column=1, pady=6)

        self.label(box, "Password", 10, True, TEXT, CARD).grid(
            row=3, column=0, sticky="w", pady=6
        )

        p = tk.Entry(
            box, width=30, show="●", font=("Segoe UI", 11),
            relief="solid", bd=1
        )
        p.grid(row=3, column=1, pady=6)

        def do_login():
            row = authenticate(u.get().strip(), p.get(), role)

            if row:
                self.user = row

                if role == "admin":
                    self.admin_dashboard()
                else:
                    self.customer_dashboard()
            else:
                messagebox.showerror(
                    "Login Failed", "Invalid login details."
                )

        self.button(box, "Login", do_login, True, 24).grid(
            row=4, column=0, columnspan=2, pady=20
        )

        if role == "customer":
            reg = tk.Frame(box, bg=CARD)
            reg.grid(row=5, column=0, columnspan=2, pady=(0, 8))

            self.label(
                reg, "Don't have an account yet?", 9, False, MUTED, CARD
            ).pack(side="left")

            tk.Button(
                reg,
                text="Register",
                command=self.register,
                bg=CARD,
                fg=PINK,
                relief="flat",
                bd=0,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2"
            ).pack(side="left", padx=4)

        tk.Button(
            box,
            text="← Back",
            command=self.show_landing,
            bg=CARD,
            fg=PURPLE,
            relief="flat"
        ).grid(row=6, column=0, columnspan=2)


    def register(self):
        self.clear_all()
        self.topbar("Create Account")

        box = tk.Frame(
            self, bg=CARD, padx=42, pady=30,
            highlightbackground=BORDER, highlightthickness=1
        )
        box.place(relx=.5, rely=.52, anchor="center")

        self.label(box, "Create Your Account", 24, True, PURPLE, CARD).grid(
            row=0, column=0, columnspan=2, pady=(0, 5)
        )
        self.label(
            box, "Start planning your dream event today!",
            10, False, MUTED, CARD
        ).grid(row=1, column=0, columnspan=2, pady=(0, 18))

        fields = {}
        items = [
            ("Full Name", ""),
            ("Username", ""),
            ("Email Address", ""),
            ("Contact Number", ""),
            ("Password", ""),
            ("Confirm Password", "")
        ]
        for i, (name, default) in enumerate(items, start=2):
            self.label(box, name, 9, True, TEXT, CARD).grid(
                row=i, column=0, sticky="w", padx=(0, 18), pady=6
            )
            ent = tk.Entry(
                box, width=30, font=("Segoe UI", 10),
                relief="solid", bd=1, show="●" if "Password" in name else ""
            )
            ent.insert(0, default)
            ent.grid(row=i, column=1, pady=6)
            fields[name] = ent

        def do_register():
            if fields["Password"].get() != fields["Confirm Password"].get():
                messagebox.showerror("Registration", "Passwords do not match.")
                return
            ok, msg = register_customer(
                fields["Username"].get(), fields["Password"].get(),
                fields["Full Name"].get(), fields["Email Address"].get(),
                fields["Contact Number"].get()
            )
            if not ok:
                messagebox.showerror("Registration", msg)
                return
            self.user = (fields["Username"].get().strip(), "customer")
            messagebox.showinfo("Registration", "Account created! Welcome to EventHub.")
            self.customer_dashboard()

        self.button(box, "Register", do_register, True, 24).grid(
            row=8, column=0, columnspan=2, pady=18
        )
        tk.Button(
            box, text="Already have an account? Login",
            command=lambda: self.login("customer"),
            bg=CARD, fg=PINK, relief="flat", bd=0,
            font=("Segoe UI", 9, "bold"), cursor="hand2"
        ).grid(row=9, column=0, columnspan=2)

    def logout(self):
        self.user = None
        self.event_type = "Birthday"
        self.booking = {}
        self.selected = {}
        self.show_landing()

    # ---------------- CUSTOMER ----------------

    def customer_dashboard(self):
        page = self.page("Dashboard", False, None)

        # =========================
        # DASHBOARD CANVAS
        # =========================

        dashboard = tk.Canvas(
            page,
            highlightthickness=0,
            bd=0
        )

        dashboard.pack(
            side="left",
            fill="both",
            expand=True
        )

        self._dashboard_canvas = dashboard

        bg_img = load_faded_image(
            hero_photo_path(),
            1600,
            900,
            0.68
        )

        if bg_img:
            self._photo_refs.append(bg_img)
            dashboard.create_image(
                0,
                0,
                image=bg_img,
                anchor="nw"
            )

        # =========================
        # GREETING — CANVAS TEXT
        # No Label background is used.
        # =========================

        current_hour = datetime.now().hour

        if 5 <= current_hour < 12:
            greeting = "Good Morning"
        elif 12 <= current_hour < 18:
            greeting = "Good Afternoon"
        else:
            greeting = "Good Evening"

        dashboard.create_text(
            35,
            55,
            text=greeting + ", " + self.user[0] + "! 👋",
            anchor="w",
            fill=PURPLE,
            font=("Segoe UI", 24, "bold")
        )

        dashboard.create_text(
            35,
            96,
            text="Here’s what’s happening with your events.",
            anchor="w",
            fill=MUTED,
            font=("Segoe UI", 11)
        )

        # =========================
        # DATABASE STATISTICS
        # =========================

        con = connect()

        total = con.execute(
            "SELECT COUNT(*) FROM reservations WHERE customer=?",
            (self.user[0],)
        ).fetchone()[0]

        pending = con.execute(
            "SELECT COUNT(*) FROM reservations "
            "WHERE customer=? AND status='Pending'",
            (self.user[0],)
        ).fetchone()[0]

        approved = con.execute(
            "SELECT COUNT(*) FROM reservations "
            "WHERE customer=? AND status='Approved'",
            (self.user[0],)
        ).fetchone()[0]

        
        spent = con.execute(
            """
            SELECT COALESCE(SUM(p.amount), 0)
            FROM payments p
            JOIN reservations r
                ON r.id = p.reservation_id
            WHERE r.customer = ?
            AND p.status = 'Paid'
            """,
            (self.user[0],)
        ).fetchone()[0]

        reservation = con.execute(
            """
            SELECT
                id, event_type, event_date, guests,
                catering_id, photography_id, venue_id,
                styling_id, total, status
            FROM reservations
            WHERE customer = ?
            AND date(event_date) >= date('now')
            AND status = 'Approved'
            ORDER BY date(event_date) ASC, id ASC
            LIMIT 1
            """,
            (self.user[0],)
        ).fetchone()

        package_names = {}

        if reservation:
            package_ids = {
                "Catering": reservation[4],
                "Photography": reservation[5],
                "Venue": reservation[6],
                "Event Styling": reservation[7]
            }

            for label_name, package_id in package_ids.items():
                if package_id:
                    result = con.execute(
                        "SELECT name FROM packages WHERE id = ?",
                        (package_id,)
                    ).fetchone()
                    package_names[label_name] = (
                        result[0] if result else "Not selected"
                    )
                else:
                    package_names[label_name] = "Not selected"

        con.close()

        # =========================
        # STATISTIC CARDS
        # =========================

        stat_data = [
            ("Total Bookings", total, PURPLE2),
            ("Upcoming Events", approved, GREEN),
            ("Pending Reservations", pending, ORANGE),
            ("Total Spent", money(spent), PINK)
        ]

        stat_windows = []

        for title, value, accent in stat_data:
            card = tk.Frame(
                dashboard,
                bg=CARD,
                padx=22,
                pady=20,
                highlightbackground=BORDER,
                highlightthickness=1
            )

            self.label(
                card, title, 9, False, MUTED, CARD
            ).pack(anchor="w")

            self.label(
                card, str(value), 22, True, accent, CARD
            ).pack(anchor="w", pady=6)

            stat_windows.append(
                dashboard.create_window(
                    0, 0,
                    window=card,
                    anchor="nw",
                    width=250,
                    height=105
                )
            )

        # =========================
        # UPCOMING RESERVATION TITLE
        # =========================

        dashboard.create_text(
            35,
            325,
            text="Upcoming Reservation",
            anchor="w",
            fill=PURPLE,
            font=("Segoe UI", 18, "bold")
        )

        # =========================
        # RESERVATION CARD
        # =========================

        reservation_window = None

        if reservation:
            (
                reservation_id,
                event_type,
                event_date,
                guests,
                catering_id,
                photography_id,
                venue_id,
                styling_id,
                total,
                status
            ) = reservation

            card = tk.Frame(
                dashboard,
                bg=CARD,
                padx=25,
                pady=22,
                highlightbackground=BORDER,
                highlightthickness=1
            )

            top = tk.Frame(card, bg=CARD)
            top.pack(fill="x")

            self.label(
                top,
                "💍 " + event_type,
                18,
                True,
                PURPLE,
                CARD
            ).pack(side="left")

            status_color = (
                GREEN
                if status.lower() == "approved"
                else ORANGE
            )

            self.label(
                top,
                status.upper(),
                9,
                True,
                status_color,
                CARD
            ).pack(side="right")

            self.label(
                card, str(event_date), 11, False, MUTED, CARD
            ).pack(anchor="w", pady=(8, 2))

            self.label(
                card, f"{guests} Guests", 10, False, TEXT, CARD
            ).pack(anchor="w", pady=(0, 12))

            self.label(
                card, f"Catering: {package_names['Catering']}",
                10, False, TEXT, CARD
            ).pack(anchor="w", pady=2)

            self.label(
                card, f"Photography: {package_names['Photography']}",
                10, False, TEXT, CARD
            ).pack(anchor="w", pady=2)

            self.label(
                card, f"Venue: {package_names['Venue']}",
                10, False, TEXT, CARD
            ).pack(anchor="w", pady=2)

            self.label(
                card, f"Event Styling: {package_names['Event Styling']}",
                10, False, TEXT, CARD
            ).pack(anchor="w", pady=2)

            bottom = tk.Frame(card, bg=CARD)
            bottom.pack(fill="x", pady=(15, 0))

            self.label(
                bottom, f"Total: {money(total)}",
                12, True, TEXT, CARD
            ).pack(side="left")

            self.button(
                bottom,
                "View Reservation →",
                self.my_reservations,
                True
            ).pack(side="right")

            reservation_window = dashboard.create_window(
                0, 0,
                window=card,
                anchor="nw",
                width=900,
                height=360
            )

        else:
            card = tk.Frame(
                dashboard,
                bg=CARD,
                padx=25,
                pady=30,
                highlightbackground=BORDER,
                highlightthickness=1
            )

            self.label(
                card,
                "No upcoming reservations",
                15, True, PURPLE, CARD
            ).pack(anchor="w")

            self.label(
                card,
                "You don't have any upcoming event yet.",
                10, False, MUTED, CARD
            ).pack(anchor="w", pady=8)

            self.button(
                card,
                "Browse Events",
                self.choose_event,
                True
            ).pack(pady=(8, 0))

            reservation_window = dashboard.create_window(
                0, 0,
                window=card,
                anchor="nw",
                width=900,
                height=180
            )

        # =========================
        # RESPONSIVE WINDOW POSITIONS
        # =========================

        def resize_dashboard(event=None):
            width = max(dashboard.winfo_width(), 1000)

            left = 35
            gap = 14
            available = width - (left * 2) - (gap * 3)
            card_width = max(210, int(available / 4))

            for index, window_id in enumerate(stat_windows):
                dashboard.coords(
                    window_id,
                    left + index * (card_width + gap),
                    180
                )
                dashboard.itemconfigure(
                    window_id,
                    width=card_width,
                    height=105
                )

            if reservation_window is not None:
                dashboard.coords(
                    reservation_window,
                    35,
                    360
                )
                dashboard.itemconfigure(
                    reservation_window,
                    width=max(300, width - 70)
                )
            dashboard.configure(
                scrollregion=dashboard.bbox("all")
            )

        def dashboard_mousewheel(event):
            try:
                if not dashboard.winfo_exists():
                    return

                dashboard.yview_scroll(
                    int(-1 * (event.delta / 120)),
                    "units"
                )
            except (tk.TclError, AttributeError):
                return


        def enable_dashboard_scroll(event):
            dashboard.bind_all(
                "<MouseWheel>",
                dashboard_mousewheel
            )


        def disable_dashboard_scroll(event):
            dashboard.unbind_all(
                "<MouseWheel>"
            )


        dashboard.bind_all("<MouseWheel>", dashboard_mousewheel)
        

        dashboard.bind("<Configure>", resize_dashboard)
        dashboard.after(50, resize_dashboard)

    def choose_event(self):
        page = self.page("Browse Events", False, None)

        # SCROLLABLE PAGE
        scroll_area = tk.Frame(page, bg=LIGHT)
        scroll_area.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            scroll_area,
            bg=LIGHT,
            highlightthickness=0
        )
        scrollbar = tk.Scrollbar(
            scroll_area,
            orient="vertical",
            command=canvas.yview
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        content = tk.Frame(canvas, bg=LIGHT)
        window_id = canvas.create_window(
            (0, 0),
            window=content,
            anchor="nw"
        )

        def update_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def update_content_width(event):
            canvas.itemconfigure(window_id, width=event.width)

        content.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", update_content_width)

        def mousewheel(event):
            canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )

        def bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", mousewheel)

        def unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", bind_mousewheel)
        canvas.bind("<Leave>", unbind_mousewheel)

        # HERO BANNER
        hero = tk.Frame(content, bg=LIGHT, height=275)
        hero.pack(fill="x", padx=18, pady=(15, 10))
        hero.pack_propagate(False)

        hero_img = load_image(hero1_photo_path(), 1500, 275)

        if hero_img:
            self._photo_refs.append(hero_img)

            hero_canvas = tk.Canvas(
                hero,
                height=275,
                highlightthickness=0,
                bd=0
            )
            hero_canvas.pack(fill="both", expand=True)

            hero_canvas.create_image(
                0, 0,
                image=hero_img,
                anchor="nw"
            )

            hero_canvas.create_text(
                35, 55,
                text="WELCOME TO EVENTHUB ♥",
                font=("Arial", 10, "bold"),
                fill="#F6A4DE",
                anchor="w"
            )

            hero_canvas.create_text(
                35, 125,
                text="Make Your Special\nMoment Unforgettable",
                font=("Arial", 25, "bold"),
                fill="white",
                anchor="w",
                justify="left"
            )

            hero_canvas.create_text(
                35, 230,
                text="Choose from our exclusive event packages and\n"
                    "let us bring your dream celebration to life.",
                font=("Arial", 10),
                fill="white",
                anchor="w",
                justify="left"
            )
        else:
            self.label(
                hero, "Make Your Special Moment Unforgettable",
                20, True, PURPLE, LIGHT
            ).pack(padx=25, pady=50, anchor="w")

        # CHOOSE YOUR EVENT
        heading = tk.Frame(content, bg=LIGHT)
        heading.pack(fill="x", padx=25, pady=(8, 10))

        self.label(
            heading, "✦  CHOOSE YOUR EVENT",
            10, True, PURPLE, LIGHT
        ).pack(anchor="w")

        self.label(
            heading,
            "Select the type of celebration you are planning.",
            19, True, PURPLE, LIGHT
        ).pack(anchor="w", pady=(8, 0))

        # EVENT CARDS
        
        row = tk.Frame(content, bg=LIGHT)
        row.pack(fill="x", padx=18, pady=(5, 18))

        row.grid_columnconfigure(0, weight=1, uniform="event_cards")
        row.grid_columnconfigure(1, weight=1, uniform="event_cards")
        row.grid_columnconfigure(2, weight=1, uniform="event_cards")


        descriptions = {
            "Birthday": "Make your special day memorable\nwith our beautiful birthday packages.",
            "Debut": "Celebrate your 18th in style\nwith our elegant debut packages.",
            "Wedding": "Begin your forever together\nwith our romantic wedding packages."
        }

        for e, icon in [
            ("Birthday", "🎂"),
            ("Debut", "🎀"),
            ("Wedding", "💍")
        ]:
            card = tk.Frame(
                row,
                bg=CARD,
                padx=15,
                pady=15,
                highlightbackground=BORDER,
                highlightthickness=1
            )
            card.grid(
                row=0,
                column=["Birthday", "Debut", "Wedding"].index(e),
                sticky="nsew",
                padx=7
            )


            img = load_image(event_photo_path(e), 350, 175)

            if img:
                self._photo_refs.append(img)
                tk.Label(
                    card,
                    image=img,
                    bg=CARD,
                    bd=0
                ).pack(fill="x", pady=(0, 12))
            else:
                self.label(
                    card, icon, 35, False, PURPLE, CARD
                ).pack(pady=20)

            self.label(
                card, f"{icon}  {e}",
                18, True, PURPLE, CARD
            ).pack(anchor="w", pady=(5, 8))

            self.label(
                card, descriptions[e],
                9, False, MUTED, CARD,
                justify="left"
            ).pack(anchor="w", pady=(0, 12))

            self.button(
                card,
                "Select  ➜",
                lambda e=e: self.start_booking(e),
                True
            ).pack(fill="x", padx=10, pady=(5, 8))

        
    def start_booking(self, event):
        self.event_type = event
        self.selected = {}
        self.choose_date()

    def choose_date(self):

        from datetime import date, datetime, timedelta

        # =========================
        # MAIN PAGE
        # =========================

        page = self.page(
            "",
            False,
            ""
        )

        # =========================
        # SCROLLABLE MAIN AREA
        # =========================

        canvas = tk.Canvas(
            page,
            bg=LIGHT,
            highlightthickness=0,
            bd=0
        )

        canvas.pack(
            fill="both",
            expand=True
        )

        scroll_frame = tk.Frame(
            canvas,
            bg=LIGHT
        )

        window_id = canvas.create_window(
            (0, 0),
            window=scroll_frame,
            anchor="nw"
        )

        def update_scroll(event=None):

            scroll_frame.update_idletasks()

            canvas.configure(
                scrollregion=canvas.bbox("all")
            )

        def resize_scroll(event):

            canvas.itemconfigure(
                window_id,
                width=event.width
            )

        scroll_frame.bind(
            "<Configure>",
            update_scroll
        )

        canvas.bind(
            "<Configure>",
            resize_scroll
        )

        # =========================
        # MOUSE WHEEL
        # =========================

        def mousewheel(event):

            canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )

        def enable_scroll(event):

            canvas.bind_all(
                "<MouseWheel>",
                mousewheel
            )

        def disable_scroll(event):

            canvas.unbind_all(
                "<MouseWheel>"
            )

        canvas.bind(
            "<Enter>",
            enable_scroll
        )

        canvas.bind(
            "<Leave>",
            disable_scroll
        )

        # =========================
        # HEADER
        # =========================

        header = tk.Frame(
            scroll_frame,
            bg=LIGHT
        )

        header.pack(
            fill="x",
            padx=35,
            pady=(20, 12)
        )

        back_btn = tk.Button(
            header,
            text="←",
            command=self.choose_event,
            bg="#EDE4FA",
            fg=PURPLE,
            activebackground="#DCCAF3",
            activeforeground=PURPLE,
            relief="flat",
            bd=0,
            font=("Segoe UI", 20, "bold"),
            width=2,
            height=1
        )

        back_btn.pack(
            side="left",
            padx=(0, 12)
        )

        title_box = tk.Frame(
            header,
            bg=LIGHT
        )

        title_box.pack(
            side="left"
        )

        self.label(
            title_box,
            "Create Your Booking",
            25,
            True,
            PURPLE,
            LIGHT
        ).pack(
            anchor="w"
        )

        self.label(
            title_box,
            "Fill in the details below to reserve your event.",
            10,
            False,
            MUTED,
            LIGHT
        ).pack(
            anchor="w",
            pady=(2, 0)
        )

        self.label(
            header,
            "Make\nBeautiful Events\n♡ Happen",
            13,
            True,
            PURPLE2,
            LIGHT,
            justify="right"
        ).pack(
            side="right",
            padx=(20, 5)
        )

        # =========================
        # MAIN TWO-COLUMN AREA
        # =========================

        main = tk.Frame(
            scroll_frame,
            bg=LIGHT
        )

        main.pack(
            fill="both",
            expand=True,
            padx=35,
            pady=(8, 30)
        )

        # =========================
        # LEFT COLUMN
        # =========================

        left = tk.Frame(
            main,
            bg=LIGHT
        )

        left.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 10)
        )

        # =========================
        # EVENT BANNER
        # =========================

        banner = tk.Canvas(
            left,
            bg=PURPLE,
            height=180,
            highlightthickness=0,
            bd=0
        )

        banner.pack(
            fill="x",
            pady=(0, 15)
        )

        banner_img = load_image(
            event_photo_path(self.event_type),
            1000,
            300
        )

        if banner_img:

            self._photo_refs.append(
                banner_img
            )

            banner.create_image(
                0,
                0,
                image=banner_img,
                anchor="nw"
            )


        event_icon = {
            "Birthday": "🎂",
            "Debut": "🎀",
            "Wedding": "💍"
        }.get(
            self.event_type,
            "🎉"
        )

        banner.create_text(
            60,
            90,
            text=event_icon,
            fill=PURPLE,
            font=("Segoe UI Emoji", 25),
            anchor="center"
        )

        banner.create_text(
            135,
            45,
            text=f"{self.event_type} Event",
            fill="white",
            font=("Segoe UI", 22, "bold"),
            anchor="nw"
        )

        banner.create_text(
            135,
            82,
            text=EVENTS.get(
                self.event_type,
                "Celebrate your special moments."
            ),
            fill="white",
            font=("Segoe UI", 10),
            anchor="nw",
            width=320
        )

        # =========================
        # EVENT DETAILS CARD
        # =========================

        details_card = tk.Frame(
            left,
            bg=CARD,
            padx=28,
            pady=25,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        details_card.pack(
            fill="x"
        )

        self.label(
            details_card,
            "▣  Event Details",
            16,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w"
        )

        self.label(
            details_card,
            "Please provide the following information.",
            9,
            False,
            MUTED,
            CARD
        ).pack(
            anchor="w",
            pady=(3, 20)
        )

        fields = {}

        # =========================
        # FIELD HELPER
        # =========================

        def create_field(
            parent,
            label_text,
            default_value,
            width=None
        ):

            wrapper = tk.Frame(
                parent,
                bg=CARD
            )

            if width:
                wrapper.configure(
                    width=width
                )

            wrapper.pack(
                fill="x",
                expand=True
            )

            self.label(
                wrapper,
                label_text,
                9,
                True,
                PURPLE,
                CARD
            ).pack(
                anchor="w",
                pady=(0, 7)
            )

            input_box = tk.Frame(
                wrapper,
                bg="#FCFAFF",
                highlightbackground="#DCCAF5",
                highlightthickness=1
            )

            input_box.pack(
                fill="x"
            )

            entry = tk.Entry(
                input_box,
                bg="#FCFAFF",
                fg=TEXT,
                relief="flat",
                bd=0,
                font=("Segoe UI", 10),
                insertbackground=PURPLE
            )

            entry.pack(
                fill="x",
                padx=14,
                pady=11
            )

            entry.insert(
                0,
                default_value
            )

            fields[label_text] = entry

        # =========================
        # DATE + GUESTS
        # =========================

        row_one = tk.Frame(
            details_card,
            bg=CARD
        )

        row_one.pack(
            fill="x"
        )

        create_field(
            row_one,
            "📅  Event Date",
            (
                date.today()
                + timedelta(days=7)
            ).isoformat()
        )

        create_field(
            row_one,
            "👥  Number of Guests",
            "50"
        )

        # Make both fields same row
        children = row_one.winfo_children()

        if len(children) >= 2:

            children[0].pack_configure(
                side="left",
                fill="x",
                expand=True,
                padx=(0, 8)
            )

            children[1].pack_configure(
                side="left",
                fill="x",
                expand=True,
                padx=(8, 0)
            )

        # =========================
        # CUSTOMER NAME
        # =========================

        customer_wrapper = tk.Frame(
            details_card,
            bg=CARD
        )

        customer_wrapper.pack(
            fill="x",
            pady=(18, 0)
        )

        self.label(
            customer_wrapper,
            "👤  Customer Name",
            9,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w",
            pady=(0, 7)
        )

        customer_box = tk.Frame(
            customer_wrapper,
            bg="#FCFAFF",
            highlightbackground="#DCCAF5",
            highlightthickness=1
        )

        customer_box.pack(
            fill="x"
        )

        customer_entry = tk.Entry(
            customer_box,
            bg="#FCFAFF",
            fg=TEXT,
            relief="flat",
            bd=0,
            font=("Segoe UI", 10),
            insertbackground=PURPLE
        )

        customer_entry.pack(
            fill="x",
            padx=14,
            pady=11
        )

        customer_entry.insert(
            0,
            self.user[0]
        )

        fields["Customer Name"] = customer_entry

        # =========================
        # CONTACT NUMBER
        # =========================

        contact_wrapper = tk.Frame(
            details_card,
            bg=CARD
        )

        contact_wrapper.pack(
            fill="x",
            pady=(18, 0)
        )

        self.label(
            contact_wrapper,
            "☎  Contact Number",
            9,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w",
            pady=(0, 7)
        )

        contact_box = tk.Frame(
            contact_wrapper,
            bg="#FCFAFF",
            highlightbackground="#DCCAF5",
            highlightthickness=1
        )

        contact_box.pack(
            fill="x"
        )

        contact_entry = tk.Entry(
            contact_box,
            bg="#FCFAFF",
            fg=TEXT,
            relief="flat",
            bd=0,
            font=("Segoe UI", 10),
            insertbackground=PURPLE
        )

        contact_entry.pack(
            fill="x",
            padx=14,
            pady=11
        )

        fields["Contact Number"] = contact_entry

        # =========================
        # RIGHT COLUMN
        # =========================

        right = tk.Frame(
            main,
            bg=CARD,
            padx=24,
            pady=25,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        right.pack(
            side="right",
            fill="both",
            padx=(10, 0)
        )

        self.label(
            right,
            "▤  Booking Summary",
            16,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w"
        )

        # =========================
        # SUMMARY EVENT
        # =========================

        summary_top = tk.Frame(
            right,
            bg=CARD
        )

        summary_top.pack(
            fill="x",
            pady=(18, 12)
        )

        summary_img = load_image(
            event_photo_path(self.event_type),
            150,
            110
        )

        if summary_img:

            self._photo_refs.append(
                summary_img
            )

            tk.Label(
                summary_top,
                image=summary_img,
                bg=CARD
            ).pack(
                side="left",
                padx=(0, 12)
            )

        summary_info = tk.Frame(
            summary_top,
            bg=CARD
        )

        summary_info.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.label(
            summary_info,
            f"{self.event_type} Event",
            11,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w"
        )

        self.label(
            summary_info,
            "Special Occasion",
            8,
            True,
            PURPLE2,
            "#EFE4FF",
            padx=8,
            pady=4
        ).pack(
            anchor="w",
            pady=(5, 8)
        )

        self.label(
            summary_info,
            "📅  " + fields["📅  Event Date"].get(),
            9,
            False,
            MUTED,
            CARD
        ).pack(
            anchor="w",
            pady=2
        )

        self.label(
            summary_info,
            "👥  " + fields["👥  Number of Guests"].get() + " guests",
            9,
            False,
            MUTED,
            CARD
        ).pack(
            anchor="w",
            pady=2
        )

        tk.Frame(
            right,
            bg=BORDER,
            height=1
        ).pack(
            fill="x",
            pady=15
        )

        # =========================
        # WHAT'S NEXT
        # =========================

        self.label(
            right,
            "What's Next?",
            14,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w",
            pady=(0, 15)
        )

        steps = [
            (
                "1",
                "Event Details",
                "Fill in your basic information."
            ),
            (
                "2",
                "Choose Packages",
                "Select your preferred packages."
            ),
            (
                "3",
                "Review & Confirm",
                "Complete your reservation."
            )
        ]

        for number, title, description in steps:

            step = tk.Frame(
                right,
                bg=CARD
            )

            step.pack(
                fill="x",
                pady=7
            )

            circle = tk.Label(
                step,
                text=number,
                bg="#E7D8FA",
                fg=PURPLE,
                font=("Segoe UI", 10, "bold"),
                width=3,
                height=1
            )

            circle.pack(
                side="left",
                padx=(0, 12)
            )

            step_text = tk.Frame(
                step,
                bg=CARD
            )

            step_text.pack(
                side="left",
                fill="x",
                expand=True
            )

            self.label(
                step_text,
                title,
                9,
                True,
                PURPLE,
                CARD
            ).pack(
                anchor="w"
            )

            self.label(
                step_text,
                description,
                8,
                False,
                MUTED,
                CARD,
                wraplength=230
            ).pack(
                anchor="w",
                pady=(2, 0)
            )

        # =========================
        # DECORATIVE MESSAGE
        # =========================

        tk.Frame(
            right,
            bg=BORDER,
            height=1
        ).pack(
            fill="x",
            pady=20
        )

        self.label(
            right,
            "Let's make\n"
            "your event special!",
            14,
            True,
            PURPLE2,
            CARD,
            justify="center"
        ).pack(
            pady=8
        )

        self.label(
            right,
            "♥",
            18,
            True,
            PINK,
            CARD
        ).pack()

        # =========================
        # CONTINUE BUTTON
        # =========================

        def continue_booking():

            try:

                event_date = (
                    fields["📅  Event Date"]
                    .get()
                    .strip()
                )

                guests = int(
                    fields["👥  Number of Guests"]
                    .get()
                    .strip()
                )

                selected_date = datetime.strptime(
                    event_date,
                    "%Y-%m-%d"
                ).date()

                if selected_date < date.today():

                    raise ValueError

                if guests <= 0:

                    raise ValueError

            except:

                messagebox.showerror(
                    "Invalid Details",
                    "Please enter a valid future date and guest count."
                )

                return

            customer_name = (
                fields["Customer Name"]
                .get()
                .strip()
            )

            contact = (
                fields["Contact Number"]
                .get()
                .strip()
            )

            if not customer_name:

                messagebox.showerror(
                    "Missing Information",
                    "Please enter the customer name."
                )

                return

            self.booking = {
                "date": event_date,
                "guests": guests,
                "name": customer_name,
                "contact": contact
            }

            self.package_catalog()

        self.button(
            details_card,
            "Continue to Packages  →",
            continue_booking,
            True
        ).pack(
            anchor="e",
            pady=(18, 0)
        )

        # =========================
        # INITIAL SCROLL SETUP
        # =========================

        scroll_frame.update_idletasks()

        canvas.configure(
            scrollregion=canvas.bbox("all")
        )

    def package_catalog(self, selected_category="Catering"):
        page = self.page(
            "Packages",
            False,
            "Browse Packages"
        )

        toolbar = tk.Frame(page, bg=LIGHT)
        toolbar.pack(fill="x", padx=30, pady=(0, 10))

        self.label(
            toolbar,
            f"{self.event_type} • {self.booking.get('date', 'Choose an event first')}",
            11,
            True,
            PURPLE,
            LIGHT
        ).pack(side="left")

        self.button(
            toolbar,
            "Review Booking",
            self.review_booking,
            True
        ).pack(side="right")

        tabs = tk.Frame(page, bg=LIGHT)
        tabs.pack(fill="x", padx=30)

        content = tk.Frame(page, bg=LIGHT)
        content.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=10
        )

        canvas = tk.Canvas(
            content,
            bg=LIGHT,
            highlightthickness=0
        )

        inner = tk.Frame(
            canvas,
            bg=LIGHT
        )

        window_id = canvas.create_window(
            (0, 0),
            window=inner,
            anchor="nw"
        )

        canvas.pack(
            side="left",
            fill="both",
            expand=True
        )


        def update_scroll(event=None):
            inner.update_idletasks()
            canvas.configure(
                scrollregion=canvas.bbox("all")
            )

        def resize_inner(event):
            canvas.itemconfig(
                window_id,
                width=max(event.width, 1)
            )

        inner.bind(
            "<Configure>",
            update_scroll
        )

        canvas.bind(
            "<Configure>",
            resize_inner
        )

        def mousewheel(event):
            canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )

        canvas.bind_all(
            "<MouseWheel>",
            mousewheel
        )
        
        category_pages = {}
        current_category = None
        
        def load(category):
            nonlocal current_category

            if category in category_pages:
                if current_category is not None:
                    category_pages[current_category].grid_remove()

                category_pages[category].grid()
                current_category = category
                update_scroll()
                return

            if current_category is not None:
                category_pages[current_category].grid_remove()

            category_frame = tk.Frame(inner, bg=LIGHT)
            category_frame.grid(row=0, column=0, sticky="nsew")

            inner.grid_columnconfigure(0, weight=1)
            category_pages[category] = category_frame
            current_category = category

            header = tk.Frame(category_frame, bg=LIGHT)
            header.grid(
                row=0,
                column=0,
                columnspan=3,
                sticky="ew",
                pady=(10, 15)
            )

            
            header.grid_columnconfigure(0, weight=1)
            header.grid_columnconfigure(1, weight=0, minsize=340)

            category_frame.grid_columnconfigure(0, weight=1, uniform="cards")
            category_frame.grid_columnconfigure(1, weight=1, uniform="cards")
            category_frame.grid_columnconfigure(2, weight=1, uniform="cards")


            search_var = tk.StringVar()
            card_items = []

            con = connect()
            try:
                rows = con.execute(
                    """
                    SELECT id, category, name, event_type, provider,
                           description, inclusions, menu, price, image_path
                    FROM packages
                    WHERE category = ? AND event_type = ?
                    ORDER BY id
                    """,
                    (category, self.event_type)
                ).fetchall()
            finally:
                con.close()

            self.label(
                header,
                f"{category} — {len(rows)} Packages",
                18, True, PURPLE, LIGHT
            ).grid(row=0, column=0, sticky="w")

            
            search_frame = tk.Frame(
                header,
                bg="white",
                highlightbackground="#E4D8F8",
                highlightthickness=1,
                width=320,
                height=44
            )

            search_frame.grid(
                row=0,
                column=1,
                sticky="e",
                padx=(15, 0)
            )

            search_frame.grid_propagate(False)


            tk.Label(
                search_frame,
                text="⌕",
                font=("Arial", 17),
                bg="white",
                fg="#6946A5"
            ).pack(side="left", padx=(12, 5))

            search_entry = tk.Entry(
                search_frame,
                textvariable=search_var,
                font=("Arial", 11),
                width=25,
                relief="flat",
                bd=0,
                bg="white",
                fg=TEXT,
                insertbackground=PURPLE
            )
            search_entry.pack(side="left", ipady=9, padx=(0, 12))

            placeholder = "Search packages..."

            def add_placeholder(event=None):
                if not search_var.get().strip():
                    search_var.set(placeholder)
                    search_entry.configure(fg="#A397BD")

            def remove_placeholder(event=None):
                if search_var.get() == placeholder:
                    search_var.set("")
                    search_entry.configure(fg=TEXT)

            search_entry.bind("<FocusIn>", remove_placeholder)
            search_entry.bind("<FocusOut>", add_placeholder)
            add_placeholder()

            self.label(
                category_frame,
                "Loading packages...",
                10, False, MUTED, LIGHT
            ).grid(row=1, column=0, sticky="w", padx=8, pady=8)

            try:
                unavailable_ids = get_unavailable_package_ids(
                    self.booking["date"]
                )
            except Exception as e:
                messagebox.showerror(
                    "Availability Error",
                    f"Could not check package availability:\n{e}"
                )
                category_pages.pop(category, None)
                category_frame.destroy()
                current_category = None
                return

            def filter_packages(*args):
                query = search_var.get().strip().lower()
                if query == placeholder.lower():
                    query = ""

                visible_cards = [
                    item for item in card_items
                    if query in item[3]
                ]

                for card, _, _, _ in card_items:
                    card.grid_remove()

                for index, (card, _, _, _) in enumerate(visible_cards):
                    card.grid(
                        row=(index // 3) + 2,
                        column=index % 3,
                        padx=8,
                        pady=8,
                        sticky="nsew"
                    )

                category_frame.update_idletasks()
                canvas.configure(scrollregion=canvas.bbox("all"))

            search_var.trace_add("write", filter_packages)

            index = 0
            loading_label = category_frame.winfo_children()[-1]

            def create_batch():
                nonlocal index

                if not category_frame.winfo_exists():
                    return

                end = min(index + 3, len(rows))

                while index < end:
                    r = rows[index]
                    pid, cat, name, event, provider, desc, inclusions, menu, price, image_path = r
                    package_number = index + 1
                    index += 1

                    card = tk.Frame(
                        category_frame,
                        bg=CARD,
                        padx=18,
                        pady=18,
                        highlightbackground=BORDER,
                        highlightthickness=1
                    )

                    card_items.append((
                        card, 0, 0,
                        f"{name} {provider} {desc}".lower()
                    ))

                    card.configure(cursor="hand2")
                    card.bind(
                        "<Button-1>",
                        lambda e, p=pid, c=cat: self.package_details(p, c)
                    )

                    self.label(
                        card, f"PACKAGE {package_number}",
                        9, True, PINK, CARD
                    ).pack(anchor="w", pady=(0, 8))

                    photo_path = image_path or package_photo_path(
                        cat, pid, name, event
                    )

                    img = load_image(photo_path, 245, 125)

                    if img:
                        self._photo_refs.append(img)
                        photo_label = tk.Label(
                            card, image=img, bg=CARD, cursor="hand2"
                        )
                        photo_label.pack(fill="x", pady=(0, 8))
                        photo_label.bind(
                            "<Button-1>",
                            lambda e, p=pid, c=cat: self.package_details(p, c)
                        )

                    self.label(
                        card, name, 12, True, PURPLE, CARD,
                        wraplength=240
                    ).pack(anchor="w", pady=(7, 3))

                    self.label(
                        card, provider, 9, False, MUTED, CARD
                    ).pack(anchor="w")

                    self.label(
                        card, desc, 9, False, TEXT, CARD,
                        wraplength=245, justify="left"
                    ).pack(anchor="w", pady=8)

                    self.label(
                        card, money(price), 15, True, TEXT, CARD
                    ).pack(anchor="w")

                    if pid in unavailable_ids:
                        self.label(
                            card, "UNAVAILABLE",
                            10, True, RED, CARD
                        ).pack(anchor="e", pady=(8, 0))
                    else:
                        def select(
                            package_id=pid,
                            package_key=dict(CATEGORIES)[category],
                            package_name=name
                        ):
                            if not is_available(
                                package_id, self.booking["date"]
                            ):
                                messagebox.showerror(
                                    "Unavailable",
                                    f"{package_name} is already booked on "
                                    f"{self.booking['date']}."
                                )
                                return

                            self.selected[package_key] = package_id
                            messagebox.showinfo(
                                "Selected",
                                f"{package_name} added to your booking."
                            )

                        self.button(
                            card, "Select Package", select, True
                        ).pack(anchor="e", pady=(8, 0))

                if loading_label.winfo_exists():
                    loading_label.destroy()

                for col in range(3):
                    category_frame.grid_columnconfigure(col, weight=1)

                for card_index, (card, _, _, _) in enumerate(card_items):
                    card.grid(
                        row=(card_index // 3) + 2,
                        column=card_index % 3,
                        padx=8,
                        pady=8,
                        sticky="nsew"
                    )

                canvas.configure(scrollregion=canvas.bbox("all"))

                if index < len(rows):
                    self.after(1, create_batch)

            self.after(1, create_batch)


        for category, key in CATEGORIES:

            self.button(
                tabs,
                category,
                lambda c=category: load(c),
                False
            ).pack(
                side="left",
                padx=3
            )

        load(selected_category)
        
    def package_details(self, pid, category):

        row = package(pid)

        if not row:
            messagebox.showerror(
                "Package",
                "Package not found."
            )
            return

        (
            package_id,
            category,
            name,
            event_type,
            provider,
            description,
            inclusions,
            menu,
            price,
            image_path
        ) = row

        page = self.page(
            "Package Details",
            False,
            "Package Details"
        )

        # =========================
        # BACK BUTTON
        # =========================

        self.button(
            page,
            "← Back to Packages",
            lambda: self.package_catalog(category),
            False
        ).pack(
            anchor="w",
            padx=30,
            pady=(0, 10)
        )

        main = tk.Frame(
            page,
            bg=LIGHT
        )

        main.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=10
        )

        # =========================
        # TOP CARD
        # =========================

        top = tk.Frame(
            main,
            bg=CARD,
            padx=16,
            pady=12,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        top.pack(
            fill="x"
        )

        # =========================
        # PACKAGE PHOTO
        # =========================

        left = tk.Frame(
            top,
            bg=CARD
        )

        left.pack(
            side="left",
            padx=(0, 18)
        )

        photo = image_path

        img = load_image(
            photo,
            330,
            210
        )

        if img:

            self._photo_refs.append(img)

            tk.Label(
                left,
                image=img,
                bg=CARD
            ).pack()

        # =========================
        # PACKAGE INFORMATION
        # =========================

        right = tk.Frame(
            top,
            bg=CARD
        )

        right.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.label(
            right,
            name,
            20,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w"
        )

        self.label(
            right,
            category,
            10,
            True,
            PINK,
            CARD
        ).pack(
            anchor="w",
            pady=(5, 12)
        )

        self.label(
            right,
            f"Provider: {provider}",
            10,
            False,
            TEXT,
            CARD
        ).pack(
            anchor="w",
            pady=3
        )

        self.label(
            right,
            f"Event Type: {event_type}",
            10,
            False,
            TEXT,
            CARD
        ).pack(
            anchor="w",
            pady=3
        )

        # =========================
        # CATEGORY-SPECIFIC LABEL
        # =========================

        if category == "Catering":

            detail_title = "Catering Description"

        elif category == "Photography":

            detail_title = "Photography Description"

        elif category == "Venue":

            detail_title = "Venue Description"

        else:

            detail_title = "Styling Description"

        self.label(
            right,
            detail_title,
            10,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w",
            pady=(8, 3)
        )

        self.label(
            right,
            description,
            9,
            False,
            MUTED,
            CARD,
            wraplength=500,
            justify="left"
        ).pack(
            anchor="w"
        )

        # =========================
        # PRICE
        # =========================

        self.label(
            right,
            money(price),
            22,
            True,
            TEXT,
            CARD
        ).pack(
            anchor="w",
            pady=(8, 3)
        )

        # =========================
        # AVAILABILITY
        # =========================

        available = is_available(
            package_id,
            self.booking["date"]
        )

        self.label(
            right,
            "● Available"
            if available
            else "● Unavailable",
            9,
            True,
            GREEN if available else RED,
            CARD
        ).pack(
            anchor="w"
        )

        # =========================
        # SCROLLABLE LOWER DETAILS
        # =========================

        details_container = tk.Frame(
            main,
            bg=LIGHT
        )

        details_container.pack(
            fill="both",
            expand=True,
            pady=(8, 0)
        )

        details_canvas = tk.Canvas(
            details_container,
            bg=LIGHT,
            highlightthickness=0
        )

        details_scroll = ttk.Scrollbar(
            details_container,
            orient="vertical",
            command=details_canvas.yview
        )

        details = tk.Frame(
            details_canvas,
            bg=LIGHT
        )

        details_window = details_canvas.create_window(
            (0, 0),
            window=details,
            anchor="nw"
        )

        details_canvas.configure(
            yscrollcommand=details_scroll.set
        )

        details_canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        details_scroll.pack(
            side="right",
            fill="y"
        )


        def update_details_scroll(event=None):
            details.update_idletasks()

            details_canvas.configure(
                scrollregion=details_canvas.bbox("all")
            )


        def resize_details(event):
            details_canvas.itemconfig(
                details_window,
                width=event.width
            )


        details.bind(
            "<Configure>",
            update_details_scroll
        )

        details_canvas.bind(
            "<Configure>",
            resize_details
        )

        # AUTOMATIC MOUSE SCROLL
        # =========================

        def details_mousewheel(event):
            details_canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )


        details_container.bind_all(
            "<MouseWheel>",
            details_mousewheel
        )

        # =========================
        # LEFT DETAIL CARD
        # =========================

        includes_card = tk.Frame(
            details,
            bg=CARD,
            padx=20,
            pady=18,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        includes_card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 7)
        )

        if category == "Catering":

            title = "Package Includes"

        elif category == "Photography":

            title = "Photography Inclusions"

        elif category == "Venue":

            title = "Venue Inclusions"

        else:

            title = "Styling Inclusions"

        self.label(
            includes_card,
            title,
            14,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w",
            pady=(0, 10)
        )

        if inclusions:

            for item in inclusions.split(","):

                self.label(
                    includes_card,
                    f"✓ {item.strip()}",
                    9,
                    False,
                    TEXT,
                    CARD,
                    wraplength=450,
                    justify="left"
                ).pack(
                    anchor="w",
                    pady=3
                )

        # =========================
        # RIGHT DETAIL CARD
        # =========================

        detail_card = tk.Frame(
            details,
            bg=CARD,
            padx=20,
            pady=18,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        detail_card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(7, 0)
        )

        # =========================
        # CATERING
        # =========================

        if category == "Catering":

            self.label(
                detail_card,
                "Menu",
                14,
                True,
                PURPLE,
                CARD
            ).pack(
                anchor="w",
                pady=(0, 10)
            )

            if menu:

                for item in menu.split(","):

                    self.label(
                        detail_card,
                        f"🍽 {item.strip()}",
                        9,
                        False,
                        TEXT,
                        CARD
                    ).pack(
                        anchor="w",
                        pady=3
                    )

            else:

                self.label(
                    detail_card,
                    "Menu details are not available.",
                    9,
                    False,
                    MUTED,
                    CARD
                ).pack(
                    anchor="w"
                )

        # =========================
        # PHOTOGRAPHY
        # =========================

        elif category == "Photography":

            self.label(
                detail_card,
                "Photography Coverage",
                14,
                True,
                PURPLE,
                CARD
            ).pack(
                anchor="w",
                pady=(0, 10)
            )

            photography_details = [
                "Event highlights",
                "Professional photo documentation",
                "Edited digital photos",
                "High-resolution image delivery",
                "Online photo gallery"
            ]

            if package_id % 2 == 0:
                photography_details.append(
                    "Pre-event photography"
                )

            if package_id >= 20:
                photography_details.append(
                    "Same-day preview photos"
                )

            if package_id >= 40:
                photography_details.append(
                    "Priority photo delivery"
                )

            for item in photography_details:

                self.label(
                    detail_card,
                    f"📸 {item}",
                    9,
                    False,
                    TEXT,
                    CARD
                ).pack(
                    anchor="w",
                    pady=3
                )

        # =========================
        # VENUE
        # =========================

        elif category == "Venue":

            self.label(
                detail_card,
                "Venue Details",
                14,
                True,
                PURPLE,
                CARD
            ).pack(
                anchor="w",
                pady=(0, 10)
            )

            venue_details = [
                "Tables and chairs",
                "Air-conditioning",
                "Basic lighting",
                "Restroom access",
                "Venue setup assistance"
            ]

            if package_id % 2 == 0:
                venue_details.append(
                    "Parking area"
                )

            if package_id >= 20:
                venue_details.append(
                    "Preparation room"
                )

            if package_id >= 40:
                venue_details.append(
                    "Premium sound system"
                )

            for item in venue_details:

                self.label(
                    detail_card,
                    f"🏛 {item}",
                    9,
                    False,
                    TEXT,
                    CARD
                ).pack(
                    anchor="w",
                    pady=3
                )

        # =========================
        # STYLING
        # =========================

        else:

            self.label(
                detail_card,
                "Styling Details",
                14,
                True,
                PURPLE,
                CARD
            ).pack(
                anchor="w",
                pady=(0, 10)
            )

            styling_details = [
                "Main event backdrop",
                "Balloon decoration",
                "Entrance styling",
                "Table centerpieces",
                "Cake table styling"
            ]

            if package_id % 2 == 0:
                styling_details.append(
                    "Welcome signage"
                )

            if package_id >= 20:
                styling_details.append(
                    "Floral arrangements"
                )

            if package_id >= 40:
                styling_details.append(
                    "Premium backdrop design"
                )

            for item in styling_details:

                self.label(
                    detail_card,
                    f"🎀 {item}",
                    9,
                    False,
                    TEXT,
                    CARD
                ).pack(
                    anchor="w",
                    pady=3
                )

        # =========================
        # SELECT PACKAGE
        # =========================

        if available:

            def select_package():

                key = dict(CATEGORIES)[category]

                self.selected[key] = package_id

                messagebox.showinfo(
                    "Selected",
                    f"{name} added to your booking."
                )

                self.package_catalog()

            self.button(
                detail_card,
                "Select Package",
                select_package,
                True
            ).pack(
                anchor="e",
                pady=(20, 0)
            )
        
        

    def review_booking(self):

        if not self.selected:
            messagebox.showwarning(
                "No Package Selected",
                "Please select at least one package before reviewing your booking."
            )
            return

        unavailable_ids = get_unavailable_package_ids(
            self.booking["date"]
        )

        for selected_pid in self.selected.values():
            if selected_pid in unavailable_ids:
                messagebox.showerror(
                    "Unavailable",
                    "A selected package is no longer available. "
                    "Please return to Packages and choose another."
                )
                return

        page = self.page(
            "Booking Summary",
            False,
            "Review & Confirm"
        )

        # =========================
        # SCROLLABLE REVIEW AREA
        # =========================

        canvas = tk.Canvas(
            page,
            bg=LIGHT,
            highlightthickness=0,
            bd=0
        )

        canvas.pack(
            fill="both",
            expand=True
        )

        scroll_frame = tk.Frame(
            canvas,
            bg=LIGHT
        )

        window_id = canvas.create_window(
            (0, 0),
            window=scroll_frame,
            anchor="nw"
        )

        def update_scroll(event=None):
            scroll_frame.update_idletasks()

            canvas.configure(
                scrollregion=canvas.bbox("all")
            )

        def resize_scroll(event):
            canvas.itemconfigure(
                window_id,
                width=event.width
            )

        scroll_frame.bind(
            "<Configure>",
            update_scroll
        )

        canvas.bind(
            "<Configure>",
            resize_scroll
        )

        # =========================
        # MOUSE WHEEL
        # =========================

        def mousewheel(event):
            canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )

        canvas.bind_all(
            "<MouseWheel>",
            mousewheel
        )

        # =========================
        # BACK BUTTON
        # =========================

        self.button(
            scroll_frame,
            "← Back to Packages",
            self.package_catalog,
            False
        ).pack(
            anchor="w",
            padx=35,
            pady=(20, 5)
        )

        # =========================
        # MAIN TWO-COLUMN AREA
        # =========================

        content = tk.Frame(
            scroll_frame,
            bg=LIGHT
        )

        content.pack(
            fill="both",
            expand=True,
            padx=35,
            pady=20
        )

        # =========================
        # LEFT COLUMN
        # =========================

        left = tk.Frame(
            content,
            bg=LIGHT
        )

        left.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 12)
        )

        # =========================
        # EVENT DETAILS
        # =========================

        info = tk.Frame(
            left,
            bg=CARD,
            padx=25,
            pady=25,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        info.pack(
            fill="x"
        )

        self.label(
            info,
            "Event Details",
            17,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w"
        )

        for t in [
            f"Event Type: {self.event_type}",
            f"Event Date: {self.booking['date']}",
            f"Number of Guests: {self.booking['guests']}",
            f"Customer: {self.booking['name']}"
        ]:

            self.label(
                info,
                t,
                10,
                False,
                TEXT,
                CARD
            ).pack(
                anchor="w",
                pady=4
            )

        # =========================
        # SELECTED PACKAGES
        # =========================

        self.label(
            left,
            "Selected Packages",
            17,
            True,
            PURPLE,
            LIGHT
        ).pack(
            anchor="w",
            pady=(22, 10)
        )

        total = 0

        for key, pid in self.selected.items():

            r = package(pid)

            total += r[-1]

            c = tk.Frame(
                left,
                bg=CARD,
                padx=18,
                pady=14,
                highlightbackground=BORDER,
                highlightthickness=1
            )

            c.pack(
                fill="x",
                pady=5
            )

            self.label(
                c,
                r[2],
                11,
                True,
                PURPLE,
                CARD
            ).pack(
                side="left"
            )

            self.label(
                c,
                money(r[-1]),
                11,
                True,
                TEXT,
                CARD
            ).pack(
                side="right"
            )

        # =========================
        # RIGHT COLUMN
        # =========================

        right = tk.Frame(
            content,
            bg=CARD,
            padx=25,
            pady=25,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        right.pack(
            side="right",
            fill="y",
            padx=(12, 0)
        )

        self.label(
            right,
            "Cost Summary",
            17,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w"
        )

        self.label(
            right,
            "Subtotal",
            10,
            False,
            MUTED,
            CARD
        ).pack(
            anchor="w",
            pady=(25, 3)
        )

        self.label(
            right,
            money(total),
            18,
            True,
            TEXT,
            CARD
        ).pack(
            anchor="w"
        )

        self.label(
            right,
            "Deposit (20%)",
            10,
            False,
            MUTED,
            CARD
        ).pack(
            anchor="w",
            pady=(18, 3)
        )

        deposit = total * 0.20

        self.label(
            right,
            money(deposit),
            12,
            True,
            PINK,
            CARD
        ).pack(
            anchor="w"
        )

        self.label(
            right,
            "Remaining Balance",
            10,
            False,
            MUTED,
            CARD
        ).pack(
            anchor="w",
            pady=(18, 3)
        )

        self.label(
            right,
            money(total - deposit),
            15,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w"
        )

        # =========================
        # PAYMENT METHOD
        # =========================

        self.label(
            right,
            "Payment Method",
            12,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w",
            pady=(25, 8)
        )

        self.payment_method = tk.StringVar(
            value="GCash"
        )

        payment_options = [
            "GCash",
            "Maya",
            "Bank Transfer",
            "Cash"
        ]

        for method in payment_options:

            tk.Radiobutton(
                right,
                text=method,
                variable=self.payment_method,
                value=method,
                bg=CARD,
                fg=TEXT,
                activebackground=CARD,
                activeforeground=PURPLE,
                selectcolor="#EDE4F8",
                font=("Segoe UI", 10),
                anchor="w"
            ).pack(
                fill="x",
                pady=2
            )

        # =========================
        # SUBMIT RESERVATION
        # =========================

        self.button(
            right,
            "Submit Reservation",
            lambda: self.submit_reservation(total),
            True
        ).pack(
            fill="x",
            pady=30
        )
        
        # =========================
        # PAYMENT NOTICE
        # =========================

        self.label(
            right,
            "No payment is required yet.",
            10,
            True,
            ORANGE,
            CARD
        ).pack(
            anchor="w",
            pady=(15, 0)
        )

        self.label(
            right,
            "Your 20% deposit will be due only "
            "after your reservation is approved.",
            9,
            False,
            MUTED,
            CARD,
            wraplength=250,
            justify="left"
        ).pack(
            anchor="w",
            pady=(5, 0)
        )

        # =========================
        # INITIAL SCROLL SETUP
        # =========================

        scroll_frame.update_idletasks()

        canvas.configure(
            scrollregion=canvas.bbox("all")
        )

    def submit_reservation(self, total):

        for pid in self.selected.values():
            if not is_available(
                pid,
                self.booking["date"]
            ):
                messagebox.showerror(
                    "Conflict",
                    "A selected package is no longer available."
                )
                return

        # Get selected payment method
        payment_method = self.payment_method.get()

        rid = create_reservation(
            self.user,
            self.booking,
            self.event_type,
            self.selected,
            total,
            payment_method
        )

        self.send_system_message(
            self.user[0],
            "Thank You for Booking with EventHub!",
            "Hello! Thank you for choosing EventHub for your special event. "
            "We're happy to be part of your celebration! "
            "Your reservation has been successfully received, "
            "and our team will keep you updated regarding your booking.\n\n"
            f"Payment Method: {payment_method}",
            False
        )

        from datetime import datetime

        reservation_id = f"EVT-{datetime.now().year}-{rid:04d}"

        popup = tk.Toplevel(self)
        popup.title("Reservation Submitted")
        popup.configure(bg="#B89EF1")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()

        popup_width = 560
        popup_height = 600

        popup.update_idletasks()

        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()

        x = (screen_width - popup_width) // 2
        y = (screen_height - popup_height) // 2 - 30
        y = max(0, min(y, screen_height - popup_height))

        popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

        # Main confirmation card
        card = tk.Frame(
            popup,
            bg="#F8F4FF",
            padx=24,
            pady=12
        )
        card.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=14
        )

        # Success icon
        tk.Label(
            card,
            text="✓",
            font=("Segoe UI", 28, "bold"),
            fg="white",
            bg="#22A66A",
            width=3,
            height=1
        ).pack(pady=(0, 8))

        # Heading
        tk.Label(
            card,
            text="Reservation Submitted\nSuccessfully!",
            font=("Segoe UI", 19, "bold"),
            fg="#39206D",
            bg="#F8F4FF",
            justify="center"
        ).pack(pady=(0, 8))

        tk.Label(
            card,
            text="Thank you for choosing EventHub!",
            font=("Segoe UI", 11),
            fg="#756887",
            bg="#F8F4FF"
        ).pack(pady=(0, 12))

        # Reservation information
        details = tk.Frame(
            card,
            bg="#EDE4FC",
            padx=14,
            pady=8
        )
        details.pack(fill="x")

        detail_rows = [
            ("Reservation ID", reservation_id),
            ("Event Type", self.event_type),
            ("Event Date", self.booking.get("date", "Not specified")),
            ("Guests", str(self.booking.get("guests", "Not specified"))),
            ("Payment Method", payment_method),
            ("Status", "PENDING"),
            ("Total Amount", money(total))
        ]

        for label_text, value_text in detail_rows:
            line = tk.Frame(details, bg="#EDE4FC")
            line.pack(fill="x", pady=3)

            tk.Label(
                line,
                text=label_text,
                font=("Segoe UI", 10),
                fg="#756887",
                bg="#EDE4FC"
            ).pack(side="left")

            tk.Label(
                line,
                text=value_text,
                font=("Segoe UI", 10, "bold"),
                fg="#39206D",
                bg="#EDE4FC",
                wraplength=250,
                justify="right"
            ).pack(side="right")

        # Confirmation message
        tk.Label(
            card,
            text=(
                "Your reservation has been received!\n"
                "Our team will review your booking and provide "
                "an update within 24 hours.\n"
                "No payment is required until your reservation "
                "is approved."
            ),
            font=("Segoe UI", 10),
            fg="#756887",
            bg="#F8F4FF",
            justify="center",
            wraplength=460
        ).pack(pady=12)

        # OK button
        def close_popup():
            popup.grab_release()
            popup.destroy()
            self.my_reservations()

        ok_button = tk.Button(
            card,
            text="OK   →",
            command=close_popup,
            font=("Segoe UI", 11, "bold"),
            bg="#D946A6",
            fg="white",
            activebackground="#C43591",
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            pady=10
        )
        ok_button.pack(fill="x", side="bottom", pady=(6, 0))

        popup.protocol("WM_DELETE_WINDOW", close_popup)


    def my_reservations(self):
        page = self.page(
        "My Reservations",
        admin=False,
        title="My Reservations"
        )

        right = page

        # =========================
        # LOAD RESERVATIONS
        # =========================
        con = connect()

        rows = con.execute(
            """
            SELECT
                id,
                event_type,
                event_date,
                guests,
                catering_id,
                photography_id,
                venue_id,
                styling_id,
                total,
                status
            FROM reservations
            WHERE customer=?
            ORDER BY id DESC
            """,
            (self.user[0],)
        ).fetchall()

        con.close()

        # =========================
        # HEADER
        # =========================
        header = tk.Frame(
            right,
            bg=LIGHT
        )
        header.pack(
            fill="x",
            padx=35,
            pady=(25, 10)
        )

        # LEFT SIDE
        header_left = tk.Frame(
            header,
            bg=LIGHT
        )
        header_left.pack(
            side="left",
            fill="x",
            expand=True
        )

        title_row = tk.Frame(
            header_left,
            bg=LIGHT
        )
        title_row.pack(
            anchor="w"
        )

        self.label(
            title_row,
            "📅 My Reservations",
            24,
            True,
            TEXT,
            LIGHT
        ).pack(
            side="left"
        )

        self.label(
            header_left,
            "View and manage your event reservations.",
            10,
            False,
            MUTED,
            LIGHT
        ).pack(
            anchor="w",
            pady=(3, 0)
        )

        # =========================
        # HEADER STATISTICS
        # =========================
        total_bookings = len(rows)

        upcoming_events = sum(
            1
            for r in rows
            if r[9] in ("Pending", "Approved")
        )

        stats = tk.Frame(
            header,
            bg=LIGHT
        )
        stats.pack(
            side="right"
        )

        # TOTAL BOOKINGS
        total_card = tk.Frame(
            stats,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            width=150,
            height=75
        )
        total_card.pack(
            side="left",
            padx=(0, 10)
        )
        total_card.pack_propagate(False)

        self.label(
            total_card,
            "Total Bookings",
            9,
            False,
            MUTED,
            CARD
        ).pack(
            pady=(12, 0)
        )

        self.label(
            total_card,
            str(total_bookings),
            20,
            True,
            PURPLE,
            CARD
        ).pack()

        # UPCOMING EVENTS
        upcoming_card = tk.Frame(
            stats,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            width=150,
            height=75
        )
        upcoming_card.pack(
            side="left"
        )
        upcoming_card.pack_propagate(False)

        self.label(
            upcoming_card,
            "Upcoming Events",
            9,
            False,
            MUTED,
            CARD
        ).pack(
            pady=(12, 0)
        )

        self.label(
            upcoming_card,
            str(upcoming_events),
            20,
            True,
            PURPLE,
            CARD
        ).pack()

        # =========================
        # FILTER BAR
        # =========================
        controls = tk.Frame(
            right,
            bg=LIGHT
        )
        controls.pack(
            fill="x",
            padx=35,
            pady=(10, 15)
        )

        # FILTER BUTTONS
        filter_frame = tk.Frame(
            controls,
            bg=LIGHT
        )
        filter_frame.pack(
            side="left"
        )

        filter_var = tk.StringVar(
            value="All"
        )
        
        # =========================
        # SEARCH BAR
        # =========================
        search_frame = tk.Frame(
            controls,
            bg="#F3EEFA",
            highlightbackground="#D8C9EF",
            highlightthickness=1
        )
        search_frame.pack(
            side="right",
            padx=(12, 0)
        )

        search_var = tk.StringVar()

        search_icon = tk.Label(
            search_frame,
            text="⌕",
            font=("Segoe UI", 12),
            bg="#F3EEFA",
            fg="#7B52B9"
        )
        search_icon.pack(
            side="left",
            padx=(8, 3)
        )

        search_entry = tk.Entry(
            search_frame,
            textvariable=search_var,
            font=("Segoe UI", 9),
            bg="#F3EEFA",
            fg="#39206D",
            insertbackground="#39206D",
            relief="flat",
            bd=0,
            width=38
        )
        search_entry.pack(
            side="left",
            ipady=5,
            padx=(0, 8),
            pady=2
        )
        placeholder_text = "Search by event type, date or booking ID"

        def on_focus_in(event):
            if search_entry.get() == placeholder_text:
                search_entry.delete(0, "end")
                search_entry.config(fg="#39206D")
                search_var.set("")

        def on_focus_out(event):
            if not search_entry.get().strip():
                search_entry.config(fg="#8B7BA8")
                search_entry.insert(0, placeholder_text)
                search_var.set("")

        search_entry.bind("<FocusIn>", on_focus_in)
        search_entry.bind("<FocusOut>", on_focus_out)

        search_entry.insert(0, placeholder_text)
        search_entry.config(fg="#8B7BA8")
        search_var.set("")

        
        # =========================
        # MAIN SCROLLABLE AREA
        # =========================
        outer = tk.Frame(
            right,
            bg=LIGHT
        )
        outer.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=(0, 20)
        )

        canvas = tk.Canvas(
            outer,
            bg=LIGHT,
            highlightthickness=0
        )
        canvas.pack(
            fill="both",
            expand=True
        )

        container = tk.Frame(
            canvas,
            bg=LIGHT
        )

        canvas_window = canvas.create_window(
            (0, 0),
            window=container,
            anchor="nw"
        )

        def resize_container(event):
            canvas.itemconfig(
                canvas_window,
                width=event.width
            )

        canvas.bind(
            "<Configure>",
            resize_container
        )

        def update_scrollregion(event=None):
            canvas.configure(
                scrollregion=canvas.bbox("all")
            )

        container.bind(
            "<Configure>",
            update_scrollregion
        )

        # =========================
        # MOUSE WHEEL SCROLL
        # =========================
        def mousewheel(event):
            if event.delta:
                canvas.yview_scroll(
                    int(-1 * (event.delta / 120)),
                    "units"
                )
            return "break"

        def bind_mousewheel(widget):
            widget.bind(
                "<MouseWheel>",
                mousewheel
            )

            for child in widget.winfo_children():
                bind_mousewheel(child)

        def refresh_mousewheel_bindings(event=None):
            bind_mousewheel(container)

        # Bind to the canvas and all existing child widgets
        bind_mousewheel(container)
        canvas.bind("<MouseWheel>", mousewheel)
        outer.bind("<MouseWheel>", mousewheel)

        # Also bind newly created widgets after the UI updates
        container.bind(
            "<Configure>",
            lambda event: (
                update_scrollregion(event),
                refresh_mousewheel_bindings()
            )
        )

        # =========================
        # VIEW DETAILS
        # =========================
        
        def view_details(
            reservation_id,
            event_type,
            event_date,
            guests,
            total,
            status,
            package_names,
            payment_method
        ):
            details = tk.Toplevel(self)
            details.title("Reservation Details")
            details.configure(bg=LIGHT)
            details.resizable(False, False)

            window_w, window_h = 1000, 620
            screen_w = details.winfo_screenwidth()
            screen_h = details.winfo_screenheight()
            x = (screen_w - window_w) // 2
            y = (screen_h - window_h) // 2 - 30
            details.geometry(
                f"{window_w}x{window_h}+{x}+{y}"
            )

            details.transient(self)
            details.grab_set()
            
            # =========================
            # MAIN SCROLLABLE AREA
            # =========================
            scroll_container = tk.Frame(details, bg=LIGHT)
            scroll_container.pack(
                fill="both",
                expand=True,
                padx=12,
                pady=12
            )

            canvas = tk.Canvas(
                scroll_container,
                bg=LIGHT,
                highlightthickness=0,
                bd=0
            )
            canvas.pack(fill="both", expand=True)

            main = tk.Frame(canvas, bg=LIGHT)

            main_window = canvas.create_window(
                (0, 0),
                window=main,
                anchor="nw"
            )

            def update_scroll_region(event=None):
                canvas.configure(
                    scrollregion=canvas.bbox("all")
                )

            def resize_main(event):
                canvas.itemconfigure(
                    main_window,
                    width=event.width
                )

            main.bind("<Configure>", update_scroll_region)
            canvas.bind("<Configure>", resize_main)

            # Mouse wheel works anywhere inside the popup
            def mousewheel_scroll(event):
                if event.delta:
                    canvas.yview_scroll(
                        -1 if event.delta > 0 else 1,
                        "units"
                    )
                return "break"

            def enable_mousewheel(event=None):
                details.bind_all(
                    "<MouseWheel>",
                    mousewheel_scroll
                )

            def disable_mousewheel(event=None):
                details.unbind_all("<MouseWheel>")

            details.bind("<Enter>", enable_mousewheel)
            details.bind("<Leave>", disable_mousewheel)
            details.bind("<Destroy>", disable_mousewheel)


            # Left and right columns
            main.grid_columnconfigure(0, weight=5, uniform="cols")
            main.grid_columnconfigure(1, weight=7, uniform="cols")
            main.grid_rowconfigure(0, weight=1)

            left = tk.Frame(
                main,
                bg=CARD,
                padx=20,
                pady=18,
                highlightbackground=BORDER,
                highlightthickness=1
            )
            left.grid(
                row=0, column=0, sticky="nsew", padx=(0, 8)
            )

            right = tk.Frame(
                main,
                bg=CARD,
                padx=18,
                pady=18,
                highlightbackground=BORDER,
                highlightthickness=1
            )
            right.grid(
                row=0, column=1, sticky="nsew", padx=(8, 0)
            )

            # =========================
            # LEFT: RESERVATION DETAILS
            # =========================
            heading = tk.Frame(left, bg=CARD)
            heading.pack(fill="x", pady=(0, 14))

            icon_box = tk.Label(
                heading,
                text="▦",
                font=("Segoe UI", 23, "bold"),
                bg="#EEE5FF",
                fg=PURPLE,
                width=3,
                height=2
            )
            icon_box.pack(side="left", padx=(0, 12))

            heading_text = tk.Frame(heading, bg=CARD)
            heading_text.pack(side="left", fill="x", expand=True)

            self.label(
                heading_text,
                f"Reservation EVT-{datetime.now().year}-{reservation_id:04d}",
                15,
                True,
                PURPLE,
                CARD,
                wraplength=390,
                justify="left"
            ).pack(anchor="w", pady=(3, 8))

            status_color = (
                "#16845B" if status == "Approved"
                else PINK if status in ("Cancelled", "Rejected")
                else PURPLE
            )

            status_bg = (
                "#DDF5E9" if status == "Approved"
                else "#FCE4EF" if status in ("Cancelled", "Rejected")
                else "#EEE5FF"
            )

            tk.Label(
                heading_text,
                text=f"●  {status}",
                bg=status_bg,
                fg=status_color,
                font=("Segoe UI", 9, "bold"),
                padx=12,
                pady=5
            ).pack(anchor="w")

            def detail_row(parent, icon, title, value):
                row = tk.Frame(parent, bg=CARD)
                row.pack(fill="x", pady=9)

                tk.Label(
                    row,
                    text=icon,
                    bg=CARD,
                    fg=PURPLE,
                    font=("Segoe UI", 14),
                    width=3
                ).pack(side="left", anchor="n")

                text_box = tk.Frame(row, bg=CARD)
                text_box.pack(
                    side="left", fill="x", expand=True
                )

                self.label(
                    text_box, title, 9, False, MUTED, CARD
                ).pack(anchor="w")

                self.label(
                    text_box, str(value), 11, True, TEXT, CARD,
                    wraplength=390,
                    justify="left"
                ).pack(anchor="w", pady=(3, 0))

                tk.Frame(
                    parent, bg=BORDER, height=1
                ).pack(fill="x", pady=(5, 0))

            detail_row(left, "♧", "Event Type", event_type)
            detail_row(left, "▦", "Event Date", event_date)
            detail_row(left, "♙", "Guests", guests)
            detail_row(
                left, "▤", "Payment Method",
                payment_method or "Not specified"
            )

            # TOTAL AMOUNT
            total_box = tk.Frame(
                left,
                bg="#EEE5FF",
                padx=16,
                pady=14
            )
            total_box.pack(fill="x", pady=(16, 14))

            self.label(
                total_box, "TOTAL AMOUNT", 9, True, PURPLE, "#EEE5FF"
            ).pack(anchor="w")

            self.label(
                total_box, money(total), 23, True, PURPLE, "#EEE5FF"
            ).pack(anchor="w", pady=(5, 0))

            # SELECTED PACKAGES
            self.label(
                left, "◇  Selected Packages", 12, True, PURPLE, CARD
            ).pack(anchor="w", pady=(4, 10))

            package_box = tk.Frame(
                left,
                bg="#FAF8FF",
                padx=12,
                pady=10,
                highlightbackground=BORDER,
                highlightthickness=1
            )
            package_box.pack(fill="x")

            if package_names:
                for name in package_names:
                    self.label(
                        package_box,
                        f"📦  {name}",
                        10,
                        True,
                        TEXT,
                        "#FAF8FF",
                        wraplength=430,
                        justify="left"
                    ).pack(anchor="w", pady=4)
            else:
                self.label(
                    package_box,
                    "No package information available.",
                    9,
                    False,
                    MUTED,
                    "#FAF8FF"
                ).pack(anchor="w")

            # =========================
            # RIGHT: EVENT BANNER
            # =========================
            banner = tk.Frame(
                right,
                bg=CARD,
                height=205
            )
            banner.pack(fill="x", pady=(0, 18))
            banner.pack_propagate(False)

            banner_path = event_photo_path(event_type)
            banner_image = load_image(
                banner_path,
                850,
                205
            )

            banner_canvas = tk.Canvas(
                banner,
                bg="#5A3565",
                highlightthickness=0,
                bd=0
            )
            banner_canvas.pack(fill="both", expand=True)

            if banner_image:
                details._banner_image = banner_image

                banner_canvas.create_image(
                    0,
                    0,
                    image=banner_image,
                    anchor="nw"
                )
            else:
                banner_canvas.create_text(
                    20,
                    25,
                    text=f"{str(event_type).upper()} CELEBRATION",
                    fill="white",
                    font=("Segoe UI", 12, "bold"),
                    anchor="nw"
                )

            banner_canvas.create_text(
                30,
                45,
                text=f"{str(event_type).upper()} CELEBRATION",
                fill="white",
                font=("Segoe UI", 10, "bold"),
                anchor="w"
            )

            banner_canvas.create_text(
                30,
                100,
                text="Make Every\nMoment Special",
                fill="white",
                font=("Segoe UI", 22, "bold"),
                anchor="w",
                width=390
            )


            # =========================
            # PACKAGE DETAILS
            # =========================
            self.label(
                right, "◇  Package Details", 13, True, PURPLE, CARD
            ).pack(anchor="w", pady=(0, 10))

            package_detail_card = tk.Frame(
                right,
                bg="#FAF8FF",
                padx=14,
                pady=13,
                highlightbackground=BORDER,
                highlightthickness=1
            )
            package_detail_card.pack(fill="x", pady=(0, 18))

            if package_names:
                package_text = ", ".join(package_names)
            else:
                package_text = "No package information available."

            self.label(
                package_detail_card,
                package_text,
                11,
                True,
                TEXT,
                "#FAF8FF",
                wraplength=650,
                justify="left"
            ).pack(anchor="w")

            # =========================
            # RESERVATION OVERVIEW
            # =========================
            self.label(
                right,
                "▤  Reservation Overview",
                13,
                True,
                PURPLE,
                CARD
            ).pack(anchor="w", pady=(0, 10))

            overview = tk.Frame(
                right,
                bg="#F7F3FC",
                padx=16,
                pady=15
            )
            overview.pack(fill="x")

            overview.grid_columnconfigure(0, weight=1)
            overview.grid_columnconfigure(1, weight=1)

            overview_items = [
                ("Event Date", event_date),
                ("Guests", str(guests)),
                ("Payment Method", payment_method or "Not specified"),
                ("Status", status)
            ]

            for index, (title, value) in enumerate(overview_items):
                r, c = divmod(index, 2)

                cell = tk.Frame(overview, bg="#F7F3FC")
                cell.grid(
                    row=r,
                    column=c,
                    sticky="nsew",
                    padx=8,
                    pady=10
                )

                self.label(
                    cell, title, 9, False, MUTED, "#F7F3FC"
                ).pack(anchor="w")

                self.label(
                    cell, value, 11, True, TEXT, "#F7F3FC",
                    wraplength=260,
                    justify="left"
                ).pack(anchor="w", pady=(4, 0))

            
            # =========================
            # BOTTOM BUTTON
            # =========================
            buttons = tk.Frame(
                right,
                bg=CARD
            )
            buttons.pack(
                side="bottom",
                fill="x",
                pady=(18, 0)
            )

            self.button(
                buttons,
                "✕  Close",
                details.destroy,
                True
            ).pack(fill="x")


        # =========================
        # DISPLAY RESERVATIONS
        # =========================
        def display_reservations(*args):

            for widget in container.winfo_children():
                widget.destroy()

            search_text = (
                search_var.get()
                .strip()
                .lower()
            )

            selected_filter = filter_var.get()

            filtered_rows = []

            for r in rows:

                (
                    reservation_id,
                    event_type,
                    event_date,
                    guests,
                    catering_id,
                    photography_id,
                    venue_id,
                    styling_id,
                    total,
                    status
                ) = r

                if selected_filter != "All":

                    if status != selected_filter:
                        continue

                searchable = (
                    f"EVT-{datetime.now().year}-{reservation_id:04d} "
                    f"{event_type} "
                    f"{event_date} "
                    f"{status} "
                    f"{guests} "
                    f"{payment_method if 'payment_method' in locals() else ''}"
                ).lower()

                if (
                    search_text
                    and search_text not in searchable
                ):
                    continue

                filtered_rows.append(r)

            # =========================
            # EMPTY FILTER RESULT
            # =========================
            if not filtered_rows:

                empty = tk.Frame(
                    container,
                    bg=CARD
                )

                empty.pack(
                    fill="x",
                    padx=10,
                    pady=30
                )

                self.label(
                    empty,
                    "No reservations found.",
                    13,
                    True,
                    MUTED,
                    CARD
                ).pack(
                    pady=35
                )

                return

            # =========================
            # RESERVATION CARDS
            # =========================
            for index, r in enumerate(
                filtered_rows
            ):

                (
                    reservation_id,
                    event_type,
                    event_date,
                    guests,
                    catering_id,
                    photography_id,
                    venue_id,
                    styling_id,
                    total,
                    status
                ) = r

                # =========================
                # PAYMENT METHOD
                # =========================
                con = connect()

                payment_row = con.execute(
                    """
                    SELECT payment_method
                    FROM reservations
                    WHERE id=?
                    """,
                    (reservation_id,)
                ).fetchone()

                con.close()

                payment_method = (
                    payment_row[0]
                    if payment_row
                    and payment_row[0]
                    else "Not specified"
                )

                # =========================
                # PACKAGE NAMES
                # =========================
                package_ids = [
                    catering_id,
                    photography_id,
                    venue_id,
                    styling_id
                ]

                package_names = []

                for pid in package_ids:

                    if pid:

                        try:
                            p = package(pid)

                            if p:

                                if isinstance(
                                    p,
                                    (tuple, list)
                                ):
                                    package_names.append(
                                        str(p[1])
                                        if len(p) > 1
                                        else str(p[0])
                                    )
                                else:
                                    package_names.append(
                                        str(p)
                                    )

                        except Exception:
                            pass

                # =========================
                # CARD
                # =========================
                card = tk.Frame(
                    container,
                    bg=CARD,
                    height=590,
                    highlightbackground=BORDER,
                    highlightthickness=1
                )

                card.grid_propagate(False)

                card.grid(
                    row=index // 3,
                    column=index % 3,
                    padx=10,
                    pady=10,
                    sticky="nsew"
                )

                for col in range(3):
                    container.grid_columnconfigure(
                        col,
                        weight=1,
                        uniform="reservation_cards"
                    )

                # =========================
                # EVENT IMAGE
                # =========================
                image_frame = tk.Frame(
                    card,
                    bg=CARD,
                    height=170
                )

                image_frame.pack(
                    fill="x"
                )

                image_frame.pack_propagate(
                    False
                )

                try:

                    event_path = event_photo_path(
                        event_type
                    )

                    img = load_image(
                        event_path,
                        330,
                        170
                    )

                    if img:

                        image_label = tk.Label(
                            image_frame,
                            image=img,
                            bg=CARD,
                            bd=0
                        )

                        image_label.image = img

                        image_label.pack(
                            fill="both",
                            expand=True
                        )

                        self._photo_refs.append(
                            img
                        )

                    else:

                        self.label(
                            image_frame,
                            event_type,
                            18,
                            True,
                            PURPLE,
                            CARD
                        ).pack(
                            expand=True
                        )

                except Exception:

                    self.label(
                        image_frame,
                        event_type,
                        18,
                        True,
                        PURPLE,
                        CARD
                    ).pack(
                        expand=True
                    )

                # =========================
                # CARD CONTENT
                # =========================
                content = tk.Frame(
                    card,
                    bg=CARD
                )

                content.pack(
                    fill="both",
                    expand=True,
                    padx=18,
                    pady=15
                )

                self.label(
                    content,
                    event_type,
                    16,
                    True,
                    PURPLE,
                    CARD
                ).pack(
                    anchor="w"
                )

                self.label(
                    content,
                    f"📅 {event_date}",
                    10,
                    False,
                    TEXT,
                    CARD
                ).pack(
                    anchor="w",
                    pady=(8, 2)
                )

                self.label(
                    content,
                    f"👥 {guests} guests",
                    10,
                    False,
                    TEXT,
                    CARD
                ).pack(
                    anchor="w",
                    pady=2
                )

                self.label(
                    content,
                    f"💳 {payment_method}",
                    10,
                    False,
                    TEXT,
                    CARD
                ).pack(
                    anchor="w",
                    pady=2
                )

                self.label(
                    content,
                    f"💰 {money(total)}",
                    13,
                    True,
                    PURPLE,
                    CARD
                ).pack(
                    anchor="w",
                    pady=(8, 2)
                )

                # =========================
                # STATUS
                # =========================
                status_color = {
                    "Pending": ORANGE,
                    "Approved": GREEN,
                    "Completed": PURPLE,
                    "Cancelled": RED
                }.get(
                    status,
                    MUTED
                )

                self.label(
                    content,
                    status,
                    9,
                    True,
                    status_color,
                    CARD
                ).pack(
                    anchor="w",
                    pady=(5, 8)
                )

                # =========================
                # PACKAGE NAMES
                # =========================
                if package_names:

                    self.label(
                        content,
                        "Packages:",
                        10,
                        True,
                        TEXT,
                        CARD
                    ).pack(
                        anchor="w",
                        pady=(5, 2)
                    )

                    for name in package_names[:4]:

                        self.label(
                            content,
                            f"• {name}",
                            9,
                            False,
                            MUTED,
                            CARD
                        ).pack(
                            anchor="w"
                        )

                # =========================
                # ACTIONS
                # =========================
                actions = tk.Frame(
                    content,
                    bg=CARD
                )

                actions.pack(
                    fill="x",
                    pady=(15, 0)
                )

                self.button(
                    actions,
                    "View Details",
                    lambda
                    rid=reservation_id,
                    et=event_type,
                    ed=event_date,
                    g=guests,
                    t=total,
                    s=status,
                    pn=package_names,
                    pm=payment_method:
                    view_details(
                        rid,
                        et,
                        ed,
                        g,
                        t,
                        s,
                        pn,
                        pm
                    ),
                    False
                ).pack(
                    side="left",
                    padx=(0, 5)
                )

                # =========================
                # CANCEL BUTTON
                # =========================
                if status == "Pending":

                    def cancel_reservation(
                        rid=reservation_id
                    ):
                        confirm = messagebox.askyesno(
                            "Cancel Reservation",
                            "Are you sure you want to cancel this reservation?"
                        )

                        if not confirm:
                            return

                        con = connect()

                        con.execute(
                            """
                            UPDATE reservations
                            SET status='Cancelled'
                            WHERE id=?
                            AND customer=?
                            AND status='Pending'
                            """,
                            (
                                rid,
                                self.user[0]
                            )
                        )

                        con.commit()
                        con.close()

                        messagebox.showinfo(
                            "Reservation Cancelled",
                            "Your reservation has been cancelled."
                        )

                        self.my_reservations()

                    self.button(
                        actions,
                        "Cancel Reservation",
                        cancel_reservation,
                        True
                    ).pack(
                        side="left",
                        padx=5
                    )

                # =========================
                # PAY NOW BUTTON
                # =========================
                elif status == "Approved":

                    self.button(
                        actions,
                        "Pay Now",
                        lambda rid=reservation_id: self.demo_payment(rid),
                        True
                    ).pack(
                        side="left",
                        padx=5
                    )

        # =========================
        # FILTER BUTTONS
        # =========================
        def set_filter(value):

            filter_var.set(value)

            for button_widget in filter_buttons:

                if button_widget["text"] == value:

                    button_widget.configure(
                        bg=PURPLE,
                        fg="white"
                    )

                else:

                    button_widget.configure(
                        bg="#EEE7F5",
                        fg=PURPLE
                    )

            display_reservations()

        filter_buttons = []

        for filter_name in [
            "All",
            "Pending",
            "Approved",
            "Completed"
        ]:

            filter_button = tk.Button(
                filter_frame,
                text=filter_name,
                command=lambda
                value=filter_name:
                set_filter(value),
                bg=PURPLE
                if filter_name == "All"
                else "#EEE7F5",
                fg="white"
                if filter_name == "All"
                else PURPLE,
                activebackground=PURPLE2,
                activeforeground="white",
                relief="flat",
                bd=0,
                font=("Segoe UI", 9, "bold"),
                padx=14,
                pady=7,
                cursor="hand2"
            )

            filter_button.pack(
                side="left",
                padx=(0, 5)
            )

            filter_buttons.append(
                filter_button
            )

        # =========================
        # SEARCH / FILTER EVENTS
        # =========================
        search_var.trace_add(
            "write",
            display_reservations
        )

        display_reservations()
            
    def customer_messages(self, filter_type="All"):

        ensure_message_tables()

        page = self.page(
            "Messages",
            admin=False,
            title="Messages"
        )

        self.label(
            page,
            "View updates, notifications and messages from EventHub admin.",
            10,
            False,
            MUTED,
            LIGHT
        ).pack(
            anchor="w",
            padx=35
        )

        # =========================
        # FILTERS
        # =========================

        filters = tk.Frame(
            page,
            bg=LIGHT
        )

        filters.pack(
            fill="x",
            padx=35,
            pady=(18, 10)
        )

        self.button(
            filters,
            "All",
            lambda: self.customer_messages("All"),
            True
        ).pack(side="left", padx=(0, 8))

        self.button(
            filters,
            "Unread",
            lambda: self.customer_messages("Unread"),
            False
        ).pack(side="left", padx=8)

        self.button(
            filters,
            "Important",
            lambda: self.customer_messages("Important"),
            False
        ).pack(side="left", padx=8)

        # =========================
        # MESSAGE LIST
        # =========================

        card = tk.Frame(
            page,
            bg=CARD,
            padx=15,
            pady=15,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        card.pack(
            fill="both",
            expand=True,
            padx=35,
            pady=(0, 25)
        )

        message_canvas = tk.Canvas(
            card,
            bg=CARD,
            highlightthickness=0
        )

        message_scrollbar = ttk.Scrollbar(
            card,
            orient="vertical",
            command=message_canvas.yview
        )

        message_list_frame = tk.Frame(
            message_canvas,
            bg=CARD
        )

        message_window = message_canvas.create_window(
            (0, 0),
            window=message_list_frame,
            anchor="nw"
        )

        message_canvas.configure(
            yscrollcommand=message_scrollbar.set
        )

        message_canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        message_scrollbar.pack(
            side="right",
            fill="y"
        )

        def update_message_scroll(event=None):
            message_canvas.configure(
                scrollregion=message_canvas.bbox("all")
            )

        def resize_message_list(event):
            message_canvas.itemconfigure(
                message_window,
                width=event.width
            )

        message_list_frame.bind(
            "<Configure>",
            update_message_scroll
        )

        message_canvas.bind(
            "<Configure>",
            resize_message_list
        )

        def message_mousewheel(event):
            message_canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )

        def enable_message_scroll(event):
            message_canvas.bind_all(
                "<MouseWheel>",
                message_mousewheel
            )

        def disable_message_scroll(event):
            message_canvas.unbind_all(
                "<MouseWheel>"
            )

        message_canvas.bind(
            "<Enter>",
            enable_message_scroll
        )

        message_canvas.bind(
            "<Leave>",
            disable_message_scroll
        )

        # =========================
        # LOAD CUSTOMER MESSAGES
        # =========================

        con = connect()

        try:
            if filter_type == "Unread":
                rows = con.execute(
                    """
                    SELECT id, sender, message, created_at, is_read, important
                    FROM messages
                    WHERE recipient = ?
                    AND is_read = 0
                    AND LOWER(sender_role) = 'admin'
                    ORDER BY id DESC
                    """,
                    (self.user[0],)
                ).fetchall()

            elif filter_type == "Important":
                rows = con.execute(
                    """
                    SELECT id, sender, message, created_at, is_read, important
                    FROM messages
                    WHERE recipient = ?
                    AND LOWER(sender_role) = 'admin'
                    AND important = 1
                    ORDER BY id DESC
                    """,
                    (self.user[0],)
                ).fetchall()

            else:
                rows = con.execute(
                    """
                    SELECT id, sender, message, created_at, is_read, important
                    FROM messages
                    WHERE recipient = ?
                    AND LOWER(sender_role) = 'admin'
                    ORDER BY id DESC
                    """,
                    (self.user[0],)
                ).fetchall()

        finally:
            con.close()

        if not rows:

            self.label(
                message_list_frame,
                "No messages yet",
                16,
                True,
                PURPLE,
                CARD
            ).pack(
                pady=(80, 5)
            )

            self.label(
                message_list_frame,
                "Messages from EventHub Admin will appear here.",
                10,
                False,
                MUTED,
                CARD
            ).pack()

            return

        # =========================
        # DISPLAY MESSAGES
        # =========================

        for row in rows:

            message_id = row[0]
            sender = row[1]
            message = row[2]
            created_at = row[3]
            is_read = row[4]
            important = row[5]

            item_bg = "#F7F2FC" if not is_read else CARD

            item = tk.Frame(
                message_list_frame,
                bg=item_bg,
                padx=16,
                pady=14,
                highlightbackground=BORDER,
                highlightthickness=1
            )

            item.pack(
                fill="x",
                pady=5
            )

            top = tk.Frame(
                item,
                bg=item_bg
            )

            top.pack(
                fill="x"
            )

            self.label(
                top,
                "✉  " + sender,
                11,
                True,
                PURPLE,
                item_bg
            ).pack(
                side="left"
            )

            if important:

                self.label(
                    top,
                    "IMPORTANT",
                    8,
                    True,
                    "white",
                    PINK
                ).pack(
                    side="left",
                    padx=10
                )

            self.label(
                top,
                created_at,
                8,
                False,
                MUTED,
                item_bg
            ).pack(
                side="right"
            )

            message_body = tk.Frame(
                item,
                bg=item_bg,
                cursor="hand2"
            )

            message_body.pack(
                fill="x",
                pady=(8, 0)
            )

            self.label(
                message_body,
                message,
                10,
                False,
                TEXT,
                item_bg,
                wraplength=850,
                justify="left"
            ).pack(
                anchor="w"
            )

            # Make the whole message clickable
            for widget in (item, top, message_body):
                widget.bind(
                    "<Button-1>",
                    lambda e, mid=message_id:
                        self.message_conversation(mid)
                )
    
    
    def demo_payment(self, reservation_id):
        con = connect()

        try:
            reservation = con.execute(
                """
                SELECT total, status, payment_method
                FROM reservations
                WHERE id=? AND customer=?
                """,
                (reservation_id, self.user[0])
            ).fetchone()

            if not reservation:
                messagebox.showerror(
                    "Reservation Not Found",
                    "The selected reservation could not be found."
                )
                return

            total, status, payment_method = reservation

            paid_row = con.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM payments
                WHERE reservation_id=? AND status='Paid'
                """,
                (reservation_id,)
            ).fetchone()

            already_paid = float(paid_row[0] or 0)

        except Exception as e:
            messagebox.showerror(
                "Checkout Error",
                str(e)
            )
            return

        finally:
            con.close()

        if status != "Approved":
            messagebox.showwarning(
                "Payment Unavailable",
                "Only approved reservations can be paid."
            )
            return

        total = float(total or 0)
        remaining = round(max(total - already_paid, 0), 2)

        deposit = round(total * 0.20, 2)

        amount_due = min(
            max(deposit - already_paid, 0),
            remaining
        )

        if amount_due <= 0:
            amount_due = remaining

        if amount_due <= 0:
            messagebox.showinfo(
                "Fully Paid",
                "This reservation is already fully paid."
            )
            return

        # =========================
        # CHECKOUT PAGE
        # =========================

        page = self.page(
            "Checkout",
            False,
            "Complete Your Payment"
        )
        
        
        scroll_container = tk.Frame(page, bg=LIGHT)
        scroll_container.pack(
            fill="both",
            expand=True
        )

        canvas = tk.Canvas(
            scroll_container,
            bg=LIGHT,
            highlightthickness=0
        )
        canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = tk.Scrollbar(
            scroll_container,
            orient="vertical",
            command=canvas.yview
        )
        scrollbar.pack(
            side="right",
            fill="y"
        )

        canvas.configure(
            yscrollcommand=scrollbar.set
        )

        content_frame = tk.Frame(
            canvas,
            bg=LIGHT
        )

        canvas_window = canvas.create_window(
            (0, 0),
            window=content_frame,
            anchor="nw"
        )

        def update_scroll_region(event=None):
            canvas.configure(
                scrollregion=canvas.bbox("all")
            )

        def resize_content(event):
            canvas.itemconfigure(
                canvas_window,
                width=event.width
            )

        content_frame.bind(
            "<Configure>",
            update_scroll_region
        )

        canvas.bind(
            "<Configure>",
            resize_content
        )

        def on_mousewheel(event):
            canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )

        canvas.bind_all(
            "<MouseWheel>",
            on_mousewheel
        )


        container = tk.Frame(
            content_frame,
            bg=LIGHT
        )

        container.pack(
            fill="both",
            expand=True,
            padx=35,
            pady=20
        )

        self.label(
            container,
            "Review your reservation before completing checkout.",
            10,
            False,
            MUTED,
            LIGHT
        ).pack(
            anchor="w",
            pady=(4, 18)
        )

        # =========================
        # RESERVATION SUMMARY
        # =========================

        summary = tk.Frame(
            container,
            bg=CARD,
            padx=22,
            pady=18,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        summary.pack(
            fill="x",
            pady=(0, 14)
        )

        self.label(
            summary,
            "RESERVATION SUMMARY",
            10,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w",
            pady=(0, 12)
        )

        self.label(
            summary,
            f"Booking ID: EVT-{datetime.now().year}-{reservation_id:04d}",
            12,
            True,
            TEXT,
            CARD
        ).pack(
            anchor="w",
            pady=3
        )

        self.label(
            summary,
            "Reservation Status: Approved",
            10,
            False,
            GREEN,
            CARD
        ).pack(
            anchor="w",
            pady=3
        )

        # =========================
        # PAYMENT METHOD
        # =========================

        method_card = tk.Frame(
            container,
            bg=CARD,
            padx=22,
            pady=18,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        method_card.pack(
            fill="x",
            pady=(0, 14)
        )

        self.label(
            method_card,
            "CHOOSE PAYMENT METHOD",
            10,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w",
            pady=(0, 10)
        )

        
        available_methods = (
            "GCash",
            "Maya",
            "Bank Transfer",
            "Cash"
        )

        selected_method = tk.StringVar(
            value=(
                payment_method
                if payment_method in available_methods
                else "GCash"
            )
        )

        for method in available_methods:
            tk.Radiobutton(
                method_card,
                text=method,
                variable=selected_method,
                value=method,
                bg=CARD,
                fg=TEXT,
                activebackground=CARD,
                activeforeground=PURPLE,
                selectcolor="#EEE7FA",
                font=("Segoe UI", 10),
                cursor="hand2"
            ).pack(
                anchor="w",
                pady=5
            )


        # =========================
        # PAYMENT BREAKDOWN
        # =========================

        breakdown = tk.Frame(
            container,
            bg=CARD,
            padx=22,
            pady=18,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        breakdown.pack(
            fill="x",
            pady=(0, 14)
        )

        self.label(
            breakdown,
            "PAYMENT BREAKDOWN",
            10,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w",
            pady=(0, 12)
        )

        def amount_row(
            label_text,
            value,
            color=TEXT,
            bold=False
        ):
            row = tk.Frame(
                breakdown,
                bg=CARD
            )

            row.pack(
                fill="x",
                pady=5
            )

            self.label(
                row,
                label_text,
                10,
                bold,
                TEXT,
                CARD
            ).pack(
                side="left"
            )

            self.label(
                row,
                money(value),
                10,
                bold,
                color,
                CARD
            ).pack(
                side="right"
            )

        amount_row(
            "Reservation Total",
            total
        )

        amount_row(
            "Previously Paid",
            already_paid
        )

        amount_row(
            "Remaining Balance",
            remaining,
            PURPLE,
            True
        )

        tk.Frame(
            breakdown,
            bg=BORDER,
            height=1
        ).pack(
            fill="x",
            pady=10
        )

        amount_row(
            "Amount Due Now",
            amount_due,
            GREEN,
            True
        )

        # =========================
        # CHECKOUT ACTIONS
        # =========================

        actions = tk.Frame(
            container,
            bg=LIGHT
        )

        actions.pack(
            fill="x",
            pady=(2, 0)
        )

        self.button(
            actions,
            f"Pay {money(amount_due)}",
            lambda: self.record_demo_payment(
                reservation_id,
                amount_due,
                selected_method.get()
            ),
            True
        ).pack(
            side="left",
            padx=(0, 10)
        )

        self.button(
            actions,
            "Back to My Reservations",
            self.my_reservations,
            False
        ).pack(
            side="left"
        )
                
    
    def message_conversation(self, message_id):
        ensure_message_tables()

        con = connect()
        try:
            selected = con.execute(
                """
                SELECT id, sender, recipient, sender_role, message,
                    created_at, is_read, important
                FROM messages
                WHERE id=?
                """,
                (message_id,)
            ).fetchone()

            if not selected:
                messagebox.showerror("Messages", "Message not found.")
                return

            (
                msg_id, sender, recipient, sender_role,
                message, created_at, is_read, important
            ) = selected

            con.execute(
                "UPDATE messages SET is_read=1 WHERE id=?",
                (message_id,)
            )
            con.commit()

            conversation = con.execute(
                """
                SELECT sender, sender_role, message, created_at
                FROM messages
                WHERE
                    (
                        recipient=?
                        AND (
                            LOWER(sender)=LOWER(?)
                            OR LOWER(sender)=LOWER(?)
                        )
                    )
                    OR
                    (
                        LOWER(sender)=LOWER(?)
                        AND recipient=?
                    )
                ORDER BY id ASC
                """,
                (
                    self.user[0],
                    "admin",
                    "EventHub Admin",
                    self.user[0],
                    "admin"
                )
            ).fetchall()

        except Exception as e:
            messagebox.showerror("Messages", str(e))
            return
        finally:
            con.close()

        # =========================
        # PAGE
        # =========================
        page = self.page(
            "Messages",
            admin=False,
            title="Messages"
        )

        # =========================
        # HEADER
        # =========================
        header = tk.Frame(
            page,
            bg=CARD,
            height=65,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        header.pack(fill="x", padx=35, pady=(20, 0))
        header.pack_propagate(False)

        tk.Button(
            header,
            text="←",
            command=self.customer_messages,
            bg=CARD,
            fg=PURPLE,
            activebackground=CARD,
            activeforeground=PURPLE,
            relief="flat",
            bd=0,
            font=("Segoe UI", 18, "bold"),
            cursor="hand2"
        ).pack(side="left", padx=(15, 8))

        tk.Label(
            header,
            text="✉",
            bg=PURPLE2,
            fg="white",
            font=("Segoe UI", 12, "bold"),
            width=3
        ).pack(side="left", padx=5)

        info = tk.Frame(header, bg=CARD)
        info.pack(side="left", padx=10)

        self.label(
            info, "Admin", 12, True, PURPLE, CARD
        ).pack(anchor="w")

        self.label(
            info, "● Online", 8, False, GREEN, CARD
        ).pack(anchor="w")

        # =========================
        # CONVERSATION AREA
        # =========================
        chat_container = tk.Frame(page, bg=LIGHT)
        chat_container.pack(
            fill="both",
            expand=True,
            padx=35
        )

        chat_canvas = tk.Canvas(
            chat_container,
            bg=LIGHT,
            highlightthickness=0,
            borderwidth=0
        )

        chat_scroll = ttk.Scrollbar(
            chat_container,
            orient="vertical",
            command=chat_canvas.yview
        )

        chat_frame = tk.Frame(chat_canvas, bg=LIGHT)

        chat_window = chat_canvas.create_window(
            (0, 0),
            window=chat_frame,
            anchor="nw"
        )

        chat_canvas.configure(
            yscrollcommand=chat_scroll.set
        )

        def update_chat_scroll(event=None):
            bbox = chat_canvas.bbox("all")
            if bbox:
                chat_canvas.configure(scrollregion=bbox)

        def resize_chat(event):
            chat_canvas.itemconfigure(
                chat_window,
                width=event.width
            )

        chat_frame.bind("<Configure>", update_chat_scroll)
        chat_canvas.bind("<Configure>", resize_chat)

        # =========================
        # LOAD ALL MESSAGES FIRST
        # =========================
        for chat_sender, chat_role, chat_message, chat_time in conversation:
            is_customer = (chat_role or "").lower() == "customer"
            bubble_color = "#E7DDFC" if is_customer else CARD

            bubble_row = tk.Frame(chat_frame, bg=LIGHT)
            bubble_row.pack(
                fill="x",
                pady=6,
                padx=15
            )

            bubble = tk.Frame(
                bubble_row,
                bg=bubble_color,
                padx=14,
                pady=10,
                highlightbackground=BORDER,
                highlightthickness=1
            )
            bubble.pack(
                side="right" if is_customer else "left"
            )

            self.label(
                bubble,
                chat_message,
                10,
                False,
                TEXT,
                bubble_color,
                wraplength=500,
                justify="left"
            ).pack(anchor="w")

            self.label(
                bubble,
                chat_time,
                8,
                False,
                MUTED,
                bubble_color
            ).pack(anchor="e", pady=(5, 0))

        # =========================
        # COMPOSE MESSAGE
        # =========================
        compose = tk.Frame(
            page,
            bg=CARD,
            padx=12,
            pady=10,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        compose.pack(
            fill="x",
            padx=35,
            pady=(0, 20)
        )

        entry = tk.Entry(
            compose,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1
        )
        entry.pack(
            side="left",
            fill="x",
            expand=True,
            ipady=8,
            padx=(0, 10)
        )

        # =========================
        # SHOW CHAT AT THE BOTTOM
        # =========================
        def show_latest_message():
            if not chat_canvas.winfo_exists():
                return

            chat_frame.update_idletasks()

            bbox = chat_canvas.bbox("all")
            if bbox:
                chat_canvas.configure(scrollregion=bbox)
                chat_canvas.yview_moveto(1.0)

        chat_canvas.pack(side="left", fill="both", expand=True)
        chat_scroll.pack(side="right", fill="y")

        chat_canvas.after(100, show_latest_message)

        # =========================
        # MOUSEWHEEL
        # =========================
        def chat_mousewheel(event):
            if chat_canvas.winfo_exists():
                chat_canvas.yview_scroll(
                    int(-1 * (event.delta / 120)),
                    "units"
                )

        def enable_chat_scroll(event):
            chat_canvas.bind_all("<MouseWheel>", chat_mousewheel)

        def disable_chat_scroll(event):
            chat_canvas.unbind_all("<MouseWheel>")

        chat_canvas.bind("<Enter>", enable_chat_scroll)
        chat_canvas.bind("<Leave>", disable_chat_scroll)

        # =========================
        # SEND REPLY
        # =========================
        def send_reply():
            text = entry.get().strip()
            if not text:
                return

            created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

            con = connect()
            try:
                con.execute(
                    """
                    INSERT INTO messages
                    (
                        sender, recipient, sender_role,
                        message, created_at, is_read, important
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.user[0],
                        "admin",
                        "customer",
                        text,
                        created_at,
                        0,
                        0
                    )
                )
                con.commit()
            except Exception as e:
                messagebox.showerror("Send Message Error", str(e))
                return
            finally:
                con.close()

            entry.delete(0, tk.END)

            bubble_row = tk.Frame(chat_frame, bg=LIGHT)
            bubble_row.pack(fill="x", pady=6, padx=15)

            bubble = tk.Frame(
                bubble_row,
                bg="#E7DDFC",
                padx=14,
                pady=10,
                highlightbackground=BORDER,
                highlightthickness=1
            )
            bubble.pack(side="right")

            self.label(
                bubble,
                text,
                10,
                False,
                TEXT,
                "#E7DDFC",
                wraplength=500,
                justify="left"
            ).pack(anchor="w")

            self.label(
                bubble,
                created_at,
                8,
                False,
                MUTED,
                "#E7DDFC"
            ).pack(anchor="e", pady=(5, 0))

            chat_frame.update_idletasks()
            update_chat_scroll()
            chat_canvas.yview_moveto(1.0)
            entry.focus_set()

        self.button(
            compose,
            "➤",
            send_reply,
            True
        ).pack(side="right")

    #===RECORD DEMO
    def record_demo_payment(
        self,
        reservation_id,
        amount,
        selected_method=None
    ):

        con = connect()

        try:
            reservation = con.execute(
                """
                SELECT total, status
                FROM reservations
                WHERE id=? AND customer=?
                """,
                (reservation_id, self.user[0])
            ).fetchone()

            if not reservation:
                messagebox.showerror(
                    "Payment Error",
                    "Reservation not found."
                )
                return

            total, status = reservation

            if status != "Approved":
                messagebox.showwarning(
                    "Payment Unavailable",
                    "Only approved reservations can be paid."
                )
                return

            paid = con.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM payments
                WHERE reservation_id=? AND status='Paid'
                """,
                (reservation_id,)
            ).fetchone()[0] or 0

            remaining = round(total - paid, 2)
            amount = round(float(amount), 2)

            if amount <= 0 or amount > remaining:
                messagebox.showerror(
                    "Payment Error",
                    "Invalid payment amount."
                )
                return

            payment_method = selected_method or "GCash"

            con.execute(
                """
                INSERT INTO payments(
                    reservation_id,
                    amount,
                    payment_type,
                    payment_method,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, 'Paid', ?)
                """,
                (
                    reservation_id,
                    amount,
                    "Demo Payment",
                    payment_method,
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )
            )
            con.commit()

            total_paid = round(paid + amount, 2)
            remaining_balance = round(
                max(total - total_paid, 0), 2
            )

            self.show_payment_success(
                amount,
                total_paid,
                remaining_balance,
                payment_method,
                reservation_id
            )

            self.generate_payment_receipt(
                reservation_id,
                amount,
                total_paid,
                remaining_balance,
                payment_method
            )

        except Exception as e:
            con.rollback()
            messagebox.showerror(
                "Payment Error",
                str(e)
            )

        finally:
            con.close()

        self.my_reservations()
        
    
    def show_payment_success(
        self,
        amount,
        total_paid,
        remaining_balance,
        payment_method,
        reservation_id
    ):
        success = tk.Toplevel(self)
        success.title("Payment Successful")
        success.configure(bg=LIGHT)
        success.resizable(False, False)
        success.transient(self)
        success.grab_set()

        width, height = 540, 580
        x = (success.winfo_screenwidth() - width) // 2
        y = (success.winfo_screenheight() - height) // 2
        success.geometry(f"{width}x{height}+{x}+{y}")

        card = tk.Frame(success, bg=CARD, padx=30, pady=25)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(
            card,
            text="✓",
            font=("Segoe UI", 54, "bold"),
            bg=CARD,
            fg="#20B875"
        ).pack(pady=(5, 0))

        self.label(
            card,
            "Payment Successful!",
            22,
            True,
            PURPLE,
            CARD
        ).pack(pady=(0, 5))

        self.label(
            card,
            "Your payment has been recorded successfully.",
            10,
            False,
            MUTED,
            CARD
        ).pack(pady=(0, 22))

        info = tk.Frame(
            card,
            bg="#F3EDFC",
            padx=18,
            pady=15
        )
        info.pack(fill="x", pady=(0, 20))

        details = [
            ("Amount Paid:", money(amount)),
            ("Total Paid:", money(total_paid)),
            ("Remaining Balance:", money(remaining_balance)),
            ("Payment Method:", payment_method),
            (
                "Reservation ID:",
                f"EVT-{datetime.now().year}-{reservation_id:04d}"
            )
        ]

        for title, value in details:
            row = tk.Frame(info, bg="#F3EDFC")
            row.pack(fill="x", pady=7)

            tk.Label(
                row,
                text=title,
                font=("Segoe UI", 10),
                bg="#F3EDFC",
                fg=TEXT
            ).pack(side="left")

            tk.Label(
                row,
                text=value,
                font=("Segoe UI", 10, "bold"),
                bg="#F3EDFC",
                fg=PURPLE if title == "Amount Paid:" else TEXT
            ).pack(side="right")

        self.button(
            card,
            "OK",
            success.destroy,
            True
        ).pack(fill="x", ipady=5)

        success.wait_window()

    
    
    def generate_payment_receipt(
        self,
        reservation_id,
        amount_paid,
        total_paid,
        remaining_balance,
        payment_method
    ):
        import os
        from datetime import datetime
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas

        receipt_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "receipts"
        )
        os.makedirs(receipt_folder, exist_ok=True)

        now = datetime.now()
        receipt_number = f"EVT-{now.year}-{reservation_id:04d}"

        receipt_path = os.path.join(
            receipt_folder,
            f"payment_receipt_{reservation_id}_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
        )

        con = connect()

        reservation = con.execute(
            """
            SELECT customer, event_type, event_date, guests, total
            FROM reservations
            WHERE id=? AND customer=?
            """,
            (reservation_id, self.user[0])
        ).fetchone()

        packages = con.execute(
            """
            SELECT r.catering_id, r.photography_id,
                r.venue_id, r.styling_id
            FROM reservations r
            WHERE r.id=? AND r.customer=?
            """,
            (reservation_id, self.user[0])
        ).fetchone()

        con.close()

        if not reservation:
            messagebox.showerror(
                "Receipt Error",
                "Reservation not found."
            )
            return

        customer, event_type, event_date, guests, reservation_total = reservation

        package_columns = [
            ("Catering", packages[0]),
            ("Photography", packages[1]),
            ("Venue", packages[2]),
            ("Event Styling & Decoration", packages[3])
        ]

        selected_packages = []

        for category, package_id in package_columns:
            if not package_id:
                continue

            try:
                package_info = package(package_id)

                if package_info:
                    if isinstance(package_info, (tuple, list)):
                        package_name = (
                            str(package_info[1])
                            if len(package_info) > 1
                            else str(package_info[0])
                        )
                    else:
                        package_name = str(package_info)

                    selected_packages.append((category, package_name))
            except Exception:
                continue

        # Colors
        purple = colors.HexColor("#482477")
        dark_purple = colors.HexColor("#301456")
        lavender = colors.HexColor("#EEE3FF")
        pale_lavender = colors.HexColor("#F8F4FF")
        border = colors.HexColor("#E2D5F4")
        muted = colors.HexColor("#68617B")
        green = colors.HexColor("#16845B")
        white = colors.white
        black = colors.HexColor("#252033")

        pdf = canvas.Canvas(receipt_path, pagesize=A4)
        width, height = A4

        # Page background and border
        pdf.setFillColor(white)
        pdf.rect(0, 0, width, height, fill=1, stroke=0)

        pdf.setStrokeColor(border)
        pdf.setLineWidth(1.2)
        pdf.rect(8 * mm, 8 * mm, width - 16 * mm, height - 16 * mm)

        # Decorative purple header waves
        pdf.setFillColor(lavender)
        path = pdf.beginPath()
        path.moveTo(10 * mm, height - 10 * mm)
        path.lineTo(width - 10 * mm, height - 10 * mm)
        path.lineTo(width - 10 * mm, height - 31 * mm)
        path.curveTo(
            width - 45 * mm, height - 15 * mm,
            width - 60 * mm, height - 42 * mm,
            width - 95 * mm, height - 24 * mm
        )
        path.curveTo(
            width - 125 * mm, height - 10 * mm,
            width - 155 * mm, height - 40 * mm,
            10 * mm, height - 25 * mm
        )
        path.close()
        pdf.drawPath(path, fill=1, stroke=0)

        # Brand
        pdf.setFillColor(purple)
        pdf.setFont("Helvetica-Bold", 27)
        pdf.drawString(24 * mm, height - 31 * mm, "♡ EventHub")

        pdf.setFillColor(purple)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(
            25 * mm,
            height - 39 * mm,
            "E V E N T   P A C K A G E   B O O K I N G   A N D   M A R K E T P L A C E"
        )

        # Receipt metadata
        meta_x = width - 62 * mm
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 7)
        pdf.drawString(meta_x, height - 20 * mm, "RECEIPT NO.")

        pdf.setFillColor(dark_purple)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(meta_x, height - 26 * mm, receipt_number)

        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 7)
        pdf.drawString(meta_x, height - 34 * mm, "ISSUED ON")

        pdf.setFillColor(dark_purple)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(meta_x, height - 40 * mm, now.strftime("%B %d, %Y"))

        pdf.setFont("Helvetica", 8)
        pdf.drawString(meta_x, height - 45 * mm, now.strftime("%I:%M %p"))

        # Main title
        pdf.setFillColor(dark_purple)
        pdf.setFont("Helvetica-Bold", 25)
        pdf.drawString(24 * mm, height - 55 * mm, "PAYMENT RECEIPT")

        pdf.setFillColor(muted)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(
            24 * mm,
            height - 63 * mm,
            "T H A N K   Y O U   F O R   Y O U R   P A Y M E N T!"
        )

        pdf.setStrokeColor(colors.HexColor("#C79BFF"))
        pdf.setLineWidth(1.1)
        pdf.line(
            24 * mm, height - 69 * mm,
            width - 24 * mm, height - 69 * mm
        )

        # Information columns
        left_x = 24 * mm
        right_x = 112 * mm
        label_offset = 31 * mm
        info_top = height - 80 * mm
        line_gap = 7 * mm

        pdf.setFillColor(purple)
        pdf.circle(left_x + 5 * mm, info_top + 1 * mm, 4 * mm, fill=1, stroke=0)
        pdf.setFillColor(white)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawCentredString(left_x + 5 * mm, info_top - 1 * mm, "U")

        pdf.setFillColor(purple)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left_x + 12 * mm, info_top, "CUSTOMER INFORMATION")

        pdf.setFillColor(purple)
        pdf.circle(right_x + 5 * mm, info_top + 1 * mm, 4 * mm, fill=1, stroke=0)
        pdf.setFillColor(white)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawCentredString(right_x + 5 * mm, info_top - 1 * mm, "$")

        pdf.setFillColor(purple)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(right_x + 12 * mm, info_top, "PAYMENT INFORMATION")

        # Vertical divider
        pdf.setStrokeColor(border)
        pdf.line(
            105 * mm, info_top + 3 * mm,
            105 * mm, info_top - 34 * mm
        )

        def draw_info(x, y, label, value, value_x=None):
            pdf.setFillColor(muted)
            pdf.setFont("Helvetica", 8.5)
            pdf.drawString(x, y, label)

            pdf.setFillColor(black)
            pdf.setFont("Helvetica", 8.5)
            pdf.drawString(
                value_x if value_x is not None else x + label_offset,
                y,
                str(value)[:38]
            )

        info_y = info_top - 10 * mm

        customer_rows = [
            ("Customer:", customer),
            ("Reservation ID:", receipt_number),
            ("Event Type:", event_type),
            ("Event Date:", event_date),
            ("Number of Guests:", guests)
        ]

        for i, (label, value) in enumerate(customer_rows):
            draw_info(left_x, info_y - i * line_gap, label, value)

        payment_rows = [
            ("Payment Method:", payment_method or "Not specified"),
            ("Payment Date:", now.strftime("%B %d, %Y")),
            ("Time:", now.strftime("%I:%M %p")),
            ("Transaction ID:", "N/A")
        ]

        for i, (label, value) in enumerate(payment_rows):
            draw_info(
                right_x,
                info_y - i * line_gap,
                label,
                value,
                value_x=right_x + 32 * mm
            )

        # Payment summary panel
        summary_top = height - 126 * mm
        summary_x = 24 * mm
        summary_w = width - 48 * mm
        summary_h = 51 * mm

        pdf.setFillColor(pale_lavender)
        pdf.roundRect(
            summary_x,
            summary_top - summary_h,
            summary_w,
            summary_h,
            3 * mm,
            fill=1,
            stroke=0
        )

        pdf.setFillColor(lavender)
        pdf.roundRect(
            summary_x,
            summary_top - 11 * mm,
            summary_w,
            11 * mm,
            3 * mm,
            fill=1,
            stroke=0
        )
        pdf.rect(
            summary_x,
            summary_top - 11 * mm,
            summary_w,
            4 * mm,
            fill=1,
            stroke=0
        )

        pdf.setFillColor(purple)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(
            summary_x + 10 * mm,
            summary_top - 7.5 * mm,
            "PAYMENT SUMMARY"
        )

        summary_rows = [
            ("Reservation Total", money(reservation_total)),
            ("Previously Paid", money(max(total_paid - amount_paid, 0))),
            ("Payment Amount", money(amount_paid)),
            ("Total Paid", money(total_paid))
        ]

        row_y = summary_top - 18 * mm

        for label, value in summary_rows:
            pdf.setFillColor(black if label == "Total Paid" else muted)
            pdf.setFont(
                "Helvetica-Bold" if label in ("Payment Amount", "Total Paid") else "Helvetica",
                9
            )
            pdf.drawString(summary_x + 12 * mm, row_y, label)

            pdf.setFillColor(dark_purple if label == "Payment Amount" else black)
            pdf.drawRightString(
                summary_x + summary_w - 10 * mm,
                row_y,
                value
            )
            row_y -= 6 * mm

            if label == "Payment Amount":
                pdf.setStrokeColor(border)
                pdf.line(
                    summary_x + 10 * mm,
                    row_y + 2 * mm,
                    summary_x + summary_w - 10 * mm,
                    row_y + 2 * mm
                )

        # Remaining balance highlight
        balance_y = summary_top - summary_h + 4 * mm

        pdf.setFillColor(lavender)
        pdf.roundRect(
            summary_x + 5 * mm,
            balance_y,
            summary_w - 10 * mm,
            8 * mm,
            2 * mm,
            fill=1,
            stroke=0
        )

        pdf.setFillColor(purple)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(
            summary_x + 8 * mm,
            balance_y + 2.7 * mm,
            "Remaining Balance"
        )

        pdf.drawRightString(
            summary_x + summary_w - 8 * mm,
            balance_y + 2.7 * mm,
            money(remaining_balance)
        )

        # Selected packages table
        table_title_y = summary_top - summary_h - 12 * mm

        pdf.setFillColor(purple)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(24 * mm, table_title_y, "SELECTED PACKAGES")

        table_x = 24 * mm
        table_top = table_title_y - 5 * mm
        table_w = width - 48 * mm
        col1 = 75 * mm
        header_h = 8 * mm
        row_h = 7 * mm

        pdf.setFillColor(lavender)
        pdf.roundRect(
            table_x,
            table_top - header_h,
            table_w,
            header_h,
            2 * mm,
            fill=1,
            stroke=0
        )

        pdf.setFillColor(dark_purple)
        pdf.setFont("Helvetica-Bold", 7.5)
        pdf.drawString(table_x + 6 * mm, table_top - 5.3 * mm, "CATEGORY")
        pdf.drawString(table_x + col1, table_top - 5.3 * mm, "PACKAGE NAME")

        rows = selected_packages or [("Packages", "No package information available")]

        row_y = table_top - header_h

        for category, name in rows[:6]:
            row_y -= row_h

            pdf.setFillColor(white if int((table_top - row_y) / row_h) % 2 else pale_lavender)
            pdf.rect(
                table_x,
                row_y,
                table_w,
                row_h,
                fill=1,
                stroke=0
            )

            pdf.setStrokeColor(border)
            pdf.rect(
                table_x,
                row_y,
                table_w,
                row_h,
                fill=0,
                stroke=1
            )
            pdf.line(
                table_x + col1 - 3 * mm,
                row_y,
                table_x + col1 - 3 * mm,
                row_y + row_h
            )

            pdf.setFillColor(muted)
            pdf.setFont("Helvetica", 8)
            pdf.drawString(
                table_x + 6 * mm,
                row_y + 2.3 * mm,
                str(category)[:30]
            )
            pdf.drawString(
                table_x + col1,
                row_y + 2.3 * mm,
                str(name)[:48]
            )

        # Thank-you footer
        footer_y = 27 * mm

        pdf.setFillColor(purple)
        pdf.setFont("Helvetica-BoldOblique", 20)
        pdf.drawString(24 * mm, footer_y + 7 * mm, "Thank You!")

        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 8.5)
        pdf.drawString(
            24 * mm,
            footer_y,
            "We appreciate your trust in EventHub."
        )
        pdf.drawString(
            24 * mm,
            footer_y - 5 * mm,
            "We look forward to making your event special!"
        )

        pdf.setFillColor(purple)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawRightString(
            width - 24 * mm,
            footer_y + 4 * mm,
            "♡ EventHub"
        )

        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 6.5)
        pdf.drawRightString(
            width - 24 * mm,
            footer_y - 2 * mm,
            "EVENT PACKAGE BOOKING"
        )
        pdf.drawRightString(
            width - 24 * mm,
            footer_y - 6 * mm,
            "AND MARKETPLACE SYSTEM"
        )

        pdf.save()

        messagebox.showinfo(
            "Receipt Created",
            f"Payment receipt created successfully:\n\n{receipt_path}"
        )

        os.startfile(receipt_path)

        
    def send_system_message(
        self,
        customer,
        subject,
        message,
        important=False
    ):
        ensure_message_tables()

        con = connect()

        con.execute(
            """
            INSERT INTO messages
            (
                sender,
                recipient,
                sender_role,
                message,
                created_at,
                is_read,
                important
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "EventHub Admin",
                customer,
                "admin",
                f"{subject}\n\n{message}",
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                0,
                1 if important else 0
            )
        )

        con.commit()
        con.close()

    
    
    def profile(self):
        page = self.page("Profile", False, "")

        con = connect()

        try:
            customer_info = con.execute(
                """
                SELECT full_name, username, email, contact
                FROM users
                WHERE username = ?
                AND role = 'customer'
                """,
                (self.user[0],)
            ).fetchone()
        finally:
            con.close()

        if not customer_info:
            messagebox.showerror(
                "Profile",
                "Unable to load customer information."
            )
            return

        full_name, username, email, contact = customer_info

        # Fixed Profile Content - No Scrolling
        container = tk.Frame(page, bg=LIGHT)
        container.pack(fill="both", expand=True)

        # Header Banner
        banner = tk.Frame(
            container,
            bg="#30204F",
            padx=25,
            pady=25
        )
        banner.pack(
            fill="x",
            padx=25,
            pady=(20, 20)
        )

        header = tk.Frame(banner, bg="#30204F")
        header.pack(fill="x")

        avatar = tk.Label(
            header,
            text="👤",
            font=("Segoe UI Emoji", 30),
            bg="#E9DDFB",
            fg="#5C3B8D",
            width=3,
            height=1
        )
        avatar.pack(side="left", padx=(0, 18))

        title_frame = tk.Frame(header, bg="#30204F")
        title_frame.pack(side="left", fill="x", expand=True)

        tk.Label(
            title_frame,
            text=f"Hello, {self.user[0]}!",
            font=("Segoe UI", 21, "bold"),
            bg="#30204F",
            fg="white"
        ).pack(anchor="w")

        tk.Label(
            title_frame,
            text="Here's your account overview.",
            font=("Segoe UI", 10),
            bg="#30204F",
            fg="#E4D8F5"
        ).pack(anchor="w", pady=(4, 0))

        tk.Label(
            banner,
            text="●  Active Account",
            font=("Segoe UI", 10, "bold"),
            bg="#30204F",
            fg="#86EFAC"
        ).pack(anchor="w", pady=(18, 0))

        # Personal Information Card
        info_card = tk.Frame(
            container,
            bg=CARD,
            padx=25,
            pady=22,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        info_card.pack(
            fill="x",
            padx=25,
            pady=(0, 20)
        )

        heading = tk.Frame(info_card, bg=CARD)
        heading.pack(fill="x", pady=(0, 18))

        tk.Label(
            heading,
            text="Personal Information",
            font=("Segoe UI", 14, "bold"),
            bg=CARD,
            fg="#30204F"
        ).pack(side="left")


        # Customer information from database
        profile_fields = [
            ("Full Name", "full_name", full_name),
            ("Username", "username", username),
            ("Email Address", "email", email),
            ("Contact Number", "contact_number", contact),
        ]

        entries = {}

        for label_text, field_name, field_value in profile_fields:
            row = tk.Frame(info_card, bg=CARD)
            row.pack(fill="x", pady=8)

            tk.Label(
                row,
                text=label_text,
                font=("Segoe UI", 9),
                bg=CARD,
                fg=MUTED,
                width=18,
                anchor="w"
            ).pack(side="left")

            entry = tk.Entry(
                row,
                font=("Segoe UI", 10),
                bg=CARD,
                fg=TEXT,
                relief="flat",
                bd=0,
                highlightthickness=0,
                readonlybackground=CARD
            )

            entry.insert(0, field_value or "")
            entry.config(state="readonly")
            entry.pack(
                side="left",
                fill="x",
                expand=True,
                ipady=8
            )

            entries[field_name] = entry

            tk.Frame(
                info_card,
                bg=BORDER,
                height=1
            ).pack(fill="x", pady=(4, 0))

    # ---------------- ADMIN ----------------

    def admin_dashboard(self):
        page = self.page("Dashboard", True, "")

        # Keep the existing scroll behavior
        wrapper = tk.Frame(page, bg=LIGHT)
        wrapper.pack(fill="both", expand=True)

        canvas = tk.Canvas(wrapper, bg=LIGHT, highlightthickness=0)
        scrollbar = tk.Scrollbar(
            wrapper, orient="vertical", command=canvas.yview
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        content = tk.Frame(canvas, bg=LIGHT)
        window_id = canvas.create_window(
            (0, 0), window=content, anchor="nw"
        )

        def update_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def resize_content(event):
            canvas.itemconfigure(window_id, width=event.width)

        content.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", resize_content)

        def on_mousewheel(event):
            if event.delta:
                canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"

        def bind_mousewheel(widget):
            widget.bind("<MouseWheel>", on_mousewheel, add="+")
            for child in widget.winfo_children():
                bind_mousewheel(child)

        # Database queries: preserve existing data sources
        con = connect()
        try:
            customers = con.execute(
                "SELECT COUNT(DISTINCT customer) FROM reservations"
            ).fetchone()[0]

            pending = con.execute(
                "SELECT COUNT(*) FROM reservations WHERE status='Pending'"
            ).fetchone()[0]

            approved = con.execute(
                "SELECT COUNT(*) FROM reservations WHERE status='Approved'"
            ).fetchone()[0]

            cancelled = con.execute(
                "SELECT COUNT(*) FROM reservations WHERE status='Cancelled'"
            ).fetchone()[0]

            revenue = con.execute("""
                SELECT COALESCE(SUM(amount), 0)
                FROM payments
                WHERE status='Paid'
            """).fetchone()[0]

            upcoming = con.execute("""
                SELECT event_date, event_type, customer, status
                FROM reservations
                WHERE date(event_date) >= date('now')
                AND status IN ('Pending', 'Approved')
                ORDER BY date(event_date) ASC
                LIMIT 11
            """).fetchall()

            popular = con.execute("""
                SELECT package_id, COUNT(*) AS total
                FROM (
                    SELECT catering_id AS package_id
                    FROM reservations
                    WHERE catering_id IS NOT NULL
                    UNION ALL
                    SELECT photography_id
                    FROM reservations
                    WHERE photography_id IS NOT NULL
                    UNION ALL
                    SELECT venue_id
                    FROM reservations
                    WHERE venue_id IS NOT NULL
                    UNION ALL
                    SELECT styling_id
                    FROM reservations
                    WHERE styling_id IS NOT NULL
                )
                GROUP BY package_id
                ORDER BY total DESC
                LIMIT 5
            """).fetchall()

            popular_packages = []
            for package_id, count in popular:
                result = con.execute(
                    "SELECT name FROM packages WHERE id=?",
                    (package_id,)
                ).fetchone()
                if result:
                    popular_packages.append((result[0], count))
        finally:
            con.close()

        # Header
        header = tk.Frame(content, bg=LIGHT)
        header.pack(fill="x", padx=30, pady=(18, 4))

        title_row = tk.Frame(header, bg=LIGHT)
        title_row.pack(fill="x")

        self.label(
            title_row, "Admin Dashboard", 25, True, PURPLE, LIGHT
        ).pack(side="left", anchor="w")

        today_box = tk.Frame(title_row, bg=LIGHT)
        today_box.pack(side="right", anchor="e")

        self.label(
            today_box, "TODAY", 9, True, PURPLE2, LIGHT
        ).pack(anchor="e")

        self.label(
            today_box,
            __import__("datetime").date.today().strftime("%b %d, %Y"),
            9, False, MUTED, LIGHT
        ).pack(anchor="e")

        self.label(
            header, "Manage your events, packages and customers.",
            11, False, MUTED, LIGHT
        ).pack(anchor="w", pady=(3, 0))

        # Statistics cards
        cards = tk.Frame(content, bg=LIGHT)
        cards.pack(fill="x", padx=25, pady=(24, 20))

        stats = [
            ("Total Customers", customers, PURPLE2),
            ("Pending Reservations", pending, ORANGE),
            ("Approved Bookings", approved, GREEN),
            ("Cancelled Bookings", cancelled, RED),
        ]

        for title, value, accent in stats:
            card = tk.Frame(
                cards, bg=CARD, padx=0, pady=0,
                highlightbackground=BORDER, highlightthickness=1
            )
            card.pack(
                side="left", fill="both", expand=True, padx=6
            )

            accent_line = tk.Frame(card, bg=accent, width=4)
            accent_line.pack(side="left", fill="y")

            body = tk.Frame(card, bg=CARD, padx=16, pady=17)
            body.pack(side="left", fill="both", expand=True)

            self.label(
                body, title, 10, False, MUTED, CARD
            ).pack(anchor="w", pady=(0, 8))

            self.label(
                body, str(value), 23, True, TEXT, CARD
            ).pack(anchor="w")

        # Main two-column layout
        lower = tk.Frame(content, bg=LIGHT)
        lower.pack(fill="x", padx=30, pady=(0, 25))

        lower.grid_columnconfigure(0, weight=11, uniform="dashboard")
        lower.grid_columnconfigure(1, weight=10, uniform="dashboard")

        # Upcoming Events card
        events_card = tk.Frame(
            lower, bg=CARD, padx=18, pady=17,
            highlightbackground=BORDER, highlightthickness=1
        )
        events_card.grid(
            row=0, column=0, sticky="nsew", padx=(0, 9)
        )

        events_heading = tk.Frame(events_card, bg=CARD)
        events_heading.pack(fill="x", pady=(0, 15))

        self.label(
            events_heading, "Upcoming Events", 15, True, PURPLE, CARD
        ).pack(anchor="w")

        self.label(
            events_heading, "Upcoming customer reservations",
            9, False, MUTED, CARD
        ).pack(anchor="w", pady=(4, 0))

        # Header and rows use the same grid columns
        table = tk.Frame(events_card, bg=CARD)
        table.pack(fill="x")

        column_weights = [13, 14, 13, 12, 9]
        column_names = [
            "Date", "Event Type", "Customer", "Status", "Action"
        ]

        for col, weight in enumerate(column_weights):
            table.grid_columnconfigure(col, weight=weight, uniform="event_cols")

        table_header = tk.Frame(table, bg="#F1EBFA")
        table_header.grid(row=0, column=0, columnspan=5, sticky="ew")

        for col, text in enumerate(column_names):
            tk.Label(
                table_header, text=text,
                font=("Segoe UI", 9, "bold"),
                bg="#F1EBFA", fg=PURPLE,
                anchor="w", padx=5, pady=10
            ).grid(row=0, column=col, sticky="ew")

            table_header.grid_columnconfigure(
                col, weight=column_weights[col], uniform="event_cols"
            )

        for index, (event_date, event_type, customer, status) in enumerate(upcoming):
            row = tk.Frame(table, bg=CARD)
            row.grid(
                row=index + 1, column=0, columnspan=5, sticky="ew",
                pady=(5, 3)
            )

            for col, weight in enumerate(column_weights):
                row.grid_columnconfigure(
                    col, weight=weight, uniform="event_cols"
                )

            values = [event_date, event_type, customer]
            for col, value in enumerate(values):
                tk.Label(
                    row, text=str(value),
                    font=("Segoe UI", 9),
                    bg=CARD, fg=TEXT, anchor="w",
                    padx=5, pady=9
                ).grid(row=0, column=col, sticky="ew")

            approved_status = status == "Approved"
            status_bg = "#DDF5E9" if approved_status else "#FFF0D8"
            status_fg = GREEN if approved_status else ORANGE

            tk.Label(
                row, text=str(status),
                font=("Segoe UI", 8, "bold"),
                bg=status_bg, fg=status_fg,
                padx=5, pady=5
            ).grid(row=0, column=3, sticky="ew", padx=3)

            tk.Button(
                row, text="View",
                font=("Segoe UI", 8, "bold"),
                bg=CARD, fg=PURPLE2,
                activebackground="#F1EBFA",
                activeforeground=PURPLE2,
                relief="solid", bd=1,
                cursor="hand2", padx=5, pady=4,
                command=lambda: self.admin_reservations()
            ).grid(row=0, column=4, sticky="ew", padx=3)

        if not upcoming:
            self.label(
                events_card, "No upcoming events.",
                10, False, MUTED, CARD
            ).pack(anchor="w", pady=20)

        # Right column
        right = tk.Frame(lower, bg=LIGHT)
        right.grid(row=0, column=1, sticky="nsew", padx=(9, 0))

        # Revenue card
        revenue_card = tk.Frame(
            right, bg=CARD, padx=18, pady=17,
            highlightbackground=BORDER, highlightthickness=1
        )
        revenue_card.pack(fill="x", pady=(0, 12))

        revenue_heading = tk.Frame(revenue_card, bg=CARD)
        revenue_heading.pack(fill="x")

        self.label(
            revenue_heading, "Total Revenue", 14, True, PURPLE, CARD
        ).pack(side="left", anchor="w")

        self.label(
            revenue_card, money(revenue), 24, True, PURPLE, CARD
        ).pack(anchor="w", pady=(10, 8))

        # Chart with clearly labeled demo values
        chart = tk.Canvas(
            revenue_card, height=165, bg=CARD, highlightthickness=0
        )
        chart.pack(fill="x")

        chart_days = ["Oct 6", "Oct 7", "Oct 8", "Oct 9",
                    "Oct 10", "Oct 11", "Oct 12"]
        chart_values = [60, 80, 95, 95, 140, 95, 110]

        def draw_bars(event=None):
            chart.delete("all")

            width = max(chart.winfo_width(), 300)
            height = 165
            left_margin = 36
            right_margin = 8
            top_margin = 8
            bottom_margin = 28
            plot_width = width - left_margin - right_margin
            plot_height = height - top_margin - bottom_margin

            max_value = 150
            for tick in [0, 50, 100, 150]:
                y = top_margin + plot_height * (1 - tick / max_value)
                chart.create_line(
                    left_margin, y, width - right_margin, y,
                    fill="#EEEAF5"
                )
                chart.create_text(
                    left_margin - 5, y, text=str(tick) + "K",
                    anchor="e", fill=MUTED,
                    font=("Segoe UI", 8)
                )

            gap = 9
            bar_width = max(
                10, (plot_width - gap * (len(chart_values) - 1))
                / len(chart_values)
            )

            for i, value in enumerate(chart_values):
                x = left_margin + i * (bar_width + gap)
                bar_height = plot_height * value / max_value
                y = top_margin + plot_height - bar_height

                chart.create_rectangle(
                    x, y, x + bar_width, top_margin + plot_height,
                    fill="#9875F5", outline=""
                )
                chart.create_text(
                    x + bar_width / 2, height - 13,
                    text=chart_days[i], fill=MUTED,
                    font=("Segoe UI", 8)
                )

        chart.bind("<Configure>", draw_bars)
        chart.after(100, draw_bars)

        self.label(
            revenue_card,
            "Illustrative chart values, not recorded daily revenue",
            8, False, MUTED, CARD
        ).pack(anchor="w", pady=(0, 2))

        # Most Selected Packages card
        popular_card = tk.Frame(
            right, bg=CARD, padx=18, pady=17,
            highlightbackground=BORDER, highlightthickness=1
        )
        popular_card.pack(fill="x")

        self.label(
            popular_card, "Most Selected Packages",
            13, True, PURPLE, CARD
        ).pack(anchor="w")

        self.label(
            popular_card, "Based on customer reservations",
            9, False, MUTED, CARD
        ).pack(anchor="w", pady=(4, 14))

        max_count = max(
            (count for _, count in popular_packages), default=1
        )
        rank_colors = ["#8156F5", "#F49A35", "#9875F5", "#AAA1D9", "#C2B9E8"]

        for index, (name, count) in enumerate(popular_packages):
            item = tk.Frame(popular_card, bg=CARD)
            item.pack(fill="x", pady=7)

            rank_color = rank_colors[index % len(rank_colors)]

            tk.Label(
                item, text=str(index + 1),
                font=("Segoe UI", 9, "bold"),
                bg=rank_color, fg="white",
                width=2, pady=4
            ).pack(side="left", padx=(0, 9))

            details = tk.Frame(item, bg=CARD)
            details.pack(side="left", fill="x", expand=True)

            name_row = tk.Frame(details, bg=CARD)
            name_row.pack(fill="x")

            tk.Label(
                name_row, text=name,
                font=("Segoe UI", 9),
                bg=CARD, fg=TEXT, anchor="w"
            ).pack(side="left", fill="x", expand=True)

            tk.Label(
                name_row, text=str(count),
                font=("Segoe UI", 9),
                bg=CARD, fg=TEXT
            ).pack(side="right", padx=(5, 0))

            bar = tk.Canvas(
                details, height=8, bg="#EEEAF5", highlightthickness=0
            )
            bar.pack(fill="x", pady=(6, 0))

            def draw_progress(event, canvas=bar, amount=count):
                canvas.delete("all")
                fill_width = event.width * amount / max_count
                canvas.create_rectangle(
                    0, 0, fill_width, 8,
                    fill="#8156F5", outline=""
                )

            bar.bind("<Configure>", draw_progress)

        if not popular_packages:
            self.label(
                popular_card, "No package selections yet.",
                9, False, MUTED, CARD
            ).pack(anchor="w", pady=15)

        # Bind mouse-wheel scrolling after creating all widgets
        bind_mousewheel(content)




        
    def admin_reservations(self):
        from datetime import datetime, date, timedelta

        page = self.page(
            "Reservations",
            True,
            "Reservation Management"
        )

        # =========================
        # UI COLORS
        # =========================
        BG = LIGHT
        WHITE = "#FFFFFF"
        PURPLE_MAIN = "#633BC4"
        PURPLE_DARK = "#39205F"
        PURPLE_LIGHT = "#F0EAFE"
        BORDER_COLOR = "#E5DFF7"
        MUTED_TEXT = "#77758F"

        # =========================
        # HEADER SUBTITLE
        # Do not add another title here:
        # self.page() already creates the page title.
        # =========================
        subtitle = tk.Label(
            page,
            text="View and manage all customer reservations.",
            font=("Segoe UI", 10),
            bg=BG,
            fg=MUTED_TEXT
        )
        subtitle.pack(anchor="w", padx=30, pady=(0, 12))

        # =========================
        # SEARCH + DATE FILTER
        # =========================
        toolbar = tk.Frame(
            page,
            bg=WHITE,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR
        )
        toolbar.pack(fill="x", padx=25, pady=(0, 10))

        search_var = tk.StringVar()

        search_box = tk.Frame(
            toolbar,
            bg=WHITE,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR
        )
        search_box.pack(
            side="left",
            fill="x",
            expand=True,
            padx=12,
            pady=10
        )

        tk.Label(
            search_box,
            text="⌕",
            font=("Segoe UI", 16, "bold"),
            bg=WHITE,
            fg=PURPLE_MAIN
        ).pack(side="left", padx=(10, 5))

        search_entry = tk.Entry(
            search_box,
            textvariable=search_var,
            font=("Segoe UI", 10),
            relief="flat",
            bd=0,
            bg=WHITE,
            fg=PURPLE_DARK
        )
        search_entry.pack(
            side="left",
            fill="x",
            expand=True,
            ipady=7,
            padx=(0, 10)
        )

        search_entry.insert(0, "Search by reservation ID or customer...")

        def clear_search_placeholder(event):
            if search_entry.get() == "Search by reservation ID or customer...":
                search_entry.delete(0, "end")

        def restore_search_placeholder(event):
            if not search_entry.get().strip():
                search_entry.insert(0, "Search by reservation ID or customer...")

        search_entry.bind("<FocusIn>", clear_search_placeholder)
        search_entry.bind("<FocusOut>", restore_search_placeholder)

        date_filter = tk.StringVar(value="All dates")

        date_button = tk.Menubutton(
            toolbar,
            text="▦  Date Filter  ▾",
            font=("Segoe UI", 9, "bold"),
            bg=WHITE,
            fg=PURPLE_MAIN,
            activebackground=PURPLE_LIGHT,
            relief="solid",
            bd=1,
            padx=12,
            pady=9,
            cursor="hand2"
        )
        date_menu = tk.Menu(date_button, tearoff=0)
        date_button.config(menu=date_menu)

        def choose_date_filter(value):
            date_filter.set(value)
            date_button.config(text=f"▦  {value}  ▾")
            refresh_table(reset_page=True)

        for option in (
            "All dates",
            "Today",
            "Next 7 days",
            "Next 30 days"
        ):
            date_menu.add_command(
                label=option,
                command=lambda value=option: choose_date_filter(value)
            )

        date_button.pack(side="right", padx=12, pady=10)

        # =========================
        # STATUS FILTERS
        # =========================
        filter_frame = tk.Frame(page, bg=BG)
        filter_frame.pack(fill="x", padx=25, pady=(0, 12))

        status_filter = tk.StringVar(value="All")
        filter_buttons = {}

        # =========================
        # TABLE CONTAINER
        # =========================
        table_card = tk.Frame(
            page,
            bg=WHITE,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR
        )
        table_card.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=(0, 10)
        )

        table_inner = tk.Frame(table_card, bg=WHITE)
        table_inner.pack(fill="both", expand=True, padx=10, pady=10)

        columns = (
            "Reservation ID",
            "Customer",
            "Event Type",
            "Event Date",
            "Guests",
            "Total",
            "Status",
            "Action"
        )

        tree = ttk.Treeview(
            table_inner,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        headings = {
            "Reservation ID": "RESERVATION ID",
            "Customer": "CUSTOMER",
            "Event Type": "EVENT TYPE",
            "Event Date": "EVENT DATE",
            "Guests": "GUESTS",
            "Total": "TOTAL",
            "Status": "STATUS",
            "Action": "ACTION"
        }

        widths = {
            "Reservation ID": 145,
            "Customer": 130,
            "Event Type": 120,
            "Event Date": 125,
            "Guests": 75,
            "Total": 125,
            "Status": 115,
            "Action": 120
        }

        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(
                col,
                width=widths[col],
                minwidth=75,
                anchor="center",
                stretch=True
            )

        # =========================
        # TREEVIEW STYLING
        # =========================
        style = ttk.Style()

        style.configure(
            "EventHub.Treeview",
            font=("Segoe UI", 10),
            rowheight=44,
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground="#30204F",
            borderwidth=0,
            relief="flat"
        )

        style.configure(
            "EventHub.Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
            background="#EDE6FA",
            foreground="#39205F",
            relief="flat",
            padding=(10, 13)
        )

        style.map(
            "EventHub.Treeview",
            background=[("selected", "#DED2FA")],
            foreground=[("selected", "#30204F")]
        )

        tree.configure(style="EventHub.Treeview")

        # Malinis at madaling basahing rows
        tree.tag_configure("Pending", background="#FFF8E8", foreground="#805000")
        tree.tag_configure("Approved", background="#EAF8F0", foreground="#176B45")
        tree.tag_configure("Completed", background="#EAF2FF", foreground="#204F9B")
        tree.tag_configure("Cancelled", background="#FFF0F0", foreground="#A52232")
        tree.tag_configure("Alternate", background="#F7F7FC", foreground="#30204F")


        tree.pack(fill="both", expand=True)

        # =========================
        # FOOTER + PAGINATION
        # =========================
        footer = tk.Frame(page, bg=BG)
        footer.pack(fill="x", padx=25, pady=(0, 12))

        result_label = tk.Label(
            footer,
            text="",
            font=("Segoe UI", 9),
            bg=BG,
            fg=MUTED_TEXT
        )
        result_label.pack(side="left")

        pagination = tk.Frame(footer, bg=BG)
        pagination.pack(side="right")

        page_number = {"value": 1}
        page_size = 10
        filtered_rows = []

        # =========================
        # LOAD RESERVATIONS
        # =========================
        con = connect()
        try:
            rows = con.execute("""
                SELECT
                    id,
                    customer,
                    event_type,
                    event_date,
                    guests,
                    total,
                    status
                FROM reservations
                ORDER BY id DESC
            """).fetchall()
        finally:
            con.close()

        # =========================
        # ACTION HANDLER
        # =========================
        def status_change(rid, new_status):
            con = connect()

            try:
                reservation = con.execute("""
                    SELECT
                        status,
                        event_date,
                        catering_id,
                        photography_id,
                        venue_id,
                        styling_id,
                        customer
                    FROM reservations
                    WHERE id=?
                """, (rid,)).fetchone()

                if not reservation:
                    messagebox.showerror(
                        "Reservation Not Found",
                        "This reservation could not be found."
                    )
                    return

                old_status = str(reservation[0] or "").strip().title()

                allowed_actions = {
                    "Pending": ("Approved", "Cancelled"),
                    "Approved": ("Completed", "Cancelled"),
                    "Completed": (),
                    "Cancelled": ()
                }

                if new_status not in allowed_actions.get(old_status, ()):
                    messagebox.showwarning(
                        "Action Not Available",
                        f"A {old_status} reservation cannot be changed "
                        f"to {new_status}."
                    )
                    return

                # Check package availability before approval.
                if new_status == "Approved":
                    event_date = reservation[1]
                    package_ids = reservation[2:6]

                    for package_id in package_ids:
                        if package_id and not is_available(
                            package_id,
                            event_date,
                            rid
                        ):
                            messagebox.showerror(
                                "Cannot Approve",
                                "A selected package conflicts with another booking."
                            )
                            return

                # Update only if the reservation still has its original status.
                cursor = con.execute("""
                    UPDATE reservations
                    SET status=?
                    WHERE id=? AND status=?
                """, (new_status, rid, reservation[0]))

                if cursor.rowcount == 0:
                    messagebox.showwarning(
                        "Reservation Changed",
                        "The reservation status has changed. Refresh and try again."
                    )
                    return

                con.commit()
                customer = reservation[6]

            except Exception as error:
                con.rollback()
                messagebox.showerror(
                    "Database Error",
                    f"Unable to update the reservation.\n\n{error}"
                )
                return
            finally:
                con.close()

            # Customer notifications
            try:
                if new_status == "Approved":
                    self.send_system_message(
                        customer,
                        "Your Reservation Has Been Approved!",
                        "Great news! Your EventHub reservation has been approved. "
                        "Thank you for choosing us. Please review your reservation "
                        "details and keep an eye on your Messages for updates.",
                        False
                    )
                    self.send_system_message(
                        customer,
                        "Initial Deposit Required",
                        "Please pay your initial 20% deposit within 3 days from "
                        "the approval date to secure your booking. Go to My "
                        "Reservations and click Pay Now. Failure to pay within "
                        "3 days may result in cancellation.",
                        False
                    )

                elif new_status == "Cancelled":
                    self.send_system_message(
                        customer,
                        "Your Reservation Has Been Cancelled",
                        "We’re sorry to inform you that your EventHub reservation "
                        "has been cancelled. Please check your reservation details "
                        "or contact the admin through Messages if you have questions.",
                        True
                    )

                elif new_status == "Completed":
                    self.send_system_message(
                        customer,
                        "Thank You for Choosing EventHub!",
                        "Thank you for choosing EventHub for your special event! "
                        "Your reservation is now marked as Completed. We hope you "
                        "had a wonderful experience and look forward to serving you again!",
                        False
                    )
            except Exception as error:
                messagebox.showwarning(
                    "Notification Warning",
                    "The reservation status was updated, but a customer notification "
                    f"could not be sent.\n\n{error}"
                )

            messagebox.showinfo(
                "Updated",
                f"Reservation status changed to {new_status}."
            )

            self.admin_reservations()

        # =========================
        # ROW ACTION MENU
        # =========================
        def open_action_menu(event):
            region = tree.identify("region", event.x, event.y)
            column = tree.identify_column(event.x)
            iid = tree.identify_row(event.y)

            if region != "cell" or column != "#8" or not iid:
                return

            tree.selection_set(iid)
            values = tree.item(iid, "values")

            try:
                rid = int(iid)
            except (ValueError, TypeError):
                return

            status = str(values[6] or "").strip().title()

            menu = tk.Menu(
                tree,
                tearoff=0,
                font=("Segoe UI", 10),
                bg=WHITE,
                fg=PURPLE_DARK,
                activebackground=PURPLE_LIGHT,
                activeforeground=PURPLE_DARK
            )

            if status == "Pending":
                menu.add_command(
                    label="✓  Approve",
                    command=lambda: status_change(rid, "Approved")
                )
                menu.add_command(
                    label="✕  Cancel",
                    command=lambda: status_change(rid, "Cancelled")
                )

            elif status == "Approved":
                menu.add_command(
                    label="✓  Complete",
                    command=lambda: status_change(rid, "Completed")
                )
                menu.add_command(
                    label="✕  Cancel",
                    command=lambda: status_change(rid, "Cancelled")
                )

            else:
                return

            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        tree.bind("<Button-1>", open_action_menu)

        # =========================
        # TABLE REFRESH
        # =========================
        def refresh_table(*_, reset_page=False):
            nonlocal filtered_rows

            if reset_page:
                page_number["value"] = 1

            term = search_var.get().strip().lower()
            if term == "search by reservation id or customer...":
                term = ""

            selected_status = status_filter.get()
            selected_date = date_filter.get()
            today = date.today()

            filtered_rows = []

            for row in rows:
                rid, customer, event_type, event_date, guests, total, status = row
                status = str(status or "").strip().title()

                if selected_status != "All" and status != selected_status:
                    continue

                reservation_id = f"EVT-{datetime.now().year}-{rid:04d}"
                searchable = (
                    f"{reservation_id} {customer} {event_type} {event_date} {status}"
                ).lower()

                if term and term not in searchable:
                    continue

                try:
                    parsed_date = datetime.strptime(
                        str(event_date)[:10], "%Y-%m-%d"
                    ).date()
                except (ValueError, TypeError):
                    parsed_date = None

                if selected_date == "Today":
                    if parsed_date != today:
                        continue
                elif selected_date == "Next 7 days":
                    if not parsed_date or not (
                        today <= parsed_date <= today + timedelta(days=7)
                    ):
                        continue
                elif selected_date == "Next 30 days":
                    if not parsed_date or not (
                        today <= parsed_date <= today + timedelta(days=30)
                    ):
                        continue

                filtered_rows.append(
                    (rid, customer, event_type, event_date, guests, total, status)
                )


            # Ipakita lahat ng filtered reservations sa iisang page
            total_pages = 1
            page_number["value"] = 1

            tree.delete(*tree.get_children())

            start = 0
            visible_rows = filtered_rows


            for index, row in enumerate(visible_rows):
                rid, customer, event_type, event_date, guests, total, status = row
                tags = [status] if status in (
                    "Pending", "Approved", "Completed", "Cancelled"
                ) else []

                if index % 2 == 1:
                    tags.append("Alternate")

                tree.insert(
                    "",
                    "end",
                    iid=str(rid),
                    values=(
                        f"EVT-{datetime.now().year}-{rid:04d}",
                        customer,
                        event_type,
                        event_date,
                        guests,
                        money(total),
                        status,
                        "View  ▾" if status in ("Pending", "Approved") else "—"
                    ),
                    tags=tuple(tags)
                )

            for widget in pagination.winfo_children():
                widget.destroy()

            first = start + 1 if filtered_rows else 0
            last = start + len(visible_rows)

            result_label.config(
                text=f"Showing {first}–{last} of {len(filtered_rows)} reservations"
            )

            def change_page(number):
                page_number["value"] = number
                refresh_table()

            tk.Button(
                pagination,
                text="‹",
                command=lambda: change_page(max(1, page_number["value"] - 1)),
                bg=WHITE,
                fg=PURPLE_MAIN,
                relief="flat",
                width=3,
                state="normal" if page_number["value"] > 1 else "disabled"
            ).pack(side="left", padx=2)

            # Display nearby page numbers.
            first_page = max(1, min(
                page_number["value"] - 2,
                total_pages - 4
            ))
            last_page = min(total_pages, first_page + 4)

            for number in range(first_page, last_page + 1):
                tk.Button(
                    pagination,
                    text=str(number),
                    command=lambda n=number: change_page(n),
                    bg=PURPLE_MAIN if number == page_number["value"] else WHITE,
                    fg="white" if number == page_number["value"] else PURPLE_DARK,
                    relief="flat",
                    width=3
                ).pack(side="left", padx=2)

            tk.Button(
                pagination,
                text="›",
                command=lambda: change_page(
                    min(total_pages, page_number["value"] + 1)
                ),
                bg=WHITE,
                fg=PURPLE_MAIN,
                relief="flat",
                width=3,
                state="normal" if page_number["value"] < total_pages else "disabled"
            ).pack(side="left", padx=2)
        
            # =========================
            # HIDDEN SCROLLBAR + PAGE-WIDE MOUSE WHEEL
            # =========================
            def scroll_reservations(event):
                direction = -1 if event.delta > 0 else 1

                # Scroll the table when it has more rows than can be displayed.
                tree.yview_scroll(direction * 3, "units")
                return "break"

            def bind_scroll_anywhere(widget):
                widget.bind("<MouseWheel>", scroll_reservations, add="+")

                for child in widget.winfo_children():
                    bind_scroll_anywhere(child)

            bind_scroll_anywhere(page)
        # =========================
        # FILTER BUTTON STYLING
        # =========================
        def update_filter_styles():
            for name, button in filter_buttons.items():
                active = status_filter.get() == name
                button.config(
                    bg=PURPLE_MAIN if active else WHITE,
                    fg="white" if active else PURPLE_DARK,
                    activebackground=PURPLE_MAIN if active else PURPLE_LIGHT,
                    activeforeground="white" if active else PURPLE_DARK
                )

        def select_status(value):
            status_filter.set(value)
            update_filter_styles()
            refresh_table(reset_page=True)

        status_options = (
            ("All", "All"),
            ("Pending", "Pending"),
            ("Approved", "Approved"),
            ("Completed", "Completed"),
            ("Cancelled", "Cancelled")
        )

        for label, value in status_options:
            button = tk.Button(
                filter_frame,
                text=label,
                command=lambda v=value: select_status(v),
                font=("Segoe UI", 9, "bold"),
                bg=WHITE,
                fg=PURPLE_DARK,
                activebackground=PURPLE_LIGHT,
                activeforeground=PURPLE_DARK,
                relief="solid",
                bd=1,
                highlightthickness=0,
                padx=13,
                pady=8,
                cursor="hand2"
            )
            button.pack(side="left", padx=(0, 7))
            filter_buttons[value] = button

        search_var.trace_add("write", lambda *_: refresh_table(reset_page=True))

        update_filter_styles()
        refresh_table()

    def admin_packages(self):
        BG = "#F7F7FF"
        DARK = "#302052"
        PURPLE = "#4B2783"
        PURPLE_BTN = "#6740A3"
        PINK = "#F52F55"
        BORDER = "#E4DFFF"
        TEXT = "#37316D"
        MUTED = "#8586B5"

        self.page("Package Management", admin=True)

        parent = self._content
        for widget in parent.winfo_children():
            widget.destroy()

        main = tk.Frame(parent, bg=BG)
        main.pack(fill="both", expand=True, padx=27, pady=22)

        # HEADER
        header = tk.Frame(main, bg=BG)
        header.pack(fill="x", pady=(0, 24))

        icon_box = tk.Frame(header, bg="#DCCBFF", width=64, height=64)
        icon_box.pack(side="left", padx=(0, 20))
        icon_box.pack_propagate(False)

        tk.Label(
            icon_box, text="♧",
            font=("Segoe UI Symbol", 30, "bold"),
            bg="#DCCBFF", fg=DARK
        ).pack(expand=True)

        title_box = tk.Frame(header, bg=BG)
        title_box.pack(side="left")

        tk.Label(
            title_box, text="Package Management",
            font=("Segoe UI", 25, "bold"),
            bg=BG, fg=DARK
        ).pack(anchor="w")

        tk.Label(
            title_box, text="Manage event packages and pricing.",
            font=("Segoe UI", 11),
            bg=BG, fg=TEXT
        ).pack(anchor="w", pady=(3, 0))

        # SEARCH / FILTER TOOLBAR
        toolbar = tk.Frame(main, bg=BG)
        toolbar.pack(fill="x", pady=(0, 17))

        search_var = tk.StringVar()
        category_var = tk.StringVar(value="All Categories")
        event_var = tk.StringVar(value="All Events")

        search_box = tk.Frame(
            toolbar, bg="white",
            highlightbackground=BORDER, highlightthickness=1
        )
        search_box.pack(
            side="left", fill="x", expand=True, padx=(0, 16)
        )

        tk.Label(
            search_box, text="⌕",
            font=("Segoe UI", 22),
            bg="white", fg=DARK
        ).pack(side="left", padx=(13, 8))

        search_entry = tk.Entry(
            search_box, textvariable=search_var,
            font=("Segoe UI", 11), bd=0,
            bg="white", fg=TEXT, insertbackground=DARK
        )
        search_entry.pack(
            side="left", fill="both", expand=True,
            ipady=11, padx=(0, 10)
        )

        style = ttk.Style()
        style.configure(
            "PackageFilter.TCombobox",
            padding=10, font=("Segoe UI", 10)
        )

        category_filter = ttk.Combobox(
            toolbar, textvariable=category_var,
            values=[
                "All Categories", "Catering", "Photography",
                "Venue", "Event Styling & Decoration"
            ],
            state="readonly", width=19,
            style="PackageFilter.TCombobox"
        )
        category_filter.pack(side="left", padx=(0, 16), ipady=3)

        event_filter = ttk.Combobox(
            toolbar, textvariable=event_var,
            values=["All Events", "Birthday", "Debut", "Wedding"],
            state="readonly", width=15,
            style="PackageFilter.TCombobox"
        )
        event_filter.pack(side="left", padx=(0, 16), ipady=3)

        tk.Button(
            toolbar, text="＋  Add Package",
            font=("Segoe UI", 10, "bold"),
            bg=PURPLE, fg="white",
            activebackground="#60399A", activeforeground="white",
            relief="flat", bd=0, cursor="hand2",
            padx=18, pady=13,
            command=lambda: self.open_add_package()
        ).pack(side="left")

        # TABLE CARD
        card = tk.Frame(
            main, bg="white",
            highlightbackground=BORDER, highlightthickness=1
        )
        card.pack(fill="both", expand=True)

        table_frame = tk.Frame(card, bg="white")
        table_frame.pack(fill="both", expand=True, padx=7, pady=7)

        columns = (
            "id", "package", "event", "category",
            "provider", "price", "actions"
        )

        table = ttk.Treeview(
            table_frame, 
            columns=columns,
            show="headings", 
            height=25
        )

        table_settings = [
            ("id", "ID", 65, "center"),
            ("package", "PACKAGE", 275, "w"),
            ("event", "EVENT", 115, "center"),
            ("category", "CATEGORY", 205, "center"),
            ("provider", "PROVIDER", 175, "w"),
            ("price", "PRICE", 135, "center"),
            ("actions", "ACTIONS", 200, "center")
        ]

        for col, heading, width, anchor in table_settings:
            table.heading(col, text=heading)
            table.column(
                col, width=width, minwidth=60,
                anchor=anchor, stretch=True
            )

        style.configure(
            "PackageTable.Treeview",
            background="white", foreground=TEXT,
            fieldbackground="white", rowheight=65,
            font=("Segoe UI", 9), borderwidth=0
        )

        style.configure(
            "PackageTable.Treeview.Heading",
            background=DARK, foreground="white",
            font=("Segoe UI", 9, "bold"),
            padding=(8, 14), relief="flat"
        )

        style.map(
            "PackageTable.Treeview.Heading",
            background=[("active", DARK)],
            foreground=[("active", "white")]
        )

        table.configure(style="PackageTable.Treeview")
        table.pack(fill="both", expand=True)
        table.tag_configure("odd", background="white")
        table.tag_configure("even", background="#F3F2FC")

        # FOOTER / PAGINATION
        footer = tk.Frame(card, bg="white")
        footer.pack(fill="x", padx=14, pady=(10, 12))

        count_label = tk.Label(
            footer, text="Showing 0 packages",
            font=("Segoe UI", 9, "bold"),
            bg="white", fg=TEXT
        )
        count_label.pack(side="left")

        pagination = tk.Frame(footer, bg="white")
        pagination.pack(side="right")

        page_size = tk.IntVar(value=600)
        all_packages = []
        current_page = 1

        
        def load_packages():
            nonlocal all_packages

            con = None
            try:
                con = connect()
                all_packages = con.execute("""
                    SELECT id, name, event_type, category,
                        provider, price, description, image_path
                    FROM packages
                    ORDER BY id DESC
                """).fetchall()

            except Exception as exc:
                all_packages = []
                messagebox.showerror(
                    "Database Error",
                    f"Unable to load packages:\n{exc}"
                )

            finally:
                if con is not None:
                    con.close()

            render_table(1)


        def render_table(requested_page=1):
            nonlocal current_page

            query = search_var.get().strip().lower()
            selected_category = category_var.get()
            selected_event = event_var.get()

            filtered = []

            for row in all_packages:
                pid, name, event_type, category, provider, price, description, image_path = row

                searchable = " ".join(
                    str(value or "")
                    for value in (
                        pid, name, event_type, category,
                        provider, description, image_path
                    )
                ).lower()

                if query and query not in searchable:
                    continue

                if (
                    selected_category != "All Categories"
                    and category != selected_category
                ):
                    continue

                if (
                    selected_event != "All Events"
                    and event_type != selected_event
                ):
                    continue

                filtered.append(row)

            size = page_size.get()
            total = len(filtered)
            total_pages = max(1, (total + size - 1) // size)
            current_page = max(1, min(requested_page, total_pages))

            table.delete(*table.get_children())

            start = (current_page - 1) * size

            for index, row in enumerate(filtered[start:start + size]):
                pid, name, event_type, category, provider, price, description, image_path = row

                table.insert(
                    "", "end", iid=str(pid),
                    values=(
                        pid,
                        f"{name}\n{(description or '')[:38]}",
                        event_type or "—",
                        category or "—",
                        provider or "—",
                        money(price),
                        "✎ Edit  |  🗑 Delete"
                    ),
                    tags=("even" if index % 2 else "odd",)
                )

            if total:
                count_label.config(
                    text=(
                        f"Showing {start + 1}–"
                        f"{min(start + size, total)} of {total} packages"
                    )
                )
            else:
                count_label.config(text="Showing 0 packages")

            for widget in pagination.winfo_children():
                widget.destroy()

            def page_button(label, target, active=False):
                return tk.Button(
                    pagination, text=label,
                    font=("Segoe UI", 9, "bold"),
                    bg=PURPLE if active else "#F5F4FC",
                    fg="white" if active else TEXT,
                    activebackground="#60399A",
                    activeforeground="white",
                    relief="flat", bd=0,
                    width=3, pady=8, cursor="hand2",
                    command=lambda: render_table(target)
                )

            page_button("‹", max(1, current_page - 1)).pack(
                side="left", padx=3
            )

            pages = list(range(1, min(5, total_pages) + 1))
            if total_pages > 5:
                pages.extend(["…", total_pages])

            for number in pages:
                if number == "…":
                    tk.Label(
                        pagination, text="…",
                        bg="white", fg=TEXT, padx=5
                    ).pack(side="left")
                else:
                    page_button(
                        str(number), number,
                        active=(number == current_page)
                    ).pack(side="left", padx=3)

            page_button(
                "›", min(total_pages, current_page + 1)
            ).pack(side="left", padx=3)

            size_filter = ttk.Combobox(
                pagination, textvariable=page_size,
                values=[8, 16, 50, 100, 200, 600],
                state="readonly", width=7
            )
            size_filter.pack(side="left", padx=(10, 0))
            size_filter.bind(
                "<<ComboboxSelected>>",
                lambda event: render_table(1)
            )

        def table_click(event):
            if table.identify_region(event.x, event.y) != "cell":
                return

            item = table.identify_row(event.y)
            column = table.identify_column(event.x)

            if not item or column != "#7":
                return

            table.selection_set(item)
            bbox = table.bbox(item, column)

            if not bbox:
                return

            relative_x = event.x - bbox[0]

            if relative_x < bbox[2] / 2:
                self.open_add_package(package_id=int(item))
            else:
                if not messagebox.askyesno(
                    "Delete Package",
                    "Are you sure you want to delete this package?"
                ):
                    return

                try:
                    con = connect()
                    reference_columns = (
                        "catering_id", "photography_id",
                        "venue_id", "styling_id"
                    )

                    used = False

                    for column_name in reference_columns:
                        try:
                            result = con.execute(
                                f"SELECT 1 FROM reservations "
                                f"WHERE {column_name}=? LIMIT 1",
                                (int(item),)
                            ).fetchone()

                            if result:
                                used = True
                                break
                        except Exception:
                            pass

                    if used:
                        con.close()
                        messagebox.showwarning(
                            "Cannot Delete",
                            "This package is used by a reservation."
                        )
                        return

                    con.execute(
                        "DELETE FROM packages WHERE id=?",
                        (int(item),)
                    )
                    con.commit()
                    con.close()
                    load_packages()

                except Exception as exc:
                    messagebox.showerror("Delete Error", str(exc))

        table.bind("<Button-1>", table_click)

        search_var.trace_add("write", lambda *_: render_table(1))
        category_filter.bind(
            "<<ComboboxSelected>>", lambda event: render_table(1)
        )
        event_filter.bind(
            "<<ComboboxSelected>>", lambda event: render_table(1)
        )

        load_packages()
    
    
    def open_add_package(self, package_id=None):
        BG = "#F7F7FF"
        DARK = "#302052"
        PURPLE = "#4B2783"
        BORDER = "#E4DFFF"
        TEXT = "#37316D"

        editing = package_id is not None
        package_data = None

        if editing:
            con = None
            try:
                con = connect()
                package_data = con.execute("""
                    SELECT name, event_type, category, provider,
                        description, inclusions, menu, price, image_path
                    FROM packages
                    WHERE id=?
                """, (package_id,)).fetchone()
            except Exception as exc:
                messagebox.showerror("Database Error", str(exc))
                return
            finally:
                if con:
                    con.close()

            if not package_data:
                messagebox.showerror(
                    "Package Not Found",
                    "Hindi na makita ang package na ito."
                )
                return

        window = tk.Toplevel(self)
        window.title("Edit Package" if editing else "Add Package")
        window.configure(bg=BG)
        window.geometry("900x650")
        window.minsize(850, 600)
        window.resizable(True, True)
        window.transient(self)
        window.grab_set()

        tk.Label(
            window,
            text="Edit Package" if editing else "Add New Package",
            font=("Segoe UI", 21, "bold"),
            bg=BG, fg=DARK
        ).pack(anchor="w", padx=28, pady=(18, 3))

        tk.Label(
            window,
            text="Fill in the package details below.",
            font=("Segoe UI", 10),
            bg=BG, fg=TEXT
        ).pack(anchor="w", padx=28, pady=(0, 12))

        form = tk.Frame(
            window, bg="white",
            highlightbackground=BORDER,
            highlightthickness=1
        )
        form.pack(fill="both", expand=True, padx=24, pady=(0, 6))

        left_panel = tk.Frame(form, bg="white")
        left_panel.pack(
            side="left", fill="both", expand=True,
            padx=(12, 6), pady=10
        )

        right_panel = tk.Frame(form, bg="white")
        right_panel.pack(
            side="left", fill="both", expand=True,
            padx=(6, 12), pady=10
        )

        fields = {}
        
        image_path_var = tk.StringVar(
            value=package_data[8] if editing else ""
        )

        def add_entry(panel, label, key, value=""):
            tk.Label(
                panel, text=label,
                font=("Segoe UI", 10, "bold"),
                bg="white", fg=TEXT
            ).pack(anchor="w", pady=(8, 4))

            entry = tk.Entry(
                panel, font=("Segoe UI", 10),
                relief="solid", bd=1
            )
            entry.pack(fill="x", ipady=7)
            entry.insert(0, str(value or ""))
            fields[key] = entry

        def add_combo(panel, label, key, values, value):
            tk.Label(
                panel, text=label,
                font=("Segoe UI", 10, "bold"),
                bg="white", fg=TEXT
            ).pack(anchor="w", pady=(8, 4))

            combo = ttk.Combobox(
                panel, values=values,
                state="readonly", font=("Segoe UI", 10)
            )
            combo.pack(fill="x", ipady=4)
            combo.set(value or values[0])
            fields[key] = combo

        def add_text(panel, label, key, value=""):
            tk.Label(
                panel, text=label,
                font=("Segoe UI", 10, "bold"),
                bg="white", fg=TEXT
            ).pack(anchor="w", pady=(8, 4))

            text_box = tk.Text(
                panel, height=3, font=("Segoe UI", 10),
                relief="solid", bd=1
            )
            text_box.pack(fill="x")
            text_box.insert("1.0", str(value or ""))
            fields[key] = text_box

        data = package_data or (
            "", "Birthday", "Catering", "", "", "", "", 0, ""
        )

        # LEFT PANEL
        add_entry(left_panel, "Package Name", "name", data[0])

        add_combo(
            left_panel, "Event Type", "event_type",
            ["Birthday", "Debut", "Wedding"], data[1]
        )

        add_combo(
            left_panel, "Category", "category",
            ["Catering", "Photography", "Venue",
            "Event Styling & Decoration"], data[2]
        )

        add_entry(left_panel, "Provider", "provider", data[3])

        add_entry(left_panel, "Price (PHP)", "price", data[7])

        # RIGHT PANEL
        add_text(right_panel, "Description", "description", data[4])

        add_text(right_panel, "Inclusions", "inclusions", data[5])

        add_text(right_panel, "Menu", "menu", data[6])
        
        
        # PACKAGE IMAGE
        image_path_var = tk.StringVar(
            value=package_data[8] if editing and len(package_data) > 8 else ""
        )

        tk.Label(
            right_panel,
            text="Package Image",
            font=("Segoe UI", 10, "bold"),
            bg="white",
            fg=TEXT
        ).pack(anchor="w", pady=(10, 4))

        
        image_preview_frame = tk.Frame(
            right_panel,
            bg="#F5F1FA",
            width=360,
            height=115
        )
        image_preview_frame.pack(fill="x", pady=(0, 8))
        image_preview_frame.pack_propagate(False)

        image_label = tk.Label(
            image_preview_frame,
            text="No image selected",
            bg="#F5F1FA",
            fg=TEXT,
            anchor="center"
        )
        image_label.pack(fill="both", expand=True)

        def show_package_image(path):
            if not path or not Path(path).is_file():
                image_label.config(image="", text="No image selected")
                image_label.image = None
                return

            try:
                img = Image.open(path).convert("RGB")
                img.thumbnail((300, 100), Image.Resampling.LANCZOS)

                preview = ImageTk.PhotoImage(img)
                image_label.config(image=preview, text="")
                image_label.image = preview

            except Exception:
                image_label.config(
                    image="",
                    text="Unable to display image"
                )
                image_label.image = None


        def choose_package_image():
            path = filedialog.askopenfilename(
                parent=window,
                title="Choose Package Image",
                filetypes=[
                    ("Image files", "*.png *.jpg *.jpeg *.webp"),
                    ("All files", "*.*")
                ]
            )

            if path:
                image_path_var.set(path)
                show_package_image(path)

        tk.Button(
            right_panel,
            text="Choose Image",
            command=choose_package_image,
            cursor="hand2",
            bg="#EAE5F5",
            fg=DARK,
            relief="flat",
            padx=12,
            pady=6
        ).pack(anchor="w")

        show_package_image(image_path_var.get())

        def save_package():
            import os
            import uuid

            name = fields["name"].get().strip()
            provider = fields["provider"].get().strip()
            price_text = fields["price"].get().strip()

            if not name or not provider or not price_text:
                messagebox.showwarning(
                    "Required Fields",
                    "Punan ang Package Name, Provider, at Price.",
                    parent=window
                )
                return

            try:
                price = float(price_text.replace(",", ""))
                if price < 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning(
                    "Invalid Price",
                    "Maglagay ng valid na presyo.",
                    parent=window
                )
                return

            image_path = image_path_var.get().strip()

            if editing and image_path and os.path.isfile(image_path):
                saved_folder = Path(__file__).resolve().parent / "photos" / "packages"

                try:
                    if Path(image_path).resolve().parent == saved_folder.resolve():
                        pass
                    else:
                        image_path = str(Path(image_path))
                except Exception:
                    pass

            try:
                if image_path and os.path.isfile(image_path):
                    package_folder = Path(__file__).resolve().parent / "photos" / "packages"
                    package_folder.mkdir(parents=True, exist_ok=True)

                    extension = Path(image_path).suffix.lower()
                    if extension not in (".png", ".jpg", ".jpeg", ".webp"):
                        messagebox.showwarning(
                            "Invalid Image",
                            "Pumili ng PNG, JPG, JPEG, o WEBP image.",
                            parent=window
                        )
                        return

                    destination = package_folder / f"package_{uuid.uuid4().hex}{extension}"
                    shutil.copy2(image_path, destination)
                    image_path = str(destination)

                values = (
                    name,
                    fields["event_type"].get(),
                    fields["category"].get(),
                    provider,
                    fields["description"].get("1.0", "end-1c").strip(),
                    fields["inclusions"].get("1.0", "end-1c").strip(),
                    fields["menu"].get("1.0", "end-1c").strip(),
                    price,
                    image_path
                )

                con = connect()
                try:
                    if editing:
                        con.execute("""
                            UPDATE packages
                            SET name=?, event_type=?, category=?, provider=?,
                                description=?, inclusions=?, menu=?, price=?,
                                image_path=?
                            WHERE id=?
                        """, values + (package_id,))
                    else:
                        con.execute("""
                            INSERT INTO packages
                            (name, event_type, category, provider,
                             description, inclusions, menu, price, image_path)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, values)

                    con.commit()
                finally:
                    con.close()

                messagebox.showinfo(
                    "Success",
                    "Package updated successfully."
                    if editing else "Package added successfully.",
                    parent=window
                )
                window.destroy()
                self.admin_packages()

            except Exception as exc:
                messagebox.showerror(
                    "Save Error", str(exc), parent=window
                )


        
        button_bar = tk.Frame(window, bg=BG)
        button_bar.pack(fill="x", padx=24, pady=(0, 10))

        tk.Button(
            button_bar,
            text="Cancel",
            font=("Segoe UI", 10, "bold"),
            bg="#EAE5F5",
            fg=DARK,
            relief="flat",
            cursor="hand2",
            padx=22,
            pady=10,
            command=window.destroy
        ).pack(side="right", padx=(10, 0))

        tk.Button(
            button_bar,
            text="Save Changes" if editing else "Add Package",
            font=("Segoe UI", 10, "bold"),
            bg=PURPLE,
            fg="white",
            activebackground="#60399A",
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=24,
            pady=10,
            command=save_package
        ).pack(side="right")


    def admin_calendar(self):
        import calendar as cal
        from datetime import datetime

        page = self.page(
            "Calendar",
            True,
            "Availability Calendar"
        )

        # =========================
        # CALENDAR STATE
        # =========================

        now = datetime.now()

        state = {
            "year": now.year,
            "month": now.month,
            "selected": now.date()
        }

        # =========================
        # MAIN CONTAINER
        # =========================

        main = tk.Frame(
            page,
            bg=LIGHT
        )

        main.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=10
        )

        # =========================
        # LEFT CALENDAR
        # =========================

        calendar_card = tk.Frame(
            main,
            bg=CARD,
            padx=18,
            pady=15,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        calendar_card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 8)
        )

        title_row = tk.Frame(
            calendar_card,
            bg=CARD
        )

        title_row.pack(
            fill="x",
            pady=(0, 12)
        )

        self.label(
            title_row,
            "Availability Calendar",
            16,
            True,
            PURPLE,
            CARD
        ).pack(
            side="left"
        )

        # =========================
        # MONTH NAVIGATION
        # =========================

        nav = tk.Frame(
            calendar_card,
            bg=CARD
        )

        nav.pack(
            fill="x",
            pady=(0, 12)
        )

        def previous_month():
            if state["month"] == 1:
                state["month"] = 12
                state["year"] -= 1
            else:
                state["month"] -= 1

            # Keep selected date inside the displayed month
            state["selected"] = datetime(
                state["year"],
                state["month"],
                1
            ).date()

            render_calendar()
            show_selected_date()


        def next_month():
            if state["month"] == 12:
                state["month"] = 1
                state["year"] += 1
            else:
                state["month"] += 1

            # Keep selected date inside the displayed month
            state["selected"] = datetime(
                state["year"],
                state["month"],
                1
            ).date()

            render_calendar()
            show_selected_date()

        self.button(
            nav,
            "‹",
            previous_month,
            False
        ).pack(
            side="left"
        )

        month_label = tk.Label(
            nav,
            text="",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 10, "bold")
        )

        month_label.pack(
            side="left",
            expand=True
        )

        self.button(
            nav,
            "›",
            next_month,
            False
        ).pack(
            side="right"
        )

        # =========================
        # WEEKDAYS
        # =========================

        weekdays = tk.Frame(
            calendar_card,
            bg=CARD
        )

        weekdays.pack(
            fill="x"
        )

        for day in [
            "Mon", "Tue", "Wed",
            "Thu", "Fri", "Sat", "Sun"
        ]:
            tk.Label(
                weekdays,
                text=day,
                bg=CARD,
                fg=MUTED,
                font=("Segoe UI", 8, "bold")
            ).pack(
                side="left",
                fill="x",
                expand=True,
                pady=5
            )

        calendar_grid = tk.Frame(
            calendar_card,
            bg=CARD
        )

        calendar_grid.pack(
            fill="both",
            expand=True
        )

        # =========================
        # DATABASE EVENTS
        # =========================

        def get_events():

            con = connect()

            rows = con.execute(
                """
                SELECT
                    id,
                    event_date,
                    event_type,
                    customer,
                    guests,
                    total,
                    status,
                    catering_id,
                    photography_id,
                    venue_id,
                    styling_id
                FROM reservations
                WHERE status IN (
                    'Pending',
                    'Approved',
                    'Completed',
                    'Cancelled'
                )
                ORDER BY event_date ASC, id ASC
                """
            ).fetchall()

            con.close()

            events = {}

            for row in rows:

                try:
                    raw_date = str(row[1]).strip()

                    # Handles:
                    # 2026-09-29
                    # 2026-09-29 00:00:00
                    date_value = datetime.strptime(
                        raw_date[:10],
                        "%Y-%m-%d"
                    ).date()

                except Exception:
                    continue

                events.setdefault(
                    date_value,
                    []
                ).append(row)

            return events

        # =========================
        # STATUS COLORS
        # =========================

        STATUS_BG = {
            "Approved": "#E8F7EF",
            "Pending": "#FFF4E2",
            "Cancelled": "#FDEAEA",
            "Completed": "#F0E9FA"
        }

        STATUS_COLOR = {
            "Approved": GREEN,
            "Pending": ORANGE,
            "Cancelled": RED,
            "Completed": PURPLE2
        }

        # =========================
        # SELECT DATE
        # =========================

        def select_date(date_value):

            state["selected"] = date_value

            render_calendar()

            show_selected_date()

        # =========================
        # RENDER CALENDAR
        # =========================

        def render_calendar():

            for widget in calendar_grid.winfo_children():
                widget.destroy()

            month_name = cal.month_name[
                state["month"]
            ]

            month_label.config(
                text=f"{month_name} {state['year']}"
            )

            events = get_events()

            weeks = cal.monthcalendar(
                state["year"],
                state["month"]
            )

            for week in weeks:

                row = tk.Frame(
                    calendar_grid,
                    bg=CARD
                )

                row.pack(
                    fill="both",
                    expand=True
                )

                for day_number in week:

                    if day_number == 0:

                        tk.Label(
                            row,
                            text="",
                            bg=CARD
                        ).pack(
                            side="left",
                            fill="both",
                            expand=True,
                            padx=2,
                            pady=2
                        )

                        continue

                    date_value = datetime(
                        state["year"],
                        state["month"],
                        day_number
                    ).date()

                    day_events = events.get(
                        date_value,
                        []
                    )

                    is_selected = (
                        date_value ==
                        state["selected"]
                    )

                    is_today = (
                        date_value ==
                        datetime.now().date()
                    )

                    # =========================
                    # DETERMINE DATE COLOR
                    # =========================

                    statuses = [
                        str(event[6]).strip()
                        for event in day_events
                    ]

                    if "Approved" in statuses:
                        date_bg = STATUS_BG["Approved"]

                    elif "Pending" in statuses:
                        date_bg = STATUS_BG["Pending"]

                    elif "Cancelled" in statuses:
                        date_bg = STATUS_BG["Cancelled"]

                    elif "Completed" in statuses:
                        date_bg = STATUS_BG["Completed"]

                    elif is_today:
                        date_bg = "#F8F5FB"

                    else:
                        date_bg = CARD

                    # Selected date keeps its event color
                    # but gets a strong purple border.
                    border_color = (
                        PURPLE2
                        if is_selected
                        else STATUS_COLOR.get(
                            statuses[0],
                            BORDER
                        )
                        if statuses
                        else BORDER
                    )

                    cell = tk.Frame(
                        row,
                        bg=date_bg,
                        highlightbackground=border_color,
                        highlightthickness=2 if is_selected else 1
                    )

                    cell.pack(
                        side="left",
                        fill="both",
                        expand=True,
                        padx=2,
                        pady=2
                    )
                    # =========================
                    # CLICKABLE DATE
                    # =========================

                    number_fg = (
                        PURPLE
                        if is_selected
                        else TEXT
                    )

                    # =========================
                    # DATE CONTENT
                    # =========================

                    date_label = tk.Label(
                        cell,
                        text=str(day_number),
                        bg=date_bg,
                        fg=number_fg,
                        font=(
                            "Segoe UI",
                            9,
                            "bold"
                            if is_selected or is_today
                            else "normal"
                        )
                    )

                    date_label.pack(
                        anchor="nw",
                        padx=5,
                        pady=4
                    )

                    # Make the entire date cell clickable
                    def click_date(event, d=date_value):
                        select_date(d)

                    cell.bind(
                        "<Button-1>",
                        click_date
                    )

                    date_label.bind(
                        "<Button-1>",
                        click_date
                    )

                    # =========================
                    # STATUS DOTS
                    # =========================

                    if day_events:

                        dot_frame = tk.Frame(
                            cell,
                            bg=date_bg
                        )

                        dot_frame.pack(
                            anchor="w",
                            padx=6,
                            pady=(0, 5)
                        )
                        dot_frame.bind(
                            "<Button-1>",
                            click_date
                        )

                        shown_statuses = []

                        for event in day_events:

                            status = str(
                                event[6]
                            ).strip()

                            if status not in shown_statuses:
                                shown_statuses.append(
                                    status
                                )

                        for status in shown_statuses:

                            dot_color = STATUS_COLOR.get(
                                status,
                                PURPLE2
                            )

                            status_dot = tk.Label(
                                dot_frame,
                                text="●",
                                fg=dot_color,
                                bg=date_bg,
                                font=("Segoe UI", 7)
                            )

                            status_dot.pack(
                                side="left",
                                padx=(0, 2)
                            )

                            status_dot.bind(
                                "<Button-1>",
                                click_date
                            )

        # =========================
        # LEGEND
        # =========================

        legend = tk.Frame(
            calendar_card,
            bg=CARD
        )

        legend.pack(
            fill="x",
            pady=(10, 0)
        )

        legend_items = [
            ("●", GREEN, "Approved"),
            ("●", ORANGE, "Pending"),
            ("●", RED, "Cancelled"),
            ("●", PURPLE2, "Completed"),
        ]

        for symbol, color, text_value in legend_items:

            item = tk.Frame(
                legend,
                bg=CARD
            )

            item.pack(
                side="left",
                padx=(0, 14)
            )

            tk.Label(
                item,
                text=symbol,
                fg=color,
                bg=CARD,
                font=("Segoe UI", 8)
            ).pack(
                side="left"
            )

            tk.Label(
                item,
                text=text_value,
                fg=MUTED,
                bg=CARD,
                font=("Segoe UI", 8)
            ).pack(
                side="left",
                padx=(3, 0)
            )

        # =========================
        # RIGHT SELECTED DATE
        # =========================

        details_card = tk.Frame(
            main,
            bg=CARD,
            padx=18,
            pady=15,
            width=290,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        details_card.pack(
            side="right",
            fill="y",
            padx=(8, 0)
        )

        details_card.pack_propagate(False)

        self.label(
            details_card,
            "Selected Date",
            13,
            True,
            PURPLE,
            CARD
        ).pack(
            anchor="w"
        )

        selected_label = tk.Label(
            details_card,
            text="",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 9, "bold")
        )

        selected_label.pack(
            anchor="w",
            pady=(5, 12)
        )

        events_container = tk.Frame(
            details_card,
            bg=CARD
        )

        events_container.pack(
            fill="both",
            expand=True
        )

        # =========================
        # SHOW SELECTED DATE
        # =========================

        def show_selected_date():

            for widget in events_container.winfo_children():
                widget.destroy()

            selected = state["selected"]

            selected_label.config(
                text=selected.strftime(
                    "%b %d, %Y"
                )
            )

            events = get_events()

            day_events = events.get(
                selected,
                []
            )

            if not day_events:

                self.label(
                    events_container,
                    "No reservations",
                    9,
                    False,
                    MUTED,
                    CARD
                ).pack(
                    anchor="w",
                    pady=20
                )

                return

            for reservation in day_events:

                (
                    rid,
                    event_date,
                    event_type,
                    customer,
                    guests,
                    total,
                    status,
                    catering_id,
                    photography_id,
                    venue_id,
                    styling_id
                ) = reservation

                status_color = STATUS_COLOR.get(
                    status,
                    MUTED
                )

                item = tk.Frame(
                    events_container,
                    bg="#FAF7FC",
                    padx=10,
                    pady=10,
                    highlightbackground=status_color,
                    highlightthickness=1
                )

                item.pack(
                    fill="x",
                    pady=4
                )

                # Event type
                self.label(
                    item,
                    event_type,
                    9,
                    True,
                    TEXT,
                    "#FAF7FC"
                ).pack(
                    anchor="w"
                )

                # Customer
                self.label(
                    item,
                    customer,
                    8,
                    False,
                    MUTED,
                    "#FAF7FC"
                ).pack(
                    anchor="w",
                    pady=(2, 3)
                )

                # Status
                status_row = tk.Frame(
                    item,
                    bg="#FAF7FC"
                )

                status_row.pack(
                    anchor="w"
                )

                tk.Label(
                    status_row,
                    text="●",
                    fg=status_color,
                    bg="#FAF7FC",
                    font=("Segoe UI", 8)
                ).pack(
                    side="left"
                )

                self.label(
                    status_row,
                    status,
                    8,
                    True,
                    status_color,
                    "#FAF7FC"
                ).pack(
                    side="left",
                    padx=(4, 0)
                )

        # =========================
        # VIEW DETAILS
        # =========================

        def view_details():

            selected_events = get_events().get(
                state["selected"],
                []
            )

            if not selected_events:

                messagebox.showinfo(
                    "Selected Date",
                    "There are no reservations "
                    "for this date."
                )

                return

            text = ""

            for reservation in selected_events:

                (
                    rid,
                    event_date,
                    event_type,
                    customer,
                    guests,
                    total,
                    status,
                    catering_id,
                    photography_id,
                    venue_id,
                    styling_id
                ) = reservation

                text += (
                    f"EVT-{datetime.now().year}-{rid:04d}\n"
                    f"Event: {event_type}\n"
                    f"Customer: {customer}\n"
                    f"Guests: {guests}\n"
                    f"Status: {status}\n"
                    f"Total: {money(total)}\n"
                    f"{'-' * 35}\n"
                )

            messagebox.showinfo(
                "Reservation Details",
                text
            )

        self.button(
            details_card,
            "View Details",
            view_details,
            True
        ).pack(
            fill="x",
            pady=(10, 0)
        )

        # =========================
        # INITIAL RENDER
        # =========================

        render_calendar()
        show_selected_date()
        
    
    
    
    def admin_messages(self):
        ensure_message_tables()

        page = self.page("Messages", admin=True, title="Messages")

        BG = LIGHT
        WHITE = CARD
        DARK = "#302052"
        PURPLE = "#6740A3"
        PINK = "#F52F8A"
        PALE = "#F4EFFB"
        BORDER_COLOR = BORDER
        TEXT_COLOR = TEXT
        MUTED_COLOR = MUTED

        for widget in page.winfo_children():
            widget.destroy()

        # =========================
        # PAGE HEADER
        # =========================
        header = tk.Frame(page, bg=BG)
        header.pack(fill="x", padx=30, pady=(22, 14))

        self.label(
            header, "Messages", 24, True, DARK, BG
        ).pack(anchor="w")

        self.label(
            header,
            "Manage customer conversations and replies.",
            10, False, MUTED_COLOR, BG
        ).pack(anchor="w", pady=(4, 0))

        # =========================
        # MAIN AREA
        # =========================
        main = tk.Frame(page, bg=BG)
        main.pack(fill="both", expand=True, padx=30, pady=(0, 24))

        list_screen = tk.Frame(
            main,
            bg=WHITE,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1
        )

        chat_screen = tk.Frame(
            main,
            bg=WHITE,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1
        )

        list_screen.pack(fill="both", expand=True)

        # =========================
        # MESSAGES LIST HEADER
        # =========================
        list_top = tk.Frame(list_screen, bg=WHITE)
        list_top.pack(fill="x", padx=22, pady=(20, 12))

        self.label(
            list_top, "Inbox", 16, True, DARK, WHITE
        ).pack(side="left")

        # =========================
        # SEARCH BAR
        # =========================
        search_area = tk.Frame(list_screen, bg=WHITE)
        search_area.pack(fill="x", padx=22, pady=(0, 14))

        search_box = tk.Frame(
            search_area,
            bg="#FAF8FD",
            highlightbackground=BORDER_COLOR,
            highlightthickness=1
        )
        search_box.pack(fill="x")

        tk.Label(
            search_box,
            text="⌕",
            font=("Segoe UI Symbol", 21),
            bg="#FAF8FD",
            fg=PURPLE
        ).pack(side="left", padx=(13, 8))

        search_var = tk.StringVar()

        search_entry = tk.Entry(
            search_box,
            textvariable=search_var,
            font=("Segoe UI", 11),
            bg="#FAF8FD",
            fg=TEXT_COLOR,
            insertbackground=PURPLE,
            relief="flat",
            bd=0
        )
        search_entry.pack(
            side="left",
            fill="x",
            expand=True,
            ipady=11,
            padx=(0, 12)
        )

        # =========================
        # CUSTOMER LIST CANVAS
        # =========================
        list_body = tk.Frame(list_screen, bg=WHITE)
        list_body.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(0, 12)
        )

        list_canvas = tk.Canvas(
            list_body,
            bg=WHITE,
            highlightthickness=0,
            bd=0
        )
        list_canvas.pack(fill="both", expand=True)

        customer_frame = tk.Frame(list_canvas, bg=WHITE)

        customer_window = list_canvas.create_window(
            (0, 0),
            window=customer_frame,
            anchor="nw"
        )

        def update_customer_scroll(event=None):
            list_canvas.configure(
                scrollregion=list_canvas.bbox("all")
            )

        def resize_customer_content(event):
            list_canvas.itemconfigure(
                customer_window,
                width=event.width
            )

        customer_frame.bind(
            "<Configure>",
            update_customer_scroll
        )
        list_canvas.bind(
            "<Configure>",
            resize_customer_content
        )

        # =========================
        # CHAT HEADER
        # =========================
        chat_header = tk.Frame(chat_screen, bg=WHITE)
        chat_header.pack(fill="x", padx=20, pady=(15, 12))

        def back_to_list():
            chat_screen.pack_forget()
            list_screen.pack(fill="both", expand=True)
            search_entry.focus_set()

        back_button = tk.Button(
            chat_header,
            text="←",
            font=("Segoe UI", 18, "bold"),
            bg="#F0E9FA",
            fg=PURPLE,
            activebackground="#E6D9F7",
            activeforeground=DARK,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=12,
            pady=5,
            command=back_to_list
        )
        back_button.pack(side="left", padx=(0, 14))

        avatar_label = tk.Label(
            chat_header,
            text="",
            font=("Segoe UI", 12, "bold"),
            bg="#E7DDFC",
            fg=PURPLE,
            width=4,
            height=2
        )
        avatar_label.pack(side="left", padx=(0, 10))

        chat_identity = tk.Frame(chat_header, bg=WHITE)
        chat_identity.pack(side="left", fill="x", expand=True)

        chat_name_label = tk.Label(
            chat_identity,
            text="Select a conversation",
            font=("Segoe UI", 12, "bold"),
            bg=WHITE,
            fg=DARK,
            anchor="w"
        )
        chat_name_label.pack(anchor="w")

        tk.Label(
            chat_identity,
            text="Customer",
            font=("Segoe UI", 9),
            bg=WHITE,
            fg=MUTED_COLOR,
            anchor="w"
        ).pack(anchor="w", pady=(2, 0))

        # =========================
        # CHAT HISTORY CANVAS
        # =========================
        chat_area = tk.Frame(chat_screen, bg=PALE)
        chat_area.pack(fill="both", expand=True)

        chat_canvas = tk.Canvas(
            chat_area,
            bg=PALE,
            highlightthickness=0,
            bd=0
        )
        chat_canvas.pack(fill="both", expand=True)

        chat_frame = tk.Frame(chat_canvas, bg=PALE)

        chat_window = chat_canvas.create_window(
            (0, 0),
            window=chat_frame,
            anchor="nw"
        )

        def update_chat_scroll(event=None):
            chat_canvas.configure(
                scrollregion=chat_canvas.bbox("all")
            )

        def resize_chat_content(event):
            chat_canvas.itemconfigure(
                chat_window,
                width=event.width
            )

        chat_frame.bind(
            "<Configure>",
            update_chat_scroll
        )
        chat_canvas.bind(
            "<Configure>",
            resize_chat_content
        )

        # =========================
        # GLOBAL MOUSE-WHEEL SCROLL
        # One handler for the entire Messages page.
        # =========================
        def wheel_scroll(event):
            if chat_screen.winfo_ismapped():
                target = chat_canvas
            elif list_screen.winfo_ismapped():
                target = list_canvas
            else:
                return "break"

            event_num = getattr(event, "num", None)

            if event_num == 4:
                amount = -1
            elif event_num == 5:
                amount = 1
            else:
                delta = getattr(event, "delta", 0)

                if not delta:
                    return "break"

                amount = -1 if delta > 0 else 1

            target.yview_scroll(amount, "units")
            return "break"

        # Bind to the root so wheel events work over nested widgets.
        root = page.winfo_toplevel()
        root.bind_all("<MouseWheel>", wheel_scroll, add="+")
        root.bind_all("<Button-4>", wheel_scroll, add="+")
        root.bind_all("<Button-5>", wheel_scroll, add="+")

        # =========================
        # MESSAGE COMPOSER
        # =========================
        composer = tk.Frame(
            chat_screen,
            bg=WHITE,
            padx=16,
            pady=14
        )
        composer.pack(fill="x")

        message_var = tk.StringVar()

        composer_box = tk.Frame(
            composer,
            bg="#FAF8FD",
            highlightbackground=BORDER_COLOR,
            highlightthickness=1
        )
        composer_box.pack(fill="x")

        message_entry = tk.Entry(
            composer_box,
            textvariable=message_var,
            font=("Segoe UI", 11),
            bg="#FAF8FD",
            fg=TEXT_COLOR,
            insertbackground=PURPLE,
            relief="flat",
            bd=0
        )
        message_entry.pack(
            side="left",
            fill="x",
            expand=True,
            ipady=12,
            padx=(14, 8)
        )

        # =========================
        # DATABASE HELPERS
        # =========================
        con = connect()
        try:
            customer_rows = con.execute("""
                SELECT DISTINCT customer
                FROM reservations
                WHERE customer IS NOT NULL
                AND TRIM(customer) != ''
                ORDER BY customer COLLATE NOCASE
            """).fetchall()
        finally:
            con.close()

        customer_names = [row[0] for row in customer_rows]
        selected_customer = {"name": None}

        def get_conversation(customer_name):
            con = connect()
            try:
                return con.execute("""
                    SELECT sender, sender_role, message, created_at
                    FROM messages
                    WHERE
                        (
                            sender IN ('admin', 'EventHub Admin')
                            AND recipient = ?
                        )
                        OR
                        (
                            sender = ?
                            AND recipient IN ('admin', 'EventHub Admin')
                        )
                    ORDER BY id ASC
                """, (
                    customer_name,
                    customer_name
                )).fetchall()
            finally:
                con.close()

        def get_latest_message(customer_name):
            con = connect()
            try:
                return con.execute("""
                    SELECT message, created_at, sender, sender_role
                    FROM messages
                    WHERE
                        (
                            sender IN ('admin', 'EventHub Admin')
                            AND recipient = ?
                        )
                        OR
                        (
                            sender = ?
                            AND recipient IN ('admin', 'EventHub Admin')
                        )
                    ORDER BY id DESC
                    LIMIT 1
                """, (
                    customer_name,
                    customer_name
                )).fetchone()
            finally:
                con.close()

        def get_unread_count(customer_name):
            con = connect()
            try:
                return con.execute("""
                    SELECT COUNT(*)
                    FROM messages
                    WHERE sender = ?
                    AND recipient IN ('admin', 'EventHub Admin')
                    AND COALESCE(is_read, 0) = 0
                """, (customer_name,)).fetchone()[0]
            finally:
                con.close()

        # =========================
        # RENDER CHAT HISTORY
        # =========================
        def show_conversation(customer_name):
            selected_customer["name"] = customer_name

            try:
                # Mark customer messages as read
                con = connect()
                try:
                    con.execute("""
                        UPDATE messages
                        SET is_read = 1
                        WHERE sender = ?
                        AND recipient IN ('admin', 'EventHub Admin')
                        AND COALESCE(is_read, 0) = 0
                    """, (customer_name,))
                    con.commit()
                finally:
                    con.close()

                # Load messages
                messages = get_conversation(customer_name)

            except Exception as e:
                messagebox.showerror(
                    "Messages Error",
                    f"Hindi ma-load ang conversation.\n\n{e}"
                )
                return

            # Refresh inbox unread badges
            refresh_customer_list()

            # Refresh sidebar badge without rebuilding the page
            if hasattr(self, "refresh_sidebar_badges"):
                self.refresh_sidebar_badges()
            else:
                # Rebuild sidebar only after the conversation is loaded
                self.sidebar("Messages", admin=True)

            # Switch to chat screen
            list_screen.pack_forget()
            chat_screen.pack_forget()
            chat_screen.pack(fill="both", expand=True)

            initials = "".join(
                part[0]
                for part in customer_name.split()
                if part
            )[:2].upper()

            avatar_label.config(text=initials or "?")
            chat_name_label.config(text=customer_name)

            # Clear previous conversation
            for widget in chat_frame.winfo_children():
                widget.destroy()

            if not messages:
                tk.Label(
                    chat_frame,
                    text="No messages yet",
                    font=("Segoe UI", 14, "bold"),
                    bg=PALE,
                    fg=PURPLE
                ).pack(pady=(80, 8))

                tk.Label(
                    chat_frame,
                    text="Send a message to start the conversation.",
                    font=("Segoe UI", 10),
                    bg=PALE,
                    fg=MUTED_COLOR
                ).pack(pady=(0, 20))

            # Display conversation messages
            for sender, sender_role, msg, created_at in messages:
                is_admin = (
                    (sender_role or "").strip().lower() == "admin"
                )

                row_frame = tk.Frame(chat_frame, bg=PALE)
                row_frame.pack(fill="x", padx=22, pady=7)

                bubble_bg = "#E8DDFC" if is_admin else WHITE

                bubble = tk.Frame(
                    row_frame,
                    bg=bubble_bg,
                    padx=14,
                    pady=10,
                    highlightbackground=BORDER_COLOR,
                    highlightthickness=1
                )
                bubble.pack(
                    side="right" if is_admin else "left",
                    anchor="e" if is_admin else "w"
                )

                tk.Label(
                    bubble,
                    text=msg or "",
                    font=("Segoe UI", 10),
                    bg=bubble_bg,
                    fg=TEXT_COLOR,
                    wraplength=460,
                    justify="left",
                    anchor="w"
                ).pack(anchor="w")

                tk.Label(
                    bubble,
                    text=created_at or "",
                    font=("Segoe UI", 8),
                    bg=bubble_bg,
                    fg=MUTED_COLOR
                ).pack(anchor="e", pady=(5, 0))

            chat_frame.update_idletasks()
            chat_canvas.configure(
                scrollregion=chat_canvas.bbox("all")
            )
            chat_canvas.yview_moveto(1.0)

            message_entry.focus_set()



        # =========================
        # SEND MESSAGE
        # =========================
        def send_message(event=None):
            customer_name = selected_customer["name"]
            text = message_var.get().strip()

            if not customer_name:
                messagebox.showwarning(
                    "Select Customer",
                    "Pumili muna ng customer."
                )
                return "break"

            if not text:
                return "break"

            created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

            con = connect()
            try:
                con.execute("""
                    INSERT INTO messages
                    (
                        sender, recipient, sender_role,
                        message, created_at, is_read, important
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    "admin",
                    customer_name,
                    "admin",
                    text,
                    created_at,
                    0,
                    0
                ))
                con.commit()
            except Exception as e:
                messagebox.showerror(
                    "Send Message Error",
                    f"Hindi naipadala ang message.\n\n{e}"
                )
                return "break"
            finally:
                con.close()

            message_var.set("")
            show_conversation(customer_name)
            return "break"

        send_button = tk.Button(
            composer_box,
            text="➤",
            font=("Segoe UI Symbol", 15, "bold"),
            bg=PINK,
            fg="white",
            activebackground="#E33178",
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=18,
            pady=7,
            command=send_message
        )
        send_button.pack(side="right", padx=5, pady=5)

        message_entry.bind("<Return>", send_message)

        # =========================
        # RENDER CUSTOMER INBOX
        # =========================
        def refresh_customer_list(*args):
            for widget in customer_frame.winfo_children():
                widget.destroy()

            query = search_var.get().strip().lower()
            count = 0

            sorted_customers = sorted(
                customer_names,
                key=lambda name: (
                    get_latest_message(name)[1]
                    if get_latest_message(name)
                    else ""
                ),
                reverse=True
            )

            for customer_name in sorted_customers:
                if query and query not in customer_name.lower():
                    continue

                latest = get_latest_message(customer_name)
                unread = get_unread_count(customer_name)

                preview = "No messages yet"
                timestamp = ""

                if latest:
                    preview = str(latest[0] or "").replace("\n", " ")
                    timestamp = str(latest[1] or "")

                    if len(preview) > 100:
                        preview = preview[:97] + "..."

                row = tk.Frame(
                    customer_frame,
                    bg=WHITE,
                    highlightbackground=BORDER_COLOR,
                    highlightthickness=1,
                    cursor="hand2"
                )
                row.pack(fill="x", padx=8, pady=5)

                row_inner = tk.Frame(
                    row,
                    bg=WHITE,
                    padx=14,
                    pady=12,
                    cursor="hand2"
                )
                row_inner.pack(fill="x")

                initials = "".join(
                    part[0]
                    for part in customer_name.split()
                    if part
                )[:2].upper()

                avatar = tk.Label(
                    row_inner,
                    text=initials or "?",
                    font=("Segoe UI", 11, "bold"),
                    bg="#E8DDFC",
                    fg=PURPLE,
                    width=4,
                    height=2,
                    cursor="hand2"
                )
                avatar.pack(side="left", padx=(0, 13))

                details = tk.Frame(
                    row_inner,
                    bg=WHITE,
                    cursor="hand2"
                )
                details.pack(side="left", fill="x", expand=True)

                title_line = tk.Frame(
                    details,
                    bg=WHITE,
                    cursor="hand2"
                )
                title_line.pack(fill="x")

                name_label = tk.Label(
                    title_line,
                    text=customer_name,
                    font=("Segoe UI", 11, "bold"),
                    bg=WHITE,
                    fg=DARK,
                    anchor="w",
                    cursor="hand2"
                )
                name_label.pack(side="left", fill="x", expand=True)

                time_label = tk.Label(
                    title_line,
                    text=timestamp,
                    font=("Segoe UI", 8),
                    bg=WHITE,
                    fg=MUTED_COLOR,
                    cursor="hand2"
                )
                time_label.pack(side="right", padx=(8, 0))

                preview_label = tk.Label(
                    details,
                    text=preview,
                    font=("Segoe UI", 9),
                    bg=WHITE,
                    fg=MUTED_COLOR,
                    anchor="w",
                    justify="left",
                    wraplength=850,
                    cursor="hand2"
                )
                preview_label.pack(fill="x", pady=(5, 0))

                def open_chat(event=None, name=customer_name):
                    show_conversation(name)
                    return "break"

                # Bind click on the entire customer row.
                for widget in (
                    row,
                    row_inner,
                    avatar,
                    details,
                    title_line,
                    name_label,
                    time_label,
                    preview_label
                ):
                    widget.bind("<Button-1>", open_chat)

                if unread:
                    unread_badge = tk.Label(
                        title_line,
                        text=str(unread),
                        font=("Segoe UI", 8, "bold"),
                        bg=PINK,
                        fg="white",
                        padx=7,
                        pady=3,
                        cursor="hand2"
                    )
                    unread_badge.pack(side="right", padx=(8, 0))
                    unread_badge.bind("<Button-1>", open_chat)

                count += 1

            if count == 0:
                tk.Label(
                    customer_frame,
                    text="No conversations found.",
                    font=("Segoe UI", 11),
                    bg=WHITE,
                    fg=MUTED_COLOR
                ).pack(pady=45)

            customer_frame.update_idletasks()
            list_canvas.configure(
                scrollregion=list_canvas.bbox("all")
            )

        search_var.trace_add("write", refresh_customer_list)
        refresh_customer_list()
