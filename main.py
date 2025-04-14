import tkinter as tk
from tkinter import ttk, messagebox
import subprocess, os, json
from tkinter import simpledialog, filedialog
import nbformat
from transformers import pipeline
import random
import string
import customtkinter as ctk
from importlib.metadata import distributions
import re
import platform

# Load summarizer
summarizer = pipeline("summarization", model="t5-small")


def kill_jupyter_servers():
    if platform.system() == "Windows":
        subprocess.call("taskkill /F /IM python.exe /T", shell=True)
    else:
        subprocess.call("pkill -f jupyter-notebook", shell=True)


# Load saved paths
def load_paths():
    try:
        with open("paths.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        messagebox.showerror("Error", "paths.json not found!")
        return {}

# Launch Jupyter
def launch_jupyter():
    selected_key = path_var.get()
    use_lab = lab_var.get()
    folder_path = paths.get(selected_key)

    if folder_path and os.path.isdir(folder_path):
        command = ["jupyter", "lab" if use_lab else "notebook"]

        # Optional: Set runtime folder in a safe location relative to current script
        runtime_dir = os.path.join(os.getcwd(), "runtime")
        os.makedirs(runtime_dir, exist_ok=True)
        os.environ["JUPYTER_RUNTIME_DIR"] = runtime_dir

        subprocess.Popen(command, cwd=folder_path)
    else:
        messagebox.showerror("Invalid Path", "The selected folder path doesn't exist.")

# Save new path
def click():
    key = simpledialog.askstring("Input", "Enter the key name:")
    path = filedialog.askdirectory(title="Select a folder for the path")

    try:
        with open("paths.json", "r", encoding="utf-8") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    if key and path:
        data[key] = path
        with open("paths.json", "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        paths.update({key: path})
        dropdown["values"] = list(paths.keys())
        path_var.set(key)
        on_key_select()
    else:
        print("Key or path not provided.")

# Delete selected path
def delete_selected():
    selected_key = path_var.get()
    if not selected_key:
        messagebox.showwarning("No Selection", "Please select a key to delete.")
        return

    confirm = messagebox.askyesno("Confirm Delete", f"Delete '{selected_key}'?")
    if confirm:
        try:
            with open("paths.json", "r", encoding="utf-8") as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        if selected_key in data:
            del data[selected_key]
            with open("paths.json", "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)
            paths.pop(selected_key, None)
            dropdown["values"] = list(paths.keys())
            path_var.set("")
            summary_text.config(state="normal")
            summary_text.delete(1.0, "end")
            summary_text.config(state="disabled")
            messagebox.showinfo("Deleted", f"'{selected_key}' removed.")
        else:
            messagebox.showwarning("Key Not Found", "Key doesn't exist.")

# Rename key
def rename_key():
    old_key = path_var.get()
    if not old_key:
        messagebox.showerror("Error", "No key selected to rename.")
        return
    new_key = simpledialog.askstring("Rename Key", f"Enter new name for '{old_key}':")
    if not new_key: return
    if new_key in paths:
        messagebox.showerror("Error", f"The key '{new_key}' already exists.")
        return
    confirm = messagebox.askyesno("Confirm Rename", f"Rename '{old_key}' to '{new_key}'?")
    if not confirm: return
    paths[new_key] = paths.pop(old_key)
    with open("paths.json", "w", encoding="utf-8") as f:
        json.dump(paths, f, indent=4)
    dropdown["values"] = list(paths.keys())
    path_var.set(new_key)
    messagebox.showinfo("Success", f"Renamed '{old_key}' to '{new_key}'")

# Get first .ipynb file in folder
def get_first_notebook(folder_path):
    for file in os.listdir(folder_path):
        if file.endswith(".ipynb"):
            return os.path.join(folder_path, file)
    return None

# Read and summarize notebook
def read_notebook_text(nb_path):
    try:
        with open(nb_path, "r", encoding="utf-8") as f:
            nb = nbformat.read(f, as_version=4)
            cells = nb.cells
            text = "\n".join(cell['source'] for cell in cells if cell['cell_type'] in ('markdown', 'code'))
            return text
    except Exception as e:
        return ""

def summarize_text(text):
    try:
        if len(text) > 1000:
            text = text[:1000]
        summary = summarizer(text, max_length=80, min_length=40, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        return "Could not summarize the notebook."

# Handle dropdown selection
def on_key_select(event=None):
    selected_key = path_var.get()
    folder = paths.get(selected_key)
    if folder and os.path.isdir(folder):
        notebook = get_first_notebook(folder)
        if notebook:
            content = read_notebook_text(notebook)
            summary = summarize_text(content)
        else:
            summary = "No .ipynb notebook found in this folder."

        summary_text.config(state="normal")
        summary_text.delete(1.0, "end")
        summary_text.insert("end", summary)
        summary_text.config(state="disabled")
    else:
        summary_text.config(state="normal")
        summary_text.delete(1.0, "end")
        summary_text.insert("end", "Invalid folder path.")
        summary_text.config(state="disabled")

# Clone GitHub Repo
def open_clone_repo_window():
    repo_url = simpledialog.askstring("GitHub Repo URL", "Enter the GitHub repository HTTPS URL:")
    if not repo_url:
        return

    folder_path = filedialog.askdirectory(title="Select destination folder")
    if not folder_path:
        return

    clone_github_repo(repo_url, folder_path)

def clone_github_repo(repo_url, destination_folder):
    try:
        repo_name = repo_url.strip().split("/")[-1].replace(".git", "")
        target_path = os.path.join(destination_folder, repo_name)

        result = subprocess.run(["git", "clone", repo_url, target_path], capture_output=True, text=True)

        if result.returncode != 0:
            messagebox.showerror("Clone Failed", f"Error cloning repo:\n{result.stderr}")
            return

        random_key = f"{repo_name}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}"
        save_to_json(random_key, target_path)
        messagebox.showinfo("Success", f"Repository cloned and saved with key: {random_key}")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

def save_to_json(key, path):
    try:
        with open("paths.json", "r", encoding="utf-8") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    if key and path:
        data[key] = path
        with open("paths.json", "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        paths.update({key: path})
        dropdown["values"] = list(paths.keys())
        path_var.set(key)
        on_key_select()

# ✅ Check dependencies in requirements.txt

try:
    from importlib.metadata import version as get_version, PackageNotFoundError
except ImportError:
    from importlib_metadata import version as get_version, PackageNotFoundError  # Python < 3.8

def check_dependencies():
    file_path = filedialog.askopenfilename(title="Select requirements.txt",
                                           filetypes=[("Text Files", "requirements.txt")])
    if not file_path:
        return

    dependencies = []

    with open(file_path, 'r') as file:
        lines = file.readlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r'^([a-zA-Z0-9_\-]+)([<>=!~]*)([\d.]*)', line)
            if match:
                pkg, operator, version = match.groups()
                required = f"{operator}{version}" if operator and version else "Any"
                try:
                    installed = get_version(pkg)
                    status = "✔ Installed"
                except PackageNotFoundError:
                    installed = "Not Installed"
                    status = "✘ Missing"
                dependencies.append((pkg, required, installed, status))

    show_dependency_result(dependencies)

def show_dependency_result(dependencies):
    result_win = tk.Toplevel()
    result_win.title("Dependency Check Result")
    result_win.geometry("700x400")
    result_win.resizable(True, True)

    canvas = tk.Canvas(result_win)
    scrollbar = tk.Scrollbar(result_win, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    tk.Label(scrollable_frame, text="Package", width=20, anchor='w', font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=5, pady=5)
    tk.Label(scrollable_frame, text="Required Version", width=20, anchor='w', font=("Segoe UI", 10, "bold")).grid(row=0, column=1, padx=5, pady=5)
    tk.Label(scrollable_frame, text="Installed Version", width=20, anchor='w', font=("Segoe UI", 10, "bold")).grid(row=0, column=2, padx=5, pady=5)
    tk.Label(scrollable_frame, text="Status", width=15, anchor='w', font=("Segoe UI", 10, "bold")).grid(row=0, column=3, padx=5, pady=5)

    for i, (pkg, required, installed, status) in enumerate(dependencies, start=1):
        tk.Label(scrollable_frame, text=pkg, anchor='w').grid(row=i, column=0, sticky='w', padx=5)
        tk.Label(scrollable_frame, text=required, anchor='w').grid(row=i, column=1, sticky='w', padx=5)
        tk.Label(scrollable_frame, text=installed, anchor='w').grid(row=i, column=2, sticky='w', padx=5)
        tk.Label(scrollable_frame, text=status, anchor='w', fg="green" if "✔" in status else "red").grid(row=i, column=3, sticky='w', padx=5)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")


# GUI Setup
root = ctk.CTk()
root.geometry("530x440")
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")
root.title("Smart Jupyter Launcher")
root.option_add("*TCombobox*Listbox.font", "Arial 16")


paths = load_paths()
path_keys = list(paths.keys())

style = ttk.Style()

# Set the theme (use 'clam' or 'default' for more styling flexibility)
style.theme_use('clam')

# Customize the Combobox
style.configure("Custom.TCombobox",
                fieldbackground="#f0f0f0",     # background of the field
                background="#d1e0e0",          # dropdown button color
                foreground="#333333",          # text color
                font=('Arial', 16),
                padding=5)

# UI Elements

lab_var = tk.BooleanVar()
ctk.CTkLabel(root, text="Select Folder:", font=("Arial", 16)).grid(row=0, column=0, padx=10, pady=10)
path_var = tk.StringVar(value=path_keys[0] if path_keys else "")
dropdown = ttk.Combobox(root, textvariable=path_var,style="Custom.TCombobox" ,values=path_keys, state="readonly", font=("Arial",16))
dropdown.grid(row=0, column=1, padx=10, pady=10)
dropdown.bind("<<ComboboxSelected>>", on_key_select)

ctk.CTkButton(root, text="👌 Save new path", command=click).grid(row=2, column=0, padx=5, pady=5)
ctk.CTkButton(root, text="🗑️ Delete selected", command=delete_selected).grid(row=3, column=0, padx=10, pady=5)
ctk.CTkButton(root, text="✏️ Rename Key", command=rename_key).grid(row=4, column=0, padx=5, pady=5)
ctk.CTkButton(root, text="🔍 Check Dependencies", command=check_dependencies).grid(row=5, column=0, padx=10, pady=5)
ctk.CTkButton(root, text="🔗 Clone a GitHub repo", command=open_clone_repo_window).grid(row=6,column=0,padx=10,pady=5)

ctk.CTkCheckBox(root, text="Launch Jupyter Lab",variable=lab_var, onvalue="on", offvalue="off").grid(row=1, columnspan=2, padx=10, pady=5)

ctk.CTkButton(root, text="🚀 Launch", command=launch_jupyter).grid(row=3, column=1 ,pady=10)

ctk.CTkLabel(root, text="📄 Project Summary:", font=("Arial",16)).grid(row=7, column=0, padx=10, pady=5, sticky='nw')
summary_text = tk.Text(root, height=6, width=40, wrap="word")
summary_text.grid(row=7, column=1, padx=10, pady=5)
summary_text.config(state="disabled")

# Show initial summary if key pre-selected
if path_var.get():
    on_key_select()

root.mainloop()
kill_jupyter_servers()