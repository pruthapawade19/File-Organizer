import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import google.generativeai as genai
import threading


class TrieNode:
    def __init__(self):

        self.children = {}
        self.is_end_of_word = False


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True

    def search_autocomplete(self, prefix):
        node = self.root
        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]
        return self._collect_words(node, prefix)

    def _collect_words(self, node, prefix):
        result = []
        if node.is_end_of_word:
            result.append(prefix)
        for char, child in node.children.items():
            result.extend(self._collect_words(child, prefix + char))
        return result


def generate_one_word_caption(image_path, extension):

    genai.configure(api_key="AIzaSyCVSwG0aI-MizpveRCFwTdgBzcyCnu3N1w")

    sample_file = genai.upload_file(path=image_path, display_name="Sample_image")

    file = genai.get_file(name=sample_file.name)

    model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest")

    prompt = "Give a one word generic description of what is present in the image"

    response = model.generate_content([prompt, sample_file])

    genai.delete_file(sample_file.name)

    try:
        text = response.text
        return text.strip() if text.strip() != "" else None
    except AttributeError:
        return None


def organize_files_by_extension(source_folder, destination_folder):
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    files = [
        f
        for f in os.listdir(source_folder)
        if os.path.isfile(os.path.join(source_folder, f))
    ]

    files_by_extension = {}

    trie = Trie()

    for filename in files:
        _, extension = os.path.splitext(filename)
        extension = extension.lower()

        trie.insert(filename)

        if extension in files_by_extension:
            files_by_extension[extension].append(filename)
        else:
            files_by_extension[extension] = [filename]

    for ext, filenames in files_by_extension.items():
        if ext not in [".jpg", ".jpeg", ".png"]:
            ext_folder = os.path.join(destination_folder, ext[1:])
            if not os.path.exists(ext_folder):
                os.makedirs(ext_folder)
            for filename in filenames:
                src_path = os.path.join(source_folder, filename)
                dst_path = os.path.join(ext_folder, filename)
                if os.path.exists(src_path):
                    shutil.move(src_path, dst_path)

    images_folder = os.path.join(destination_folder, "images")
    if not os.path.exists(images_folder):
        os.makedirs(images_folder)

    for ext in [".jpg", ".jpeg", ".png"]:
        if ext in files_by_extension:
            for filename in files_by_extension[ext]:
                image_path = os.path.join(source_folder, filename)
                caption = generate_one_word_caption(image_path, ext)
                if caption:
                    caption_folder = os.path.join(images_folder, caption)
                    if not os.path.exists(caption_folder):
                        os.makedirs(caption_folder)
                    dst_path = os.path.join(caption_folder, filename)
                    if os.path.exists(image_path):
                        shutil.move(image_path, dst_path)
                else:
                    others_folder = os.path.join(images_folder, "others")
                    if not os.path.exists(others_folder):
                        os.makedirs(others_folder)
                    dst_path = os.path.join(others_folder, filename)
                    if os.path.exists(image_path):
                        shutil.move(image_path, dst_path)

    return files_by_extension, trie


def organize_files():
    def thread_organize():
        loading_screen = tk.Toplevel()
        loading_screen.title("Processing")
        loading_screen.geometry("200x100")
        loading_label = tk.Label(loading_screen, text="Processing... Please wait.")
        loading_label.pack()

        global files_by_extension, trie
        files_by_extension, trie = organize_files_by_extension(
            src_var.get(), dest_var.get()
        )

        loading_screen.destroy()

    thread = threading.Thread(target=thread_organize)
    thread.start()


def browse_src():
    selected_folder = filedialog.askdirectory()
    src_var.set(selected_folder)


def search_file():
    selected_item = entry.get()
    full_path = find_file(selected_item, files_by_extension, dest_var.get())
    if full_path:
        messagebox.showinfo("File Path", f"Path of {selected_item}: {full_path}")
    else:
        messagebox.showerror("File Not Found", f"File '{selected_item}' not found.")


def search_autocomplete(event):
    prefix = entry.get()
    if prefix:
        autocomplete_results = trie.search_autocomplete(prefix)
    else:
        autocomplete_results = []
    update_autocomplete(autocomplete_results)


def browse_dest():
    selected_folder = filedialog.askdirectory()
    dest_var.set(selected_folder)


def update_autocomplete(results):
    listbox_autocomplete.delete(0, tk.END)
    for result in results:
        listbox_autocomplete.insert(tk.END, result)
    listbox_autocomplete.bind("<<ListboxSelect>>", on_select_autocomplete)


def on_select_autocomplete(event):
    selected_index = listbox_autocomplete.curselection()
    if selected_index:
        selected_text = listbox_autocomplete.get(selected_index)
        entry.delete(0, tk.END)
        entry.insert(tk.END, selected_text)


def find_file(filename, files_by_extension, destination_folder):
    for ext, filenames in files_by_extension.items():
        if filename in filenames:
            if ext.lower() in {".jpg", ".jpeg", ".png"}:
                # For image files, check if it's categorized into subfolders
                image_folder = os.path.join(destination_folder, "images")
                for subdir in os.listdir(image_folder):
                    subdir_path = os.path.join(image_folder, subdir)
                    if os.path.isdir(subdir_path) and filename in os.listdir(subdir_path):
                        return os.path.join(subdir_path, filename)
                return os.path.join(destination_folder, "images", "others", filename)  # Not found in specific subfolder, return path in 'others' folder
            else:
                return os.path.join(destination_folder, ext[1:], filename)  # Include filename in the path for other file types
    return None


root = tk.Tk()
root.title("File Organizer")

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0)

label_src = ttk.Label(frame, text="Source Path:")
label_src.grid(row=0, column=0, sticky="w")

src_var = tk.StringVar()
entry_src = ttk.Entry(frame, textvariable=src_var, width=40)
entry_src.grid(row=0, column=1, padx=(0, 10))

button_browse_src = ttk.Button(frame, text="Browse", command=browse_src)
button_browse_src.grid(row=0, column=2)

label_dest = ttk.Label(frame, text="Destination Path:")
label_dest.grid(row=1, column=0, sticky="w")

dest_var = tk.StringVar()
entry_dest = ttk.Entry(frame, textvariable=dest_var, width=40)
entry_dest.grid(row=1, column=1, padx=(0, 10))

button_browse_dest = ttk.Button(frame, text="Browse", command=browse_dest)
button_browse_dest.grid(row=1, column=2)

button_organize = ttk.Button(frame, text="Organize Files", command=organize_files)
button_organize.grid(row=2, column=0, columnspan=3, pady=(10, 0))

label_search = ttk.Label(frame, text="Search:")
label_search.grid(row=3, column=0, sticky="w")

autocomplete_var = tk.StringVar()
entry = ttk.Entry(frame, textvariable=autocomplete_var, width=40)
entry.grid(row=3, column=1, padx=(0, 10))

button_search = ttk.Button(frame, text="Search", command=search_file)
button_search.grid(row=3, column=2)

listbox_autocomplete = tk.Listbox(frame, width=40, height=5)
listbox_autocomplete.grid(row=4, column=1, padx=(0, 10), columnspan=2, sticky="ew")

entry.bind("<KeyRelease>", search_autocomplete)

root.mainloop()
