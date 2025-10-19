# macro_plus.py - Main Application File
import customtkinter as ctk
from pynput import keyboard, mouse
from pynput.keyboard import Key, Controller as KeyboardController, GlobalHotKeys
from pynput.mouse import Button, Controller as MouseController
import threading
import time
import json
import os
import sys
from datetime import datetime
import pygetwindow as gw
from collections import deque
from pathlib import Path

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MacroRecorder:
    def __init__(self):
        # Setup application directories
        self.setup_directories()
        
        self.window = ctk.CTk()
        self.window.title("Macro+ v1.0")
        self.window.geometry("450x650")
        self.window.resizable(False, False)
        self.window.configure(fg_color="#1a1a1a")
        
        # Set icon if available
        icon_path = self.app_dir / "resources" / "icon.ico"
        if icon_path.exists():
            self.window.iconbitmap(str(icon_path))
        
        # State
        self.is_recording = False
        self.is_playing = False
        self.recorded_events = []
        self.start_time = None
        self.playback_speed = 1.0
        self.repeat_count = 1
        self.event_buffer = deque(maxlen=10000)
        self.buffer_lock = threading.Lock()
        self.last_mouse_pos = None
        
        # Controllers
        self.keyboard_controller = KeyboardController()
        self.mouse_controller = MouseController()
        self.keyboard_listener = None
        self.mouse_listener = None
        self.hotkey_listener = None
        
        # Load settings
        self.load_settings()
        
        self.setup_hotkeys()
        self.setup_ui()
        
    def setup_directories(self):
        """Setup application directory structure"""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            self.app_dir = Path(os.environ.get('LOCALAPPDATA')) / "MacroPlus"
        else:
            # Running as script
            self.app_dir = Path.cwd()
        
        # Create directory structure
        self.macros_dir = self.app_dir / "macros"
        self.settings_dir = self.app_dir / "settings"
        self.logs_dir = self.app_dir / "logs"
        self.resources_dir = self.app_dir / "resources"
        
        for directory in [self.macros_dir, self.settings_dir, self.logs_dir, self.resources_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        self.settings_file = self.settings_dir / "config.json"
        
    def load_settings(self):
        """Load user settings"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.playback_speed = settings.get('speed', 1.0)
                    self.repeat_count = settings.get('repeat', 1)
        except:
            pass
    
    def save_settings(self):
        """Save user settings"""
        try:
            settings = {
                'speed': self.playback_speed,
                'repeat': self.repeat_count
            }
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except:
            pass
        
    def setup_hotkeys(self):
        hotkeys = {
            '<f9>': lambda: self.window.after(0, self.toggle_recording),
            '<f10>': lambda: self.window.after(0, self.play_macro) if len(self.recorded_events) > 0 else None,
            '<f11>': lambda: self.window.after(0, self.stop_recording if self.is_recording else self.stop_playback),
        }
        try:
            self.hotkey_listener = GlobalHotKeys(hotkeys)
            self.hotkey_listener.start()
        except:
            pass
        
    def setup_ui(self):
        # Main container
        main = ctk.CTkFrame(self.window, fg_color="#1a1a1a")
        main.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Title bar
        title_bar = ctk.CTkFrame(main, fg_color="#0d0d0d", height=50, corner_radius=0)
        title_bar.pack(fill="x", padx=0, pady=0)
        title_bar.pack_propagate(False)
        
        title = ctk.CTkLabel(
            title_bar,
            text="Macro+ v1.0",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffffff"
        )
        title.pack(side="left", padx=20, pady=15)
        
        version = ctk.CTkLabel(
            title_bar,
            text="Professional Edition",
            font=ctk.CTkFont(size=10),
            text_color="#666666"
        )
        version.pack(side="right", padx=20)
        
        # Recording controls section
        controls_frame = ctk.CTkFrame(main, fg_color="#1a1a1a")
        controls_frame.pack(fill="x", padx=15, pady=15)
        
        # Record button - large and prominent
        self.record_btn = ctk.CTkButton(
            controls_frame,
            text="● Record",
            command=self.toggle_recording,
            corner_radius=8,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#dc3545",
            hover_color="#c82333",
            text_color="#ffffff"
        )
        self.record_btn.pack(fill="x", pady=(0, 8))
        
        # Playback controls row
        playback_row = ctk.CTkFrame(controls_frame, fg_color="transparent")
        playback_row.pack(fill="x", pady=(0, 8))
        
        self.play_btn = ctk.CTkButton(
            playback_row,
            text="▶ Play",
            command=self.play_macro,
            corner_radius=8,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#28a745",
            hover_color="#218838",
            state="disabled"
        )
        self.play_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        self.stop_btn = ctk.CTkButton(
            playback_row,
            text="■ Stop",
            command=self.stop_playback,
            corner_radius=8,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268",
            state="disabled"
        )
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))
        
        # Settings section
        settings_frame = ctk.CTkFrame(main, fg_color="#252525", corner_radius=8)
        settings_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        # Speed control
        speed_label = ctk.CTkLabel(
            settings_frame,
            text="Playback Speed:",
            font=ctk.CTkFont(size=13),
            text_color="#cccccc"
        )
        speed_label.pack(anchor="w", padx=15, pady=(15, 5))
        
        speed_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        speed_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.speed_var = ctk.DoubleVar(value=self.playback_speed)
        self.speed_slider = ctk.CTkSlider(
            speed_frame,
            from_=0.1,
            to=3.0,
            variable=self.speed_var,
            command=self.update_speed_label,
            height=20,
            button_color="#007bff",
            button_hover_color="#0056b3",
            progress_color="#007bff",
            fg_color="#3a3a3a"
        )
        self.speed_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.speed_label = ctk.CTkLabel(
            speed_frame,
            text=f"{self.playback_speed:.1f}x",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff",
            width=50
        )
        self.speed_label.pack(side="left")
        
        # Repeat control
        repeat_label = ctk.CTkLabel(
            settings_frame,
            text="Repeat Count:",
            font=ctk.CTkFont(size=13),
            text_color="#cccccc"
        )
        repeat_label.pack(anchor="w", padx=15, pady=(5, 5))
        
        repeat_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        repeat_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.repeat_var = ctk.IntVar(value=self.repeat_count)
        self.repeat_entry = ctk.CTkEntry(
            repeat_frame,
            textvariable=self.repeat_var,
            corner_radius=6,
            height=35,
            justify="center",
            font=ctk.CTkFont(size=14),
            fg_color="#3a3a3a",
            border_width=1,
            border_color="#4a4a4a",
            text_color="#ffffff"
        )
        self.repeat_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        infinite_btn = ctk.CTkButton(
            repeat_frame,
            text="∞ Infinite",
            command=lambda: self.repeat_var.set(0),
            corner_radius=6,
            height=35,
            fg_color="#007bff",
            hover_color="#0056b3",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=90
        )
        infinite_btn.pack(side="left")
        
        # Status section
        status_frame = ctk.CTkFrame(main, fg_color="#252525", corner_radius=8)
        status_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Ready",
            font=ctk.CTkFont(size=13),
            text_color="#28a745"
        )
        self.status_label.pack(pady=12)
        
        # Stats row
        stats_row = ctk.CTkFrame(status_frame, fg_color="transparent")
        stats_row.pack(fill="x", padx=15, pady=(0, 12))
        
        self.events_label = ctk.CTkLabel(
            stats_row,
            text="Events: 0",
            font=ctk.CTkFont(size=12),
            text_color="#999999"
        )
        self.events_label.pack(side="left")
        
        self.duration_label = ctk.CTkLabel(
            stats_row,
            text="Duration: 0.0s",
            font=ctk.CTkFont(size=12),
            text_color="#999999"
        )
        self.duration_label.pack(side="right")
        
        # Macro library section
        library_frame = ctk.CTkFrame(main, fg_color="#252525", corner_radius=8)
        library_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        library_header = ctk.CTkLabel(
            library_frame,
            text="Saved Macros",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff"
        )
        library_header.pack(anchor="w", padx=15, pady=(15, 10))
        
        # Macro name entry
        entry_frame = ctk.CTkFrame(library_frame, fg_color="transparent")
        entry_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.macro_entry = ctk.CTkEntry(
            entry_frame,
            placeholder_text="Macro name...",
            corner_radius=6,
            height=35,
            font=ctk.CTkFont(size=13),
            fg_color="#3a3a3a",
            border_width=1,
            border_color="#4a4a4a",
            placeholder_text_color="#666666",
            text_color="#ffffff"
        )
        self.macro_entry.pack(fill="x")
        
        # Action buttons
        actions_row1 = ctk.CTkFrame(library_frame, fg_color="transparent")
        actions_row1.pack(fill="x", padx=15, pady=(0, 6))
        
        save_btn = ctk.CTkButton(
            actions_row1,
            text="Save",
            command=self.save_macro,
            corner_radius=6,
            height=35,
            fg_color="#007bff",
            hover_color="#0056b3",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        save_btn.pack(side="left", fill="x", expand=True, padx=(0, 3))
        
        load_btn = ctk.CTkButton(
            actions_row1,
            text="Load",
            command=self.load_macro,
            corner_radius=6,
            height=35,
            fg_color="#17a2b8",
            hover_color="#138496",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        load_btn.pack(side="left", fill="x", expand=True, padx=(3, 3))
        
        delete_btn = ctk.CTkButton(
            actions_row1,
            text="Delete",
            command=self.delete_macro,
            corner_radius=6,
            height=35,
            fg_color="#dc3545",
            hover_color="#c82333",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        delete_btn.pack(side="left", fill="x", expand=True, padx=(3, 0))
        
        # Macro list
        list_frame = ctk.CTkFrame(library_frame, fg_color="#1a1a1a", corner_radius=6)
        list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        self.macro_list = ctk.CTkTextbox(
            list_frame,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color="#1a1a1a",
            text_color="#cccccc",
            border_width=0
        )
        self.macro_list.pack(fill="both", expand=True, padx=2, pady=2)
        self.update_macro_list()
        
        # Hotkeys info at bottom
        hotkeys_label = ctk.CTkLabel(
            main,
            text="F9: Record/Stop | F10: Play | F11: Stop Playback",
            font=ctk.CTkFont(size=10),
            text_color="#666666"
        )
        hotkeys_label.pack(pady=(0, 10))
        
        # Bind close event to save settings
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_closing(self):
        """Handle window close event"""
        self.save_settings()
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.window.destroy()
    
    def update_speed_label(self, value):
        self.playback_speed = float(value)
        self.speed_label.configure(text=f"{self.playback_speed:.1f}x")
    
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        self.is_recording = True
        self.recorded_events = []
        self.event_buffer.clear()
        self.start_time = time.time()
        self.last_mouse_pos = None
        
        self.record_btn.configure(text="⏸ Recording...", fg_color="#fd7e14")
        self.play_btn.configure(state="disabled")
        self.update_status("Recording...", "#fd7e14")
        
        threading.Thread(target=self.start_listeners, daemon=True).start()
    
    def start_listeners(self):
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        self.mouse_listener = mouse.Listener(
            on_click=self.on_mouse_click,
            on_move=self.on_mouse_move
        )
        self.keyboard_listener.start()
        self.mouse_listener.start()
    
    def stop_recording(self):
        self.is_recording = False
        
        with self.buffer_lock:
            self.recorded_events.extend(list(self.event_buffer))
            self.event_buffer.clear()
        
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        
        self.record_btn.configure(text="● Record", fg_color="#dc3545")
        if self.recorded_events:
            self.play_btn.configure(state="normal")
        
        duration = self.recorded_events[-1]['timestamp'] if self.recorded_events else 0
        self.update_status(f"Recorded {len(self.recorded_events)} events", "#28a745")
        self.events_label.configure(text=f"Events: {len(self.recorded_events)}")
        self.duration_label.configure(text=f"Duration: {duration:.1f}s")
    
    def on_key_press(self, key):
        if self.is_recording:
            with self.buffer_lock:
                self.event_buffer.append({
                    'type': 'key_press',
                    'key': str(key),
                    'timestamp': time.time() - self.start_time
                })
    
    def on_key_release(self, key):
        if self.is_recording:
            with self.buffer_lock:
                self.event_buffer.append({
                    'type': 'key_release',
                    'key': str(key),
                    'timestamp': time.time() - self.start_time
                })
    
    def on_mouse_click(self, x, y, button, pressed):
        if self.is_recording:
            with self.buffer_lock:
                self.event_buffer.append({
                    'type': 'mouse_click',
                    'x': x, 'y': y,
                    'button': str(button),
                    'pressed': pressed,
                    'timestamp': time.time() - self.start_time
                })
    
    def on_mouse_move(self, x, y):
        """Smooth mouse movement recording with interpolation"""
        if self.is_recording:
            current_time = time.time() - self.start_time
            
            # Record at higher frequency for smoother playback
            if not self.event_buffer or current_time - self.event_buffer[-1]['timestamp'] > 0.016:  # ~60fps
                with self.buffer_lock:
                    self.event_buffer.append({
                        'type': 'mouse_move',
                        'x': x, 'y': y,
                        'timestamp': current_time
                    })
                self.last_mouse_pos = (x, y)
    
    def play_macro(self):
        if not self.recorded_events:
            self.update_status("No macro loaded", "#ffc107")
            return
        
        self.is_playing = True
        self.play_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.record_btn.configure(state="disabled")
        
        repeat = self.repeat_var.get()
        repeat_text = "∞" if repeat == 0 else str(repeat)
        self.update_status(f"Playing (Repeat: {repeat_text})", "#28a745")
        
        threading.Thread(target=self.playback_thread, args=(repeat,), daemon=True).start()
    
    def playback_thread(self, repeat):
        iterations = 0
        while self.is_playing:
            if repeat != 0 and iterations >= repeat:
                break
            
            start_time = time.time()
            last_mouse_event = None
            
            for i, event in enumerate(self.recorded_events):
                if not self.is_playing:
                    break
                
                target_time = start_time + (event['timestamp'] / self.playback_speed)
                sleep_time = target_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                try:
                    if event['type'] == 'key_press':
                        self.simulate_key(event['key'], True)
                    elif event['type'] == 'key_release':
                        self.simulate_key(event['key'], False)
                    elif event['type'] == 'mouse_click':
                        self.simulate_click(event)
                    elif event['type'] == 'mouse_move':
                        # Smooth mouse movement with interpolation
                        if last_mouse_event and last_mouse_event['type'] == 'mouse_move':
                            self.smooth_mouse_move(
                                last_mouse_event['x'], last_mouse_event['y'],
                                event['x'], event['y'],
                                steps=5
                            )
                        else:
                            self.mouse_controller.position = (event['x'], event['y'])
                        last_mouse_event = event
                except:
                    pass
            
            iterations += 1
            if repeat == 0 or iterations < repeat:
                time.sleep(0.1)
        
        self.is_playing = False
        self.window.after(0, self.playback_finished)
    
    def smooth_mouse_move(self, x1, y1, x2, y2, steps=5):
        """Interpolate mouse movement for smoother playback"""
        for i in range(1, steps + 1):
            if not self.is_playing:
                break
            ratio = i / steps
            x = int(x1 + (x2 - x1) * ratio)
            y = int(y1 + (y2 - y1) * ratio)
            self.mouse_controller.position = (x, y)
            time.sleep(0.001)  # Tiny delay for smooth movement
    
    def simulate_key(self, key_str, press):
        try:
            if key_str.startswith("Key."):
                key = getattr(Key, key_str.replace("Key.", ""), None)
                if key:
                    self.keyboard_controller.press(key) if press else self.keyboard_controller.release(key)
            else:
                key_char = key_str.strip("'")
                self.keyboard_controller.press(key_char) if press else self.keyboard_controller.release(key_char)
        except:
            pass
    
    def simulate_click(self, event):
        self.mouse_controller.position = (event['x'], event['y'])
        button = Button.left if 'left' in event['button'].lower() else Button.right
        if event['pressed']:
            self.mouse_controller.press(button)
        else:
            self.mouse_controller.release(button)
    
    def stop_playback(self):
        self.is_playing = False
    
    def playback_finished(self):
        self.play_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.record_btn.configure(state="normal")
        self.update_status("Playback complete", "#28a745")
    
    def save_macro(self):
        name = self.macro_entry.get().strip()
        if not name:
            self.update_status("Enter a macro name", "#ffc107")
            return
        
        if not self.recorded_events:
            self.update_status("No macro to save", "#ffc107")
            return
        
        macro_data = {
            'name': name,
            'events': self.recorded_events,
            'created': datetime.now().isoformat(),
            'duration': self.recorded_events[-1]['timestamp'] if self.recorded_events else 0,
            'event_count': len(self.recorded_events),
            'speed': self.playback_speed,
            'repeat': self.repeat_var.get()
        }
        
        macro_file = self.macros_dir / f"{name}.json"
        with open(macro_file, 'w') as f:
            json.dump(macro_data, f, indent=2)
        
        self.update_status(f"Saved '{name}'", "#28a745")
        self.update_macro_list()
        self.macro_entry.delete(0, 'end')
    
    def load_macro(self):
        name = self.macro_entry.get().strip()
        if not name:
            self.update_status("Enter macro name to load", "#ffc107")
            return
        
        macro_file = self.macros_dir / f"{name}.json"
        if not macro_file.exists():
            self.update_status(f"Macro '{name}' not found", "#dc3545")
            return
        
        with open(macro_file, 'r') as f:
            macro_data = json.load(f)
        
        self.recorded_events = macro_data['events']
        if 'speed' in macro_data:
            self.speed_var.set(macro_data['speed'])
        if 'repeat' in macro_data:
            self.repeat_var.set(macro_data['repeat'])
        
        self.play_btn.configure(state="normal")
        duration = macro_data.get('duration', 0)
        self.events_label.configure(text=f"Events: {len(self.recorded_events)}")
        self.duration_label.configure(text=f"Duration: {duration:.1f}s")
        self.update_status(f"Loaded '{name}'", "#28a745")
    
    def delete_macro(self):
        name = self.macro_entry.get().strip()
        if not name:
            self.update_status("Enter macro name to delete", "#ffc107")
            return
        
        macro_file = self.macros_dir / f"{name}.json"
        if not macro_file.exists():
            self.update_status(f"Macro '{name}' not found", "#dc3545")
            return
        
        macro_file.unlink()
        self.update_status(f"Deleted '{name}'", "#dc3545")
        self.update_macro_list()
        self.macro_entry.delete(0, 'end')
    
    def update_macro_list(self):
        self.macro_list.delete("1.0", "end")
        
        macros = list(self.macros_dir.glob("*.json"))
        
        if not macros:
            self.macro_list.insert("1.0", "No saved macros.\n\nRecord and save your first macro!")
            return
        
        for macro_file in sorted(macros):
            try:
                with open(macro_file, 'r') as f:
                    data = json.load(f)
                
                name = data['name']
                events = data.get('event_count', len(data['events']))
                duration = data.get('duration', 0)
                created = data.get('created', 'Unknown')[:10]
                
                self.macro_list.insert("end",
                    f"• {name}\n"
                    f"  {events} events, {duration:.1f}s - {created}\n\n")
            except:
                pass
    
    def update_status(self, message, color):
        self.status_label.configure(text=message, text_color=color)
    
    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = MacroRecorder()
    app.run()