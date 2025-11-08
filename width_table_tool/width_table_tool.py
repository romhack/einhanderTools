import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import json
import struct

# === CONFIGURATION ===
FIELD_SCHEMA = {
    "name": "",
    "x": 0,
    "y": 0,
    "w": 1,
    "h": 1,
    "leftMargin": 0,
    "topMargin": 0,
    "rightMargin": 0,
    "unknown1": 0,
    "trimLeft": 0,
    "trimRight": 0,
    "unknown2": 0,
    "unknown3": 0
}

scale = 2
original_img = Image.open("glyphs.png")

root = tk.Tk()
icon_img = tk.PhotoImage(file="icon.png")
root.iconphoto(True, icon_img)
root.title("Width Table Tool")

rects = []
canvas_ids = []
selected_index = None

frame = tk.Frame(root)
frame.pack()

left_container = tk.Frame(frame)
left_container.grid(row=0, column=0)
zoom_frame = tk.Frame(left_container)
zoom_frame.pack(anchor='w', pady=(0, 5))
canvas_frame = tk.Frame(left_container)
canvas_frame.pack()

hbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
hbar.pack(side=tk.BOTTOM, fill=tk.X)
vbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
vbar.pack(side=tk.RIGHT, fill=tk.Y)

def update_scaled_image():
    global scaled_img, tk_img, img_width, img_height
    scaled_img = original_img.resize((original_img.width * scale, original_img.height * scale), Image.NEAREST)
    img_width, img_height = scaled_img.size
    tk_img = ImageTk.PhotoImage(scaled_img)

update_scaled_image()

canvas = tk.Canvas(canvas_frame, width=original_img.width * 2, height=original_img.height * 2, bg='white', xscrollcommand=hbar.set, yscrollcommand=vbar.set)
canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
hbar.config(command=canvas.xview)
vbar.config(command=canvas.yview)

canvas_img_id = canvas.create_image(0, 0, anchor='nw', image=tk_img)
canvas.image = tk_img
canvas.config(scrollregion=(0, 0, img_width, img_height))

right_panel = tk.Frame(frame)
right_panel.grid(row=0, column=1, padx=(10, 0), sticky='n')

file_ops_frame = tk.Frame(right_panel)
file_ops_frame.pack(anchor='w', pady=(0, 10))

tk.Button(file_ops_frame, text="Load Binary", command=lambda: load_binary_file()).pack(side=tk.LEFT, padx=(0, 5))
tk.Button(file_ops_frame, text="Save Binary", command=lambda: save_binary_file()).pack(side=tk.LEFT, padx=(0, 32))
tk.Button(file_ops_frame, text="Load JSON", command=lambda: load_json_file()).pack(side=tk.LEFT, padx=(0, 5))
tk.Button(file_ops_frame, text="Save JSON", command=lambda: save_json_file()).pack(side=tk.LEFT, padx=(0, 5))



def on_zoom_change(selected_zoom):
    global scale
    old_scale = scale
    new_scale = int(selected_zoom[1:])
    if new_scale != old_scale:
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        center_x = canvas.canvasx(canvas_width / 2)
        center_y = canvas.canvasy(canvas_height / 2)
        x_ratio = center_x / (original_img.width * old_scale)
        y_ratio = center_y / (original_img.height * old_scale)
        scale = new_scale
        update_scaled_image()
        canvas.config(width=original_img.width * 2, height=original_img.height * 2)
        canvas.config(scrollregion=(0, 0, img_width, img_height))
        redraw_rectangles()
        canvas.xview_moveto(max(0, x_ratio - 0.5 * canvas_width / (original_img.width * scale)))
        canvas.yview_moveto(max(0, y_ratio - 0.5 * canvas_height / (original_img.height * scale)))

tk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT, padx=(0, 5))
zoom_var = tk.StringVar(value="x2")
tk.OptionMenu(zoom_frame, zoom_var, "x2", "x4", "x6", "x8", command=on_zoom_change).pack(side=tk.LEFT)

list_frame = tk.Frame(right_panel)
list_frame.pack(anchor='w', pady=(0, 10))
tk.Label(list_frame, text="Glyph Rectangles (JSON):").pack(anchor='w')

listbox_frame = tk.Frame(list_frame)
listbox_frame.pack(fill=tk.BOTH, expand=True)

rect_listbox = tk.Listbox(listbox_frame, width=68, height=25, font=('Courier', 10), activestyle='none')
rect_scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL)
rect_listbox.config(yscrollcommand=rect_scrollbar.set)
rect_scrollbar.config(command=rect_listbox.yview)
rect_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
rect_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

