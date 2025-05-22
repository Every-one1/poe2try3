import tkinter as tk
from tkinter import ttk
import threading

# Attempt to import storage and LLM components
try:
    from storage.json_storage import load_latest_patch_note
    from llm_interface.gemini_analyzer import summarize_patch_note_with_llm, API_KEY as GEMINI_API_KEY
    LLM_AVAILABLE = True
except ImportError as e:
    print(f"Error importing LLM/storage modules: {e}. Some features might be unavailable.")
    LLM_AVAILABLE = False
    GEMINI_API_KEY = None 
    def load_latest_patch_note(progress_callback=None): return None # Mock
    def summarize_patch_note_with_llm(patch_data): return "LLM functionality not available." # Mock

from tkinter import filedialog

# Attempt to import the GUI pipeline function
try:
    from main import run_patch_notes_pipeline_gui, analyze_build_gui
    PIPELINE_AVAILABLE = True
    ANALYZE_BUILD_AVAILABLE = True
except ImportError as e:
    print(f"Error importing from main: {e}. Some features might be disabled.")
    PIPELINE_AVAILABLE = False
    ANALYZE_BUILD_AVAILABLE = False
    def run_patch_notes_pipeline_gui(progress_callback): # Mock
        progress_callback("Error: Patch notes pipeline function not available.")
        return
    def analyze_build_gui(xml_filepath, user_goals, progress_callback, get_gemini_api_key_func): # Mock
        progress_callback("Error: Build analysis function not available.")
        return None, None


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Path of Exile 2 Information Tool")
        self.geometry("900x700")
        self.current_patch_data = None
        self.selected_xml_path = None

        # --- Dark Theme Colors ---
        APP_BG = "#2B2B2B"
        TEXT_AREA_BG = "#3C3F41"
        TEXT_FG = "#BBBBBB"
        BUTTON_BG = "#555555"
        BUTTON_FG = "#FFFFFF"
        ENTRY_BG = "#3C3F41" # Same as TEXT_AREA_BG for consistency
        ENTRY_FG = "#BBBBBB" # Same as TEXT_FG
        FRAME_BG = APP_BG # ttk.Frame will use this via style
        LABEL_FG = TEXT_FG
        BUTTON_ACTIVE_BG = "#656565"
        DISABLED_BUTTON_FG = "#999999"

        self.configure(bg=APP_BG)

        # --- Style Configuration ---
        style = ttk.Style(self)
        style.theme_use('default') # Start with a base theme that allows overrides

        # General Frame style (for ttk.Frame)
        style.configure("TFrame", background=FRAME_BG)
        
        # LabelFrame style
        style.configure("TLabelFrame", background=FRAME_BG, relief=tk.SOLID, borderwidth=1)
        style.configure("TLabelFrame.Label", background=FRAME_BG, foreground=LABEL_FG, font=('TkDefaultFont', 9, 'bold'))

        # Button style
        style.configure("TButton", 
                        background=BUTTON_BG, 
                        foreground=BUTTON_FG, 
                        padding=6, 
                        relief=tk.FLAT, 
                        font=('TkDefaultFont', 9))
        style.map("TButton",
                  background=[('active', BUTTON_ACTIVE_BG), ('disabled', '#4A4A4A')],
                  foreground=[('disabled', DISABLED_BUTTON_FG)])

        # Label style
        style.configure("TLabel", background=FRAME_BG, foreground=LABEL_FG, padding=3)
        
        # Entry style
        style.configure("TEntry", 
                        fieldbackground=ENTRY_BG, 
                        foreground=ENTRY_FG, 
                        insertcolor=TEXT_FG, # Cursor color
                        relief=tk.FLAT,
                        borderwidth=1, # Subtle border
                        padding=4)
        style.map("TEntry",
                  fieldbackground=[('disabled', TEXT_AREA_BG)], # Keep bg same when disabled
                  foreground=[('disabled', DISABLED_BUTTON_FG)])


        # Main frame - using ttk.Frame to inherit style
        main_frame = ttk.Frame(self, padding="10", style="TFrame")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Action buttons frame (Row 0)
        action_frame = ttk.LabelFrame(main_frame, text="Actions", padding="10")
        action_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        main_frame.grid_columnconfigure(0, weight=1)

        self.patch_notes_button = ttk.Button(action_frame, text="View Latest Patch Note", command=self._load_and_display_latest_patch)
        self.patch_notes_button.grid(row=0, column=0, padx=5, pady=5)

        self.generate_llm_summary_button = ttk.Button(action_frame, text="Generate LLM Summary", command=self._start_llm_summary_task, state=tk.DISABLED)
        self.generate_llm_summary_button.grid(row=0, column=1, padx=5, pady=5)
        
        self.scrape_patches_button = ttk.Button(action_frame, text="Scrape New Patch Notes", command=self._start_patch_scraping_task)
        if not PIPELINE_AVAILABLE:
            self.scrape_patches_button.config(state=tk.DISABLED)
        self.scrape_patches_button.grid(row=0, column=2, padx=5, pady=5)

        # Build Analysis Input Frame (Row 1)
        build_analysis_input_frame = ttk.LabelFrame(main_frame, text="Build Analysis Setup", padding="10")
        build_analysis_input_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        build_analysis_input_frame.grid_columnconfigure(1, weight=1)

        self.select_xml_button = ttk.Button(build_analysis_input_frame, text="Select PoB XML File", command=self._select_xml_file)
        self.select_xml_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.xml_file_label = ttk.Label(build_analysis_input_frame, text="No file selected.")
        self.xml_file_label.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        user_goals_label = ttk.Label(build_analysis_input_frame, text="User Goals/Context:")
        user_goals_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.user_goals_entry = ttk.Entry(build_analysis_input_frame, width=80)
        self.user_goals_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.analyze_build_button = ttk.Button(build_analysis_input_frame, text="Analyze Build from XML", command=self._start_build_analysis_task)
        if not ANALYZE_BUILD_AVAILABLE:
            self.analyze_build_button.config(state=tk.DISABLED)
        self.analyze_build_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        # Content display area (Row 2)
        content_frame = ttk.LabelFrame(main_frame, text="Content", padding="10")
        content_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        main_frame.grid_rowconfigure(2, weight=1)

        self.content_text = tk.Text(content_frame, wrap=tk.WORD, state=tk.NORMAL, 
                                    bg=TEXT_AREA_BG, fg=TEXT_FG, insertbackground=TEXT_FG,
                                    relief=tk.FLAT, borderwidth=0, highlightthickness=0)
        self.content_text.grid(row=0, column=0, sticky="nsew")
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        self._clear_content_text() # Also applies disabled background

        # Status bar (Row 3)
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        main_frame.grid_rowconfigure(3, weight=0)

        self.status_text = tk.Text(status_frame, height=5, wrap=tk.WORD, state=tk.NORMAL,
                                   bg=TEXT_AREA_BG, fg=TEXT_FG, insertbackground=TEXT_FG,
                                   relief=tk.FLAT, borderwidth=0, highlightthickness=0)
        self.status_text.grid(row=0, column=0, sticky="ew")
        status_frame.grid_rowconfigure(0, weight=1) 
        status_frame.grid_columnconfigure(0, weight=1)
        self._clear_status_text() # Also applies disabled background

    def _update_content_text(self, text, clear_first=False):
        # Define TEXT_AREA_BG locally for this method or access via self if stored
        TEXT_AREA_BG = "#3C3F41" 
        self.content_text.config(state=tk.NORMAL)
        if clear_first:
            self.content_text.delete("1.0", tk.END)
        self.content_text.insert(tk.END, text + "\n")
        self.content_text.config(state=tk.DISABLED, bg=TEXT_AREA_BG) # Ensure bg persists

    def _clear_content_text(self):
        TEXT_AREA_BG = "#3C3F41" 
        self.content_text.config(state=tk.NORMAL)
        self.content_text.delete("1.0", tk.END)
        self.content_text.config(state=tk.DISABLED, bg=TEXT_AREA_BG)

    def _clear_status_text(self):
        TEXT_AREA_BG = "#3C3F41"
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete("1.0", tk.END)
        self.status_text.config(state=tk.DISABLED, bg=TEXT_AREA_BG)

    def _append_to_status_text(self, message):
        TEXT_AREA_BG = "#3C3F41"
        def append_action():
            self.status_text.config(state=tk.NORMAL, bg=TEXT_AREA_BG) # Ensure bg when normal
            self.status_text.insert(tk.END, message + "\n")
            self.status_text.see(tk.END)
            self.status_text.config(state=tk.DISABLED, bg=TEXT_AREA_BG)
        self.after(0, append_action)


    def _load_and_display_latest_patch(self):
        self._clear_content_text()
        self._clear_status_text()
        self._append_to_status_text("Loading latest patch note...")
        self.generate_llm_summary_button.config(state=tk.DISABLED)
        self.current_patch_data = None

        # Pass the GUI update method as callback
        patch_data = load_latest_patch_note(progress_callback=self._append_to_status_text)

        if patch_data:
            self.current_patch_data = patch_data
            title = patch_data.get('title', 'N/A')
            date = patch_data.get('date', 'N/A')
            summary = patch_data.get('summary', 'No pre-existing summary available.')

            display_text = f"Title: {title}\nDate: {date}\n\n--- Summary ---\n{summary}"
            self._update_content_text(display_text)
            
            if LLM_AVAILABLE and GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
                 self.generate_llm_summary_button.config(state=tk.NORMAL)
            self._append_to_status_text("Patch note loaded.") # Appended after load_latest_patch_note messages
        else:
            self._update_content_text("No patch notes found or error loading.")
            # Status already updated by load_latest_patch_note via callback

    def _start_llm_summary_task(self):
        if not self.current_patch_data:
            self._append_to_status_text("No patch data loaded to summarize.")
            return

        self._append_to_status_text("Checking API key for LLM summary...")
        if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
            self._append_to_status_text("Gemini API Key not configured. Cannot generate LLM summary.")
            return

        if not LLM_AVAILABLE:
            self._append_to_status_text("LLM functionality is not available (Import error).")
            return

        self.generate_llm_summary_button.config(state=tk.DISABLED)
        self._append_to_status_text("Generating LLM summary... (This may take a moment)")
        
        threading.Thread(target=self._llm_summary_thread_worker, daemon=True).start()
        
    def _llm_summary_thread_worker(self):
        try:
            llm_summary = summarize_patch_note_with_llm(self.current_patch_data)
            
            def update_gui_with_summary():
                if llm_summary:
                    self._update_content_text("\n\n--- LLM Summary ---\n" + llm_summary)
                    self._append_to_status_text("LLM summary generated.")
                else:
                    self._update_content_text("\n\n--- LLM Summary ---\nFailed to generate summary or summary was empty.")
                    self._append_to_status_text("LLM summary generation returned empty.")
            self.after(0, update_gui_with_summary)

        except Exception as e:
            def update_gui_with_error():
                self._update_content_text(f"\n\n--- LLM Summary ---\nError generating LLM summary: {e}")
                self._append_to_status_text(f"Error generating LLM summary: {e}")
            self.after(0, update_gui_with_error)
        finally:
            self.after(0, lambda: self.generate_llm_summary_button.config(state=tk.NORMAL))

    def _start_patch_scraping_task(self):
        if not PIPELINE_AVAILABLE:
            self._append_to_status_text("Patch scraping pipeline is not available. Check imports.")
            return
            
        self._clear_status_text() # Clear previous status messages
        self._append_to_status_text("Initiating patch notes scraping process...")
        self.scrape_patches_button.config(state=tk.DISABLED)
        
        # Worker function to run in a separate thread
        def _scrape_thread_worker():
            try:
                run_patch_notes_pipeline_gui(progress_callback=self._append_to_status_text)
            except Exception as e:
                self._append_to_status_text(f"Unhandled error in scraping thread: {e}")
            finally:
                # Ensure button is re-enabled on the main thread
                self.after(0, lambda: self.scrape_patches_button.config(state=tk.NORMAL))
        
        # Create and start the thread
        scraper_thread = threading.Thread(target=_scrape_thread_worker, daemon=True)
        scraper_thread.start()

    def _get_gemini_api_key_status(self):
        if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY": # Check for placeholder
            return GEMINI_API_KEY
        return None

    def _select_xml_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Path of Building XML File",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if filepath:
            self.selected_xml_path = filepath
            # Display only the filename for brevity in the label
            filename = filepath.split("/")[-1]
            self.xml_file_label.config(text=filename)
            self._append_to_status_text(f"Selected XML: {filename}")
        else:
            self.selected_xml_path = None
            self.xml_file_label.config(text="No file selected.")
            self._append_to_status_text("XML file selection cancelled.")

    def _start_build_analysis_task(self):
        if not ANALYZE_BUILD_AVAILABLE:
            self._append_to_status_text("Build analysis feature is not available. Check main.py imports.")
            return

        xml_path = self.selected_xml_path
        goals = self.user_goals_entry.get().strip()

        if not xml_path:
            self._append_to_status_text("Error: No XML file selected for build analysis.")
            return
        
        if not self._get_gemini_api_key_status():
            self._append_to_status_text("Error: Gemini API Key not configured. Cannot perform analysis.")
            return

        self._clear_content_text()
        # self._clear_status_text() # Keep previous status like "Selected XML..."
        self._append_to_status_text(f"Initiating build analysis for: {xml_path.split('/')[-1]}...")

        self.analyze_build_button.config(state=tk.DISABLED)
        self.select_xml_button.config(state=tk.DISABLED)
        self.user_goals_entry.config(state=tk.DISABLED)
        # Also disable other action buttons if desired during this long task
        self.patch_notes_button.config(state=tk.DISABLED)
        self.generate_llm_summary_button.config(state=tk.DISABLED)
        self.scrape_patches_button.config(state=tk.DISABLED)

        thread = threading.Thread(
            target=self._build_analysis_thread_worker, 
            args=(xml_path, goals),
            daemon=True
        )
        thread.start()

    def _build_analysis_thread_worker(self, xml_filepath, user_goals):
        try:
            report_content, saved_filepath = analyze_build_gui(
                xml_filepath=xml_filepath,
                user_goals=user_goals,
                progress_callback=self._append_to_status_text,
                get_gemini_api_key_func=self._get_gemini_api_key_status
            )

            if report_content:
                # Clear content area before adding new report
                self.after(0, lambda: self._update_content_text(report_content, clear_first=True))
                if saved_filepath:
                    self.after(0, lambda msg=f"Build analysis complete. Report saved to: {saved_filepath}": self._append_to_status_text(msg))
                else:
                    self.after(0, lambda: self._append_to_status_text("Build analysis complete (report generated but not saved to file)."))
            else:
                self.after(0, lambda: self._append_to_status_text("Build analysis failed to generate content. Check logs."))

        except Exception as e:
            self.after(0, lambda msg=f"Error during build analysis thread: {e}": self._append_to_status_text(msg))
        finally:
            def re_enable_ui():
                self.analyze_build_button.config(state=tk.NORMAL)
                self.select_xml_button.config(state=tk.NORMAL)
                self.user_goals_entry.config(state=tk.NORMAL)
                self.patch_notes_button.config(state=tk.NORMAL)
                # Re-enable LLM summary button only if conditions are met (patch loaded, API key ok)
                if self.current_patch_data and self._get_gemini_api_key_status():
                    self.generate_llm_summary_button.config(state=tk.NORMAL)
                else:
                    self.generate_llm_summary_button.config(state=tk.DISABLED)

                if PIPELINE_AVAILABLE: # Only re-enable if it was available
                    self.scrape_patches_button.config(state=tk.NORMAL)

            self.after(0, re_enable_ui)


if __name__ == "__main__":
    app = App()
    app.mainloop()
