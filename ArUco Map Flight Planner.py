import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle, Circle, Ellipse
import re
import json
import numpy as np

class ArucoMapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Планировщик полетов ArUco")
        self.markers = []
        self.marker_positions = []
        self.flight_plan = []
        self.obstacles = []
        self.selected_marker = None
        self.highlighted_patch = None
        self.current_mode = "обычный"
        self.selected_obstacle = None
        self.dragging = False
        self.resize_handle = None
        self.obstacle_handles = {}
        self.create_widgets()
        self.setup_plot()

    def create_widgets(self):
        control_frame = ttk.Frame(self.root)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        self.load_map_btn = ttk.Button(control_frame, text="Загрузить карту", command=self.load_map)
        self.load_map_btn.pack(pady=5)
        self.changer_map_btn = ttk.Button(control_frame, text="Редактор карты", command=self.open_editor)
        self.changer_map_btn.pack(pady=5)
        ttk.Label(control_frame, text="Тип препятствия:").pack(pady=5)
        self.obstacle_type = ttk.Combobox(control_frame, values=["куб", "арка", "флаг"])
        self.obstacle_type.current(0)
        self.obstacle_type.pack(pady=5)
        self.obstacle_btn = ttk.Button(control_frame, text="Добавить препятствие", command=self.toggle_obstacle_mode)
        self.obstacle_btn.pack(pady=5)
        ttk.Label(control_frame, text="Высота (z):").pack(pady=5)
        self.z_entry = ttk.Entry(control_frame)
        self.z_entry.pack(pady=5)
        self.add_point_btn = ttk.Button(control_frame, text="Добавить точку", command=self.add_waypoint)
        self.add_point_btn.pack(pady=5)
        self.insert_before_btn = ttk.Button(control_frame, text="Вставить перед", command=lambda: self.insert_point("перед"))
        self.insert_before_btn.pack(pady=2)
        self.insert_after_btn = ttk.Button(control_frame, text="Вставить после", command=lambda: self.insert_point("после"))
        self.insert_after_btn.pack(pady=2)
        self.remove_point_btn = ttk.Button(control_frame, text="Удалить выбранное", command=self.remove_point)
        self.remove_point_btn.pack(pady=5)
        self.clear_btn = ttk.Button(control_frame, text="Очистить все", command=self.clear_points)
        self.clear_btn.pack(pady=5)
        self.download_btn = ttk.Button(control_frame, text="Сохранить план", command=self.save_plan)
        self.download_btn.pack(pady=5)
        self.upload_plan_btn = ttk.Button(control_frame, text="Загрузить план", command=self.load_plan)
        self.upload_plan_btn.pack(pady=5)
        self.save_project_btn = ttk.Button(control_frame, text="Сохранить проект", command=self.save_project)
        self.save_project_btn.pack(pady=5)
        self.load_project_btn = ttk.Button(control_frame, text="Загрузить проект", command=self.load_project)
        self.load_project_btn.pack(pady=5)
        self.flight_plan_list = tk.Listbox(control_frame, width=30)
        self.flight_plan_list.pack(pady=5, fill=tk.BOTH, expand=True)

    def setup_plot(self):
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect("button_press_event", self.on_click)
        self.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.canvas.mpl_connect("button_release_event", self.on_release)
        self.canvas.mpl_connect("key_press_event", self.on_key_press)
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_title("Карта ArUco")
        self.ax.grid(True)
        self.ax.set_aspect("equal")

    def toggle_obstacle_mode(self):
        if self.current_mode == "добавление":
            self.current_mode = "обычный"
            self.obstacle_btn.config(text="Добавить препятствие")
        else:
            self.current_mode = "добавление"
            self.obstacle_btn.config(text="Выйти из режима")
        self.selected_obstacle = None
        self.draw_obstacles()

    def load_map(self):
        file_path = filedialog.askopenfilename(filetypes=[("Текстовые файлы", "*.txt")])
        if not file_path:
            return
        self.markers = []
        self.marker_positions = []
        self.clear_plot()
        errors = []
        seen_ids = set()
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = re.split(r"\s+", line)
                    if len(parts) != 8:
                        errors.append(f"Строка {line_num}: Некорректное количество элементов")
                        continue
                    try:
                        marker = {
                            "id": int(parts[0]),
                            "length": float(parts[1]),
                            "x": float(parts[2]),
                            "y": float(parts[3]),
                            "z": float(parts[4]),
                            "rot_z": float(parts[5]),
                            "rot_y": float(parts[6]),
                            "rot_x": float(parts[7]),
                        }
                    except ValueError:
                        errors.append(f"Строка {line_num}: Ошибка формата данных")
                        continue
                    if marker["id"] in seen_ids:
                        errors.append(f"Строка {line_num}: Повторяющийся ID")
                        continue
                    seen_ids.add(marker["id"])
                    if marker["length"] <= 0:
                        errors.append(f"Строка {line_num}: Недопустимая длина маркера")
                    self.markers.append(marker)
                    self.marker_positions.append((marker["x"], marker["y"]))
            if errors:
                raise ValueError("\n".join(errors[:5]))
            self.draw_markers()
            self.draw_obstacles()
            self.canvas.draw()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки карты:\n{str(e)}")
            self.markers = []
            self.marker_positions = []
        finally:
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw()

    def draw_markers(self):
        for marker in self.markers:
            rect = Rectangle(
                (marker["x"] - marker["length"] / 2, marker["y"] - marker["length"] / 2),
                marker["length"],
                marker["length"],
                edgecolor="blue",
                facecolor="none",
            )
            self.ax.add_patch(rect)
            self.ax.text(
                marker["x"],
                marker["y"],
                str(marker["id"]),
                ha="center",
                va="center",
                color="blue",
                fontsize=8,
            )

    def draw_obstacles(self):
        for patch in self.ax.patches + self.ax.collections:
            if hasattr(patch, "is_obstacle") or hasattr(patch, "is_handle"):
                patch.remove()
        self.obstacle_handles.clear()
        for idx, obstacle in enumerate(self.obstacles):
            x, y = obstacle["position"]
            color = "yellow" if idx == self.selected_obstacle else "gray"
            handles = []
            if obstacle["type"] == "куб":
                size = obstacle.get("size", 0.6)
                patch = Rectangle(
                    (x - size / 2, y - size / 2),
                    size,
                    size,
                    facecolor=color,
                    edgecolor="black",
                    alpha=0.7,
                )
                if idx == self.selected_obstacle:
                    handles.append(Circle((x + size / 2, y + size / 2), 0.1, facecolor="red"))
                    handles.append(Circle((x - size / 2, y - size / 2), 0.1, facecolor="red"))
            elif obstacle["type"] == "арка":
                length = obstacle.get("length", 1.0)
                thickness = obstacle.get("thickness", 0.2)
                patch = Rectangle(
                    (x - length / 2, y - thickness / 2),
                    length,
                    thickness,
                    facecolor=color,
                    alpha=0.7,
                    edgecolor="black",
                )
                if idx == self.selected_obstacle:
                    handles.append(Circle((x + length / 2, y), 0.1, facecolor="red"))
                    handles.append(Circle((x, y + thickness / 2), 0.1, facecolor="red"))
            elif obstacle["type"] == "флаг":
                radius = obstacle.get("radius", 0.25)
                patch = Circle((x, y), radius, facecolor=color, alpha=0.7, edgecolor="black")
                if idx == self.selected_obstacle:
                    handles.append(Circle((x + radius, y), 0.1, facecolor="red"))
            patch.is_obstacle = True
            patch.obstacle_idx = idx
            self.ax.add_patch(patch)
            if idx == self.selected_obstacle:
                for handle in handles:
                    handle.is_handle = True
                    self.ax.add_patch(handle)
                self.obstacle_handles[idx] = handles
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

    def on_click(self, event):
        if not event.inaxes:
            self.selected_obstacle = None
            self.draw_obstacles()
            return
        if self.current_mode == "добавление":
            x, y = event.xdata, event.ydata
            obstacle_type = self.obstacle_type.get()
            new_obstacle = {"type": obstacle_type, "position": (x, y)}
            if obstacle_type == "куб":
                new_obstacle["size"] = 0.6
            elif obstacle_type == "арка":
                new_obstacle["length"] = 1.0
                new_obstacle["thickness"] = 0.2
            elif obstacle_type == "флаг":
                new_obstacle["radius"] = 0.25
            self.obstacles.append(new_obstacle)
            self.draw_obstacles()
            return
        for patch in reversed(self.ax.patches):
            if hasattr(patch, "contains") and patch.contains(event)[0]:
                if hasattr(patch, "obstacle_idx"):
                    self.selected_obstacle = patch.obstacle_idx
                    self.current_mode = "редактирование"
                    self.draw_obstacles()
                    for idx, handles in self.obstacle_handles.items():
                        for handle_idx, handle in enumerate(handles):
                            if handle.contains(event)[0]:
                                self.resize_handle = (idx, handle_idx)
                                self.dragging = True
                                return
                    self.dragging = True
                    return
        if self.current_mode == "обычный":
            x_click, y_click = event.xdata, event.ydata
            min_dist = float("inf")
            closest = None
            for x, y in self.marker_positions:
                dist = ((x - x_click) ** 2 + (y - y_click) ** 2) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    closest = (x, y)
            if min_dist <= 0.11:
                self.selected_marker = closest
                self.highlight_marker(closest)
        if not any(patch.contains(event)[0] for patch in self.ax.patches):
            self.selected_obstacle = None
            self.current_mode = "обычный"
            self.draw_obstacles()

    def on_motion(self, event):
        if not self.dragging or not event.inaxes:
            return
        try:
            x, y = event.xdata, event.ydata
            obstacle = self.obstacles[self.selected_obstacle]
            original_x, original_y = obstacle["position"]
            if self.resize_handle is not None:
                idx, handle_idx = self.resize_handle
                if obstacle["type"] == "куб":
                    if handle_idx == 0:
                        new_size = max(0.2, (x - (original_x - obstacle["size"] / 2)))
                        obstacle["size"] = new_size
                    else:
                        new_size = max(0.2, ((original_x + obstacle["size"] / 2) - x))
                        obstacle["size"] = new_size
                        obstacle["position"] = (x + new_size / 2, y + new_size / 2)
                elif obstacle["type"] == "арка":
                    if handle_idx == 0:
                        new_length = max(0.3, x - (original_x - obstacle["length"] / 2))
                        obstacle["length"] = new_length
                    elif handle_idx == 1:
                        new_thickness = max(0.1, y - (original_y - obstacle["thickness"] / 2))
                        obstacle["thickness"] = new_thickness
                elif obstacle["type"] == "флаг":
                    dx = x - original_x
                    dy = y - original_y
                    new_radius = max(0.1, (dx**2 + dy**2) ** 0.5)
                    obstacle["radius"] = new_radius
            else:
                if obstacle["type"] in ["флаг", "куб"]:
                    obstacle["position"] = (x, y)
                elif obstacle["type"] == "арка":
                    obstacle["position"] = (x, y)
            self.draw_obstacles()
        except Exception as e:
            print(f"Ошибка при обработке перемещения: {str(e)}")
            self.dragging = False
            self.resize_handle = None

    def on_release(self, event):
        self.dragging = False
        self.resize_handle = None

    def highlight_marker(self, position):
        self.clear_highlights()
        for marker in self.markers:
            if (marker["x"], marker["y"]) == position:
                for patch in self.ax.patches:
                    if isinstance(patch, Rectangle) and patch.get_xy() == (
                        marker["x"] - marker["length"] / 2,
                        marker["y"] - marker["length"] / 2,
                    ):
                        patch.set_edgecolor("red")
                        self.highlighted_patch = patch
                        break
        self.canvas.draw()

    def clear_highlights(self):
        if self.highlighted_patch:
            self.highlighted_patch.set_edgecolor("blue")
            self.highlighted_patch = None
            self.canvas.draw()

    def add_waypoint(self):
        if not self.selected_marker:
            messagebox.showwarning("Внимание", "Выберите маркер на карте")
            return
        try:
            z = abs(float(self.z_entry.get()))
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректное значение высоты")
            return
        x, y = self.selected_marker
        self.flight_plan.append((x, y, z))
        self.update_plan_list()
        self.plot_path()
        self.clear_highlights()

    def insert_point(self, position):
        selected = self.flight_plan_list.curselection()
        if not selected or not self.selected_marker:
            return
        try:
            z = float(self.z_entry.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректное значение высоты")
            return
        idx = selected[0]
        if position == "после":
            idx += 1
        x, y = self.selected_marker
        self.flight_plan.insert(idx, (x, y, z))
        self.update_plan_list()
        self.plot_path()

    def update_plan_list(self):
        self.flight_plan_list.delete(0, tk.END)
        for point in self.flight_plan:
            self.flight_plan_list.insert(tk.END, f"({point[0]:.2f}, {point[1]:.2f}, {point[2]:.2f})")

    def plot_path(self):
        if hasattr(self, "path_line"):
            self.path_line.remove()
        if len(self.flight_plan) >= 2:
            x = [p[0] for p in self.flight_plan]
            y = [p[1] for p in self.flight_plan]
            (self.path_line,) = self.ax.plot(x, y, "r-", marker="o", markersize=5)
        elif len(self.flight_plan) == 1:
            x, y, _ = self.flight_plan[0]
            (self.path_line,) = self.ax.plot([x], [y], "ro", markersize=5)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

    def remove_point(self):
        selected = self.flight_plan_list.curselection()
        if selected:
            self.flight_plan.pop(selected[0])
            self.update_plan_list()
            self.plot_path()

    def clear_points(self):
        self.flight_plan = []
        self.update_plan_list()
        self.plot_path()

    def save_plan(self):
        if not self.flight_plan:
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Текстовые файлы", "*.txt")])
        if not file_path:
            return
        with open(file_path, "w") as f:
            points = [f"({x:.2f},{y:.2f},{z:.2f})" for x, y, z in self.flight_plan]
            f.write(f"[{','.join(points)}]")

    def load_plan(self):
        file_path = filedialog.askopenfilename(filetypes=[("Текстовые файлы", "*.txt")])
        if not file_path:
            return
        try:
            with open(file_path, "r") as f:
                content = f.read()
            pattern = r"\(([\d.]+),([\d.]+),([\d.]+)\)"
            matches = re.findall(pattern, content)
            if not matches:
                raise ValueError("Некорректный формат файла")
            new_plan = []
            for match in matches:
                x, y, z = map(float, match)
                if (x, y) not in self.marker_positions:
                    raise ValueError(f"Маркер не найден: ({x:.2f}, {y:.2f})")
                new_plan.append((x, y, z))
            self.flight_plan = new_plan
            self.update_plan_list()
            self.plot_path()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def clear_plot(self):
        self.ax.clear()
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_title("Карта ArUco")
        self.ax.grid(True)
        self.ax.set_aspect("equal")
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

    def on_key_press(self, event):
        if event.key.lower() in ["delete", "backspace"]:
            self.delete_selected_obstacle()
        elif event.key == "escape":
            self.selected_obstacle = None
            self.draw_obstacles()

    def delete_selected_obstacle(self):
        if self.selected_obstacle is not None:
            try:
                if 0 <= self.selected_obstacle < len(self.obstacles):
                    del self.obstacles[self.selected_obstacle]
                    self.selected_obstacle = None
                    self.draw_obstacles()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить препятствие: {str(e)}")

    def save_project(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".aproject", filetypes=[("Проект ArUco", "*.aproject")])
        if not file_path:
            return
        project_data = {
            "metadata": {"version": "1.0", "type": "aruco_project"},
            "markers": self.markers,
            "obstacles": self.obstacles,
            "flight_plan": self.flight_plan,
        }
        try:
            with open(file_path, "w") as f:
                json.dump(project_data, f, indent=2)
            messagebox.showinfo("Успех", "Проект успешно сохранен")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка сохранения: {str(e)}")

    def load_project(self):
        file_path = filedialog.askopenfilename(filetypes=[("Проект ArUco", "*.aproject")])
        if not file_path:
            return
        try:
            with open(file_path, "r") as f:
                project_data = json.load(f)
            if project_data.get("metadata", {}).get("type") != "aruco_project":
                raise ValueError("Неверный формат файла проекта")
            self.markers = []
            self.obstacles = []
            self.flight_plan = []
            self.clear_plot()
            self.markers = project_data["markers"]
            self.marker_positions = [(m["x"], m["y"]) for m in self.markers]
            self.obstacles = project_data["obstacles"]
            self.flight_plan = [tuple(point) for point in project_data["flight_plan"]]
            self.draw_markers()
            self.draw_obstacles()
            self.update_plan_list()
            self.plot_path()
            messagebox.showinfo("Успех", "Проект успешно загружен")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки: {str(e)}")
            self.markers = []
            self.obstacles = []
            self.flight_plan = []
            self.clear_plot()

    def open_editor(self):
        self.editor_window = tk.Toplevel(self.root)
        self.editor_window.title("Редактор карты")
        self.editor_window.geometry("800x600")
        self.editing_markers = [m.copy() for m in self.markers]
        self.create_editor_widgets()
        self.load_editor_table()
        self.editor_window.protocol("WM_DELETE_WINDOW", self.close_editor)

    def create_editor_widgets(self):
        self.marker_table = ttk.Treeview(self.editor_window, columns=("ID", "X", "Y", "Size"), show="headings")
        self.marker_table.heading("ID", text="ID")
        self.marker_table.heading("X", text="X")
        self.marker_table.heading("Y", text="Y")
        self.marker_table.heading("Size", text="Размер")
        self.marker_table.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        btn_frame = ttk.Frame(self.editor_window)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Добавить", command=self.add_marker_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_marker).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Экспорт", command=self.export_map).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=self.close_editor).pack(side=tk.LEFT, padx=5)
        self.marker_table.bind("<Double-1>", self.edit_marker)

    def load_editor_table(self):
        for item in self.marker_table.get_children():
            self.marker_table.delete(item)
        for marker in self.editing_markers:
            self.marker_table.insert("", tk.END, values=(marker["id"], f"{marker['x']:.2f}", f"{marker['y']:.2f}", f"{marker['length']:.2f}"))

    def add_marker_dialog(self):
        dialog = tk.Toplevel(self.editor_window)
        dialog.title("Новый маркер")
        entries = {}
        fields = [("ID", "int"), ("X", "float"), ("Y", "float"), ("Size", "float")]
        for i, (label, dtype) in enumerate(fields):
            ttk.Label(dialog, text=label).grid(row=i, column=0, padx=5, pady=2)
            entries[label] = ttk.Entry(dialog)
            entries[label].grid(row=i, column=1, padx=5, pady=2)
        def save_marker():
            try:
                new_marker = {
                    "id": int(entries["ID"].get()),
                    "x": float(entries["X"].get()),
                    "y": float(entries["Y"].get()),
                    "length": float(entries["Size"].get()),
                    "z": 0.0,
                    "rot_z": 0.0,
                    "rot_y": 0.0,
                    "rot_x": 0.0,
                }
                self.editing_markers.append(new_marker)
                self.load_editor_table()
                self.update_main_display()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Ошибка", "Некорректные данные")
        ttk.Button(dialog, text="Сохранить", command=save_marker).grid(row=4, columnspan=2, pady=10)

    def edit_marker(self, event):
        selected = self.marker_table.selection()
        if not selected:
            return
        index = self.marker_table.index(selected[0])
        marker = self.editing_markers[index]
        dialog = tk.Toplevel(self.editor_window)
        dialog.title("Редактирование маркера")
        entries = {}
        fields = [("ID", "int", marker["id"]), ("X", "float", marker["x"]), ("Y", "float", marker["y"]), ("Size", "float", marker["length"])]
        for i, (label, dtype, value) in enumerate(fields):
            ttk.Label(dialog, text=label).grid(row=i, column=0, padx=5, pady=2)
            entries[label] = ttk.Entry(dialog)
            entries[label].insert(0, str(value))
            entries[label].grid(row=i, column=1, padx=5, pady=2)
        def save_changes():
            try:
                self.editing_markers[index] = {
                    "id": int(entries["ID"].get()),
                    "x": float(entries["X"].get()),
                    "y": float(entries["Y"].get()),
                    "length": float(entries["Size"].get()),
                    "z": marker["z"],
                    "rot_z": marker["rot_z"],
                    "rot_y": marker["rot_y"],
                    "rot_x": marker["rot_x"],
                }
                self.load_editor_table()
                self.update_main_display()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Ошибка", "Некорректные данные")
        ttk.Button(dialog, text="Сохранить", command=save_changes).grid(row=4, columnspan=2, pady=10)

    def delete_marker(self):
        selected = self.marker_table.selection()
        if selected:
            index = self.marker_table.index(selected[0])
            del self.editing_markers[index]
            self.load_editor_table()
            self.update_main_display()

    def close_editor(self):
        self.markers = [m.copy() for m in self.editing_markers]
        self.update_main_display()
        self.editor_window.destroy()

    def export_map(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            try:
                with open(file_path, "w") as f:
                    f.write("# id\tlength\tx\ty\tz\trot_z\trot_y\trot_x\n")
                    for marker in self.editing_markers:
                        line = (f"{marker['id']}\t{marker['length']}\t"
                                f"{marker['x']}\t{marker['y']}\t{marker['z']}\t"
                                f"{marker['rot_z']}\t{marker['rot_y']}\t{marker['rot_x']}\n")
                        f.write(line)
                messagebox.showinfo("Успех", "Карта успешно экспортирована")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка экспорта: {str(e)}")

    def update_main_display(self):
        self.marker_positions = [(m["x"], m["y"]) for m in self.markers]
        self.ax.clear()
        self.draw_markers()
        self.draw_obstacles()
        self.plot_path()
        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_title("Карта ArUco")
        self.ax.grid(True)
        self.ax.set_aspect("equal")
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = ArucoMapApp(root)
    root.mainloop()