tk.Button(list_frame, text="Delete Selected", command=lambda: delete_selected_glyph()).pack(pady=(5, 0), anchor='w')

def clamp(val, low, high): return max(low, min(val, high))

def format_hex_dict(d): return json.dumps({k: (f"0x{int(v):X}" if isinstance(v, int) else v) for k, v in d.items()}, separators=(',', ':'))

def parse_hex_dict(s): return {k: (int(str(v), 16) if isinstance(FIELD_SCHEMA[k], int) else v) for k, v in json.loads(s).items()}

def get_next_glyph_number():
    max_val = 0x1F
    for r in rects:
        name = r.get("name", "")
        if name.startswith("glyph_"):
            try: max_val = max(max_val, int(name[6:], 16))
            except: continue
    return f"{max_val + 1:X}"

def update_listbox(preserve_scroll=False):
    scroll_position = rect_listbox.yview() if preserve_scroll and rect_listbox.size() > 0 else None
    rect_listbox.delete(0, tk.END)
    for r in rects: rect_listbox.insert(tk.END, format_hex_dict(r))
    if preserve_scroll and scroll_position: rect_listbox.yview_moveto(scroll_position[0])
    elif not preserve_scroll: rect_listbox.see(tk.END)

def redraw_rectangles():
    canvas.delete("all")
    canvas.create_image(0, 0, anchor='nw', image=tk_img)
    canvas.image = tk_img
    canvas_ids.clear()
    canvas.config(scrollregion=(0, 0, img_width, img_height))
    for i, r in enumerate(rects):
        x, y, w, h = [r[k] * scale for k in ("x", "y", "w", "h")]
        color = 'yellow' if i == selected_index else 'red'
        rid = canvas.create_rectangle(x, y, x + w, y + h, outline=color, width=2)
        canvas_ids.append(rid)

def delete_selected_glyph():
    global selected_index
    if selected_index is None or selected_index >= len(rects): return
    name = rects[selected_index].get("name", f"glyph_{selected_index}")
    if messagebox.askyesno("Confirm Delete", f"Delete {name}?"):
        rects.pop(selected_index)
        selected_index = len(rects) - 1 if selected_index >= len(rects) else selected_index
        update_listbox(True)
        redraw_rectangles()
        if selected_index is not None and selected_index < rect_listbox.size(): rect_listbox.select_set(selected_index)

def load_binary_file():
    global rects, selected_index
    f = filedialog.askopenfilename(title="Load Binary", filetypes=[("Binary", "*.bin"), ("All", "*.*")])
    if not f: return
    try:
        with open(f, 'rb') as binf: data = binf.read()
        if len(data) % 12 != 0: raise ValueError("Invalid file size")
        rects = []
        for i in range(0, len(data), 12):
            vals = struct.unpack('BBBBBBBBBBBB', data[i:i+12])
            r = dict(FIELD_SCHEMA)
            r.update({
                "name": f"glyph_{(len(rects)+0x20):X}",
                "x": vals[0],
                "y": vals[1],
                "w": vals[2]+1,
                "h": vals[3]+1,
                "leftMargin": vals[4],
                "topMargin": vals[5],
                "rightMargin": vals[6],
                "unknown1": vals[7],
                "trimLeft": vals[8],
                "trimRight": vals[9],
                "unknown2": vals[10],
                "unknown3": vals[11]
            })
            rects.append(r)
        selected_index = None
        update_listbox(False)
        redraw_rectangles()
        messagebox.showinfo("Success", f"Loaded {len(rects)} glyphs")
    except Exception as e:
        messagebox.showerror("Error", f"{e}")

def save_json_file():
    if not rects: return
    f = filedialog.asksaveasfilename(title="Save JSON", defaultextension=".json", filetypes=[("JSON", "*.json"), ("All", "*.*")])
    if not f: return
    try:
        with open(f, 'w') as outf:
            json.dump([{k: (f"0x{int(v):X}" if isinstance(FIELD_SCHEMA[k], int) else v) for k, v in r.items()} for r in rects], outf, indent=2)
        messagebox.showinfo("Success", f"Saved {len(rects)} glyphs")
    except Exception as e:
        messagebox.showerror("Error", f"{e}")

