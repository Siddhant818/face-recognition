import cv2
import face_recognition
import os
import csv
import winsound  
from datetime import datetime, timedelta
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MultiFaceAttendanceSystem(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Biometric Hub - Stealth Edition")
        self.geometry("1400x900")

        # Configuration
        self.db_path = "faces"
        self.csv_file = "attendance.csv"
        if not os.path.exists(self.db_path): os.makedirs(self.db_path)
        
        self.known_face_encodings = []
        self.known_face_names = []
        self.is_active = False
        self.load_known_faces()

        # Layout Config
        self.grid_columnconfigure(0, weight=0) 
        self.grid_columnconfigure(1, weight=1) 
        self.grid_columnconfigure(2, weight=0) 
        self.grid_rowconfigure(0, weight=1)

        # --- LEFT SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color="#1a1c1e")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.time_lbl = ctk.CTkLabel(self.sidebar, text="00:00:00", font=ctk.CTkFont(size=32, weight="bold"))
        self.time_lbl.pack(pady=(30, 5))
        ctk.CTkLabel(self.sidebar, text="INTELLIGENT HUB", font=ctk.CTkFont(size=12)).pack(pady=(0, 20))
        
        self.status_card = ctk.CTkFrame(self.sidebar, fg_color="#282a2d", corner_radius=15)
        self.status_card.pack(pady=10, padx=20, fill="x")
        self.status_lbl = ctk.CTkLabel(self.status_card, text="SYSTEM OFFLINE", text_color="#e74c3c", font=ctk.CTkFont(weight="bold"))
        self.status_lbl.pack(pady=10)
        
        self.face_count_lbl = ctk.CTkLabel(self.sidebar, text="Presence: None Detected", font=ctk.CTkFont(size=13))
        self.face_count_lbl.pack(pady=20)

        self.start_btn = ctk.CTkButton(self.sidebar, text="ACTIVATE HUB", command=self.toggle_system, height=50, corner_radius=10, font=ctk.CTkFont(weight="bold"), fg_color="#3498db")
        self.start_btn.pack(pady=10, padx=20, fill="x")

        # Registration Card
        self.reg_card = ctk.CTkFrame(self.sidebar, fg_color="#282a2d", corner_radius=15)
        self.reg_card.pack(pady=20, padx=20, fill="x")
        self.name_entry = ctk.CTkEntry(self.reg_card, placeholder_text="Name", border_width=0)
        self.name_entry.pack(pady=10, padx=15, fill="x")
        ctk.CTkButton(self.reg_card, text="Register", command=self.register_face, fg_color="#5d6d7e").pack(pady=(0, 15), padx=15, fill="x")

        ctk.CTkButton(self.sidebar, text="Reset Data", command=self.clear_logs, fg_color="transparent", text_color="#e74c3c", border_width=1).pack(side="bottom", pady=20, padx=20, fill="x")

        # --- CENTER PANEL (Video & Screensaver) ---
        self.center_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.video_container = ctk.CTkFrame(self.center_panel, fg_color="#000", corner_radius=20)
        self.video_container.pack(expand=True, fill="both", pady=(0, 20))
        
        self.video_label = ctk.CTkLabel(self.video_container, text="")
        self.video_label.place(relx=0.5, rely=0.5, anchor="center")

        self.summary_card = ctk.CTkFrame(self.center_panel, corner_radius=15, fg_color="#1a1c1e", height=200)
        self.summary_card.pack(fill="x")
        self.summary_card.pack_propagate(False) 
        self.summary_frame = ctk.CTkScrollableFrame(self.summary_card, fg_color="transparent", orientation="horizontal")
        self.summary_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # --- RIGHT PANEL ---
        self.log_sidebar = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color="#111214")
        self.log_sidebar.grid(row=0, column=2, sticky="nsew")
        ctk.CTkLabel(self.log_sidebar, text="ACTIVITY", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        self.log_scroll = ctk.CTkScrollableFrame(self.log_sidebar, fg_color="transparent")
        self.log_scroll.pack(expand=True, fill="both", padx=10, pady=5)

        # Logic Variables
        self.cap = cv2.VideoCapture(0)
        self.face_locations = []
        self.face_names = []
        self.process_counter = 0
        self.attendance_history = {}
        
        self.screensaver_active = True
        self.scan_line_y = 0 # For screensaver animation
        
        self.update_summary_view()
        self.clock_tick()
        self.update_feed()

    def clock_tick(self):
        self.time_lbl.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.after(1000, self.clock_tick)

    def create_screensaver(self):
        """Generates a sleek scanning graphic when no one is present."""
        width, height = 800, 500
        img = Image.new('RGB', (width, height), color=(10, 12, 14))
        draw = ImageDraw.Draw(img)
        
        # Draw scanning circles
        center = (width // 2, height // 2)
        for r in range(50, 250, 50):
            draw.ellipse((center[0]-r, center[1]-r, center[0]+r, center[1]+r), outline=(40, 44, 52), width=1)
        
        # Animated Scan Line
        self.scan_line_y = (self.scan_line_y + 10) % height
        draw.line((0, self.scan_line_y, width, self.scan_line_y), fill=(52, 152, 219), width=2)
        
        # Text
        draw.text((center[0]-80, center[1]-10), "SYSTEM SECURED", fill=(100, 110, 120))
        draw.text((center[0]-95, center[1]+15), "WAITING FOR PRESENCE...", fill=(50, 60, 70))
        
        return ctk.CTkImage(img, size=(width, height))

    def play_sound(self, type="success"):
        try:
            if type == "success": winsound.Beep(1200, 100)
            elif type == "out": winsound.Beep(800, 150)
        except: pass

    def get_next_status(self, name):
        if not os.path.exists(self.csv_file): return "IN"
        last_status = "OUT"
        with open(self.csv_file, "r") as f:
            reader = list(csv.DictReader(f))
            for row in reversed(reader):
                if row['Name'] == name:
                    last_status = row['Status']
                    break
        return "OUT" if last_status == "IN" else "IN"

    def toggle_system(self):
        self.is_active = not self.is_active
        self.status_lbl.configure(text="ENGINE ACTIVE" if self.is_active else "ENGINE OFFLINE", 
                                 text_color="#2ecc71" if self.is_active else "#e74c3c")

    def auto_log_attendance(self, name):
        if name == "Unknown": return
        now = datetime.now()
        if name not in self.attendance_history or (now - self.attendance_history[name]) > timedelta(seconds=15):
            mode = self.get_next_status(name)
            self.attendance_history[name] = now
            f_exists = os.path.isfile(self.csv_file)
            with open(self.csv_file, "a", newline="") as f:
                writer = csv.writer(f)
                if not f_exists: writer.writerow(["Name", "Date", "Time", "Status"])
                writer.writerow([name, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), mode])
            self.play_sound("success" if mode == "IN" else "out")
            self.add_log_entry(name, f"AUTO-{mode}", mode)
            self.update_summary_view()

    def add_log_entry(self, name, message, type):
        color = "#2ecc71" if type == "IN" else "#e74c3c"
        card = ctk.CTkFrame(self.log_scroll, fg_color="#1e2023", height=50, corner_radius=8)
        card.pack(fill="x", pady=4, padx=5)
        ctk.CTkLabel(card, text=name.upper(), font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=15)
        ctk.CTkLabel(card, text=message, text_color=color).pack(side="right", padx=15)

    def update_summary_view(self):
        for widget in self.summary_frame.winfo_children(): widget.destroy()
        if not os.path.exists(self.csv_file): return
        headers = ["STAFF NAME", "STATUS", "DAILY HOURS"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self.summary_frame, text=h, font=ctk.CTkFont(size=11, weight="bold"), text_color="#7f8c8d").grid(row=0, column=i, padx=40, pady=5)

        data = {}
        with open(self.csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'Name' not in row: continue
                n = row['Name']
                dt = datetime.strptime(f"{row['Date']} {row['Time']}", "%Y-%m-%d %H:%M:%S")
                if n not in data: data[n] = []
                data[n].append({'dt': dt, 'status': row['Status']})

        for idx, (name, logs) in enumerate(data.items(), start=1):
            total_sec, last_in = 0, None
            logs.sort(key=lambda x: x['dt'])
            for l in logs:
                if l['status'] == "IN": last_in = l['dt']
                elif l['status'] == "OUT" and last_in:
                    total_sec += (l['dt'] - last_in).total_seconds()
                    last_in = None
            h, m = int(total_sec // 3600), int((total_sec % 3600) // 60)
            status = logs[-1]['status']
            ctk.CTkLabel(self.summary_frame, text=name, font=ctk.CTkFont(weight="bold")).grid(row=idx, column=0, padx=40)
            ctk.CTkLabel(self.summary_frame, text=status, text_color="#2ecc71" if status=="IN" else "#e74c3c").grid(row=idx, column=1)
            ctk.CTkLabel(self.summary_frame, text=f"{h}h {m}m", font=("Consolas", 13)).grid(row=idx, column=2, padx=40)

    def update_feed(self):
        ret, frame = self.cap.read()
        if not ret:
            self.after(20, self.update_feed)
            return

        frame = cv2.flip(frame, 1)
        
        if self.is_active:
            # Face processing logic
            if self.process_counter % 5 == 0:
                rgb_small = cv2.cvtColor(cv2.resize(frame, (0,0), fx=0.25, fy=0.25), cv2.COLOR_BGR2RGB)
                self.face_locations = face_recognition.face_locations(rgb_small)
                
                if self.face_locations:
                    self.screensaver_active = False
                    encs = face_recognition.face_encodings(rgb_small, self.face_locations)
                    self.face_names = []
                    for enc in encs:
                        matches = face_recognition.compare_faces(self.known_face_encodings, enc, 0.45)
                        name = "Unknown"
                        if any(matches):
                            name = self.known_face_names[np.argmin(face_recognition.face_distance(self.known_face_encodings, enc))]
                            self.auto_log_attendance(name)
                        self.face_names.append(name)
                else:
                    self.screensaver_active = True
                
                self.face_count_lbl.configure(text=f"Presence: {len(self.face_locations)} Detected" if not self.screensaver_active else "Presence: Searching...")

            if not self.screensaver_active:
                for (t, r, b, l), name in zip(self.face_locations, self.face_names):
                    t*=4; r*=4; b*=4; l*=4
                    clr = (255, 255, 255) if name == "Unknown" else (46, 204, 113)
                    cv2.rectangle(frame, (l, t), (r, b), clr, 2)
                    cv2.putText(frame, name, (l, t-10), 1, 1, clr, 2)
                
                img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                final_img = ctk.CTkImage(img_pil, size=(800, 500))
            else:
                final_img = self.create_screensaver()
        else:
            final_img = self.create_screensaver()

        self.video_label.configure(image=final_img, text="")
        self.process_counter += 1
        self.after(20, self.update_feed)

    def load_known_faces(self):
        self.known_face_encodings, self.known_face_names = [], []
        for file in os.listdir(self.db_path):
            if file.lower().endswith((".jpg", ".png", ".jpeg")):
                img = face_recognition.load_image_file(os.path.join(self.db_path, file))
                encs = face_recognition.face_encodings(img)
                if encs:
                    self.known_face_encodings.append(encs[0])
                    self.known_face_names.append(os.path.splitext(file)[0])

    def register_face(self):
        name = self.name_entry.get().strip()
        if not name: return
        ret, frame = self.cap.read()
        if ret:
            cv2.imwrite(os.path.join(self.db_path, f"{name}.jpg"), frame)
            self.load_known_faces()
            self.add_log_entry("SYSTEM", "User Registered", "IN")
            self.name_entry.delete(0, 'end')

    def clear_logs(self):
        if os.path.exists(self.csv_file): os.remove(self.csv_file)
        self.update_summary_view()

if __name__ == "__main__":
    app = MultiFaceAttendanceSystem()
    app.mainloop()