def load_json_file():
    global rects, selected_index
    f = filedialog.askopenfilename(title="Load JSON", filetypes=[("JSON", "*.json"), ("All", "*.*")])
    if not f: return
    try:
        with open(f, 'r') as inf: data = json.load(inf)
        rects = [{k: (int(str(v), 16) if isinstance(FIELD_SCHEMA[k], int) else v) for k, v in entry.items()} for entry in data]
        selected_index = None
        update_listbox(False)
        redraw_rectangles()
        messagebox.showinfo("Success", f"Loaded {len(rects)} glyphs from JSON")
    except Exception as e:
        messagebox.showerror("Error", f"{e}")

def save_binary_file():
    if not rects: return
    f = filedialog.asksaveasfilename(title="Save Binary", defaultextension=".bin", filetypes=[("Binary", "*.bin"), ("All", "*.*")])
    if not f: return
    try:
        with open(f, 'wb') as outf:
            for r in rects:
                vals = [r.get(k, 0) for k in ["x", "y"]] + [max(0, r.get("w", 1)-1), max(0, r.get("h", 1)-1)]
                vals += [r.get(k, 0) for k in ["leftMargin", "topMargin", "rightMargin", "unknown1", "trimLeft", "trimRight", "unknown2", "unknown3"]]
                outf.write(struct.pack('BBBBBBBBBBBB', *vals))
        messagebox.showinfo("Success", f"Saved {len(rects)} glyphs to binary")
    except Exception as e:
        messagebox.showerror("Error", f"{e}")

def on_list_select(e):
    global selected_index
    try:
        selected_index = rect_listbox.curselection()[0]
        redraw_rectangles()
    except IndexError:
        pass

def open_edit_dialog():
    global selected_index
    if selected_index is None or selected_index >= len(rects): return
    d = tk.Toplevel(root); d.title("Edit JSON")
    t = tk.Text(d, width=80, height=4); t.insert("1.0", format_hex_dict(rects[selected_index])); t.pack(padx=10, pady=10)
    def apply_changes():
        try:
            new_data = parse_hex_dict(t.get("1.0", "end").strip())
            rects[selected_index] = {k: new_data.get(k, FIELD_SCHEMA[k]) for k in FIELD_SCHEMA}
            update_listbox(True); redraw_rectangles(); rect_listbox.select_set(selected_index); d.destroy()
        except Exception as e:
            messagebox.showerror("Invalid JSON", str(e))
    t.bind("<Return>", lambda e: apply_changes())
    tk.Button(d, text="OK", command=apply_changes).pack(pady=5)
    d.transient(root); d.grab_set(); t.focus_set(); root.wait_window(d)

drawing = False
start_x = start_y = None

def on_mouse_down(event):
    global drawing, start_x, start_y
    x = clamp(canvas.canvasx(event.x), 0, img_width - 1)
    y = clamp(canvas.canvasy(event.y), 0, img_height - 1)
    drawing = True
    start_x, start_y = x, y

def on_mouse_move(event):
    x = clamp(canvas.canvasx(event.x), 0, img_width - 1)
    y = clamp(canvas.canvasy(event.y), 0, img_height - 1)
    canvas.delete("temp")
    if drawing: canvas.create_rectangle(start_x, start_y, x, y, outline='red', tag="temp", width=1)

def on_mouse_up(event):
    global drawing, start_x, start_y, selected_index
    x = clamp(canvas.canvasx(event.x), 0, img_width - 1)
    y = clamp(canvas.canvasy(event.y), 0, img_height - 1)
    canvas.delete("temp")
    if drawing and start_x is not None and start_y is not None:
        x0, y0, x1, y1 = min(start_x, x), min(start_y, y), max(start_x, x), max(start_y, y)
        gx, gy = round(x0 / scale), round(y0 / scale)
        gw, gh = round((x1 - x0) / scale), round((y1 - y0) / scale)
        if gw > 0 and gh > 0:
            r = dict(FIELD_SCHEMA)
            r.update({"name": f"glyph_{get_next_glyph_number()}", "x": gx, "y": gy, "w": gw, "h": gh})
            rects.append(r)
            selected_index = len(rects) - 1
        update_listbox(False); redraw_rectangles()
        if selected_index is not None: rect_listbox.select_set(selected_index)
    drawing = False
    start_x = start_y = None

canvas.bind("<ButtonPress-1>", on_mouse_down)
canvas.bind("<B1-Motion>", on_mouse_move)
canvas.bind("<ButtonRelease-1>", on_mouse_up)
rect_listbox.bind("<<ListboxSelect>>", on_list_select)
rect_listbox.bind("<Double-Button-1>", lambda e: open_edit_dialog())

root.mainloop()
