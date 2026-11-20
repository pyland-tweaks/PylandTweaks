"""Interfaz del asistente inicial de PylandTweaks (15 preguntas)."""

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import onboarding_data as data

CREATE_NO_WINDOW = 0x08000000


def _base_path():
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "assets").exists():
            return exe_dir
        return Path(getattr(sys, "_MEIPASS", exe_dir))
    return Path(__file__).resolve().parent


class OnboardingApp:
    TOTAL = 15

    def __init__(self, root, on_open_advanced=None):
        self.root = root
        self.on_open_advanced = on_open_advanced
        self.root.title("PylandTweaks - Asistente inicial")
        self.root.geometry("1120x860")
        self.root.minsize(960, 700)
        self.root.configure(bg=data.BG)
        self._set_icon()

        self.container = tk.Frame(root, bg=data.BG)
        self.container.pack(fill="both", expand=True)

        self.questions = []
        self.answers = {}
        self.index = 0
        self.vars = {}
        self.current_frame = None
        self.progress_anim = 0.0
        self.progress_token = 0
        self.exec_queue = queue.Queue()
        self.busy = False
        self.log_widget = None
        self.progress_canvas = None
        self.progress_fill = None
        self.step_label = None

        loading = tk.Frame(self.container, bg=data.BG)
        loading.pack(fill="both", expand=True)
        tk.Label(loading, text="Preparando el asistente...", bg=data.BG, fg=data.FG,
                 font=(data.FONT_BOLD, 20)).pack(expand=True)
        tk.Label(loading, text="Detectando apps de inicio y aplicaciones instaladas",
                 bg=data.BG, fg=data.MUTED, font=(data.FONT, 11)).pack(pady=(0, 24))
        self.loading = loading
        self.root.after(80, self._prepare)

    def _set_icon(self):
        ico = _base_path() / "assets" / "app.ico"
        if ico.exists():
            try:
                self.root.iconbitmap(str(ico))
            except tk.TclError:
                pass

    def _logo(self):
        path = _base_path() / "assets" / "logo.png"
        if not path.exists():
            return None
        try:
            return tk.PhotoImage(file=str(path))
        except tk.TclError:
            return None

    def _prepare(self):
        detected = data.detect_all()
        self.questions = data.build_questions(detected)
        self.answers = data.default_answers(self.questions)
        self.loading.destroy()
        self._show_selector()
        self.root.focus_force()
        self.root.lift()

    def _show_selector(self):
        frame = tk.Frame(self.container, bg=data.BG)
        frame.pack(fill="both", expand=True)

        logo = self._logo()
        if logo is not None:
            label = tk.Label(frame, image=logo, bg=data.BG)
            label.image = logo
            label.pack(pady=(54, 6))
        tk.Label(frame, text="PylandTweaks", bg=data.BG, fg=data.FG,
                 font=(data.FONT_BOLD, 30)).pack()
        tk.Label(frame, text="Elige cómo quieres optimizar tu Windows 10 / 11",
                 bg=data.BG, fg=data.MUTED, font=(data.FONT, 13)).pack(pady=(6, 34))

        cards = tk.Frame(frame, bg=data.BG)
        cards.pack()

        self._mode_card(cards, "Modo Guiado",
                        "15 preguntas sencillas para dejar el PC listo. Ideal si no sabes qué tocar.",
                        "Recomendado", self._start_guided, data.ACCENT, True)
        self._mode_card(cards, "Modo Avanzado",
                        "Acceso directo a todas las pestañas, ajustes y herramientas técnicas.",
                        "Clásico", self._open_advanced, data.BORDER, False)

        tk.Label(frame, text="Puedes crear un punto de restauración antes de aplicar nada.",
                 bg=data.BG, fg=data.MUTED, font=(data.FONT, 10)).pack(pady=(34, 0))

    def _mode_card(self, parent, title, desc, badge, command, accent, highlighted):
        text = f"{title}\n\n{desc}\n\n{badge}"
        card = tk.Button(parent, text=text, command=command, bg=data.CARD, fg=data.FG,
                         activebackground="#20242E", activeforeground=data.FG,
                         bd=0, relief="flat", highlightthickness=2 if highlighted else 1,
                         highlightbackground=accent, font=(data.FONT_BOLD, 12),
                         wraplength=320, justify="left", padx=24, pady=18,
                         cursor="hand2", width=34, height=9)
        card.grid(row=0, column=1 if highlighted else 0, padx=14, pady=10)
        card.bind("<Enter>", lambda event: card.configure(
            highlightbackground=data.ACCENT, bg="#20242E"))
        card.bind("<Leave>", lambda event: card.configure(
            highlightbackground=accent, bg=data.CARD))

    def _open_advanced(self):
        self.container.destroy()
        if self.on_open_advanced:
            self.on_open_advanced()

    def _start_guided(self):
        for child in list(self.container.winfo_children()):
            child.destroy()
        self._build_shell()
        self._show_step(0, 1)
        self.root.focus_force()
        self.root.lift()

    def _build_shell(self):
        self.header = tk.Frame(self.container, bg=data.BG, height=86)
        self.header.pack(fill="x", padx=40, pady=(18, 0))
        self.header.pack_propagate(False)

        left = tk.Frame(self.header, bg=data.BG)
        left.pack(side="left", fill="y")
        tk.Label(left, text="PylandTweaks", bg=data.BG, fg=data.FG,
                 font=(data.FONT_BOLD, 17)).pack(anchor="w", pady=(8, 0))
        self.step_label = tk.Label(left, text="Pregunta 1 de 15", bg=data.BG,
                                   fg=data.MUTED, font=(data.FONT, 11))
        self.step_label.pack(anchor="w", pady=(2, 0))

        right = tk.Frame(self.header, bg=data.BG)
        right.pack(side="right", fill="y", pady=(18, 0))
        self.progress_canvas = tk.Canvas(right, width=520, height=7, bg=data.CARD,
                                         highlightthickness=0, bd=0)
        self.progress_canvas.pack()
        self.progress_fill = self.progress_canvas.create_rectangle(0, 0, 0, 7,
                                                                    fill=data.ACCENT, outline="")

        self.stage = tk.Frame(self.container, bg=data.BG)
        self.stage.pack(fill="both", expand=True, padx=40, pady=(6, 6))

        self.footer = tk.Frame(self.container, bg=data.BG, height=68)
        self.footer.pack(fill="x", padx=40, pady=(0, 18))
        self.footer.pack_propagate(False)
        self.back_button = tk.Button(self.footer, text="Anterior", command=self._previous,
                                     bg=data.CARD2, fg=data.MUTED, bd=0, highlightthickness=1,
                                     highlightbackground=data.BORDER, activebackground=data.CARD,
                                     activeforeground=data.FG, font=(data.FONT_BOLD, 11),
                                     padx=22, pady=9, cursor="hand2")
        self.back_button.pack(side="left", pady=(12, 0))
        self.next_button = tk.Button(self.footer, text="Siguiente", command=self._next,
                                     bg=data.ACCENT, fg=data.FG, bd=0,
                                     activebackground=data.ACCENT_DARK,
                                     font=(data.FONT_BOLD, 11), padx=26, pady=9,
                                     cursor="hand2")
        self.next_button.pack(side="right", pady=(12, 0))
        tk.Label(self.footer, text="Tus respuestas se pueden cambiar antes de aplicar.",
                 bg=data.BG, fg=data.MUTED, font=(data.FONT, 10)).pack(side="right",
                                                                        padx=(0, 18), pady=(14, 0))

    def _set_progress(self, value):
        self.progress_token += 1
        token = self.progress_token
        start = self.progress_anim
        target = max(0.0, min(1.0, value)) * 520
        self.progress_anim = target
        for step in range(1, 9):
            t = step / 8
            eased = 1 - (1 - t) ** 3
            x = start + (target - start) * eased
            self.root.after(step * 22, lambda x=x, token=token: self._draw_progress(x, token))

    def _draw_progress(self, width, token):
        if token != self.progress_token or self.progress_fill is None:
            return
        try:
            self.progress_canvas.coords(self.progress_fill, 0, 0, int(width), 7)
        except tk.TclError:
            pass

    def _scroll_area(self, parent):
        outer = tk.Frame(parent, bg=data.BG)
        canvas = tk.Canvas(outer, bg=data.BG, highlightthickness=0, bd=0)
        scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=data.BG)
        inner.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        canvas.bind("<MouseWheel>",
                    lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        return outer, inner

    def _show_step(self, index, direction=1):
        self.index = index
        for child in list(self.stage.winfo_children()):
            child.destroy()
        self.vars = {}

        if index >= len(self.questions):
            self.step_label.configure(text="Resumen final")
            self._set_progress(1.0)
            frame, inner = self._scroll_area(self.stage)
            self._build_summary(inner)
            self.back_button.configure(text="Anterior", state="normal")
            self.next_button.configure(text="Aplicar optimizaciones", bg=data.SUCCESS,
                                       activebackground="#0EA472", command=self._apply)
        else:
            question = self.questions[index]
            self.step_label.configure(text=f"Pregunta {index + 1} de {self.TOTAL}")
            self._set_progress((index + 1) / (self.TOTAL + 1))
            frame, inner = self._scroll_area(self.stage)
            self._build_question(inner, question, index)
            self.back_button.configure(text="Anterior" if index else "Volver al inicio",
                                       state="normal")
            self.next_button.configure(text="Siguiente", bg=data.ACCENT,
                                       activebackground=data.ACCENT_DARK, command=self._next)

        frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        for step in range(7):
            t = step / 6
            offset = int(direction * 38 * (1 - t) ** 2)
            self.root.after(step * 26, lambda off=offset, f=frame: self._slide(f, off))

    def _slide(self, frame, offset):
        if frame.winfo_exists():
            frame.place_configure(x=offset)

    def _build_question(self, parent, question, index):
        head = tk.Frame(parent, bg=data.BG)
        head.pack(fill="x", pady=(4, 16))
        tk.Label(head, text=f"{index + 1:02d} / {self.TOTAL}", bg=data.BG, fg=data.ACCENT,
                 font=(data.FONT_BOLD, 12)).pack(anchor="w")
        tk.Label(head, text=question["title"], bg=data.BG, fg=data.FG,
                 font=(data.FONT_BOLD, 24), wraplength=900, justify="left").pack(anchor="w",
                                                                                  pady=(6, 6))
        tk.Label(head, text=question["subtitle"], bg=data.BG, fg=data.MUTED,
                 font=(data.FONT, 12), wraplength=900, justify="left").pack(anchor="w")

        if question["multi"] and len(question["options"]) > 1:
            quick = tk.Frame(parent, bg=data.BG)
            quick.pack(fill="x", pady=(0, 12))
            self._small_button(quick, "Aplicar recomendados", data.ACCENT,
                               lambda: self._quick("recommended"))
            self._small_button(quick, "Seleccionar todo", data.CARD,
                               lambda: self._quick("all"))
            self._small_button(quick, "Desmarcar todo", data.CARD,
                               lambda: self._quick("none"))

        for option in question["options"]:
            self._option_row(parent, option, question)

    def _small_button(self, parent, text, bg, command):
        button = tk.Button(parent, text=text, command=command, bg=bg,
                           fg=data.FG if bg == data.ACCENT else data.MUTED,
                           bd=0, activebackground=data.ACCENT_DARK if bg == data.ACCENT else data.CARD2,
                           activeforeground=data.FG, font=(data.FONT_BOLD, 9),
                           padx=12, pady=5, cursor="hand2")
        button.pack(side="left", padx=(0, 8))
        return button

    def _badge_color(self, badge):
        if "Precaución" in badge:
            return data.WARN
        if badge == "Seguro":
            return data.SUCCESS
        return data.ACCENT

    def _draw_check(self, canvas, checked):
        canvas.delete("all")
        canvas.create_rectangle(1, 1, 17, 17,
                                fill=data.ACCENT if checked else data.CARD2,
                                outline=data.ACCENT if checked else data.BORDER, width=1)
        if checked:
            canvas.create_line(4, 9, 7, 13, 13, 5, fill=data.FG, width=2,
                               smooth=True, splinesteps=2)

    def _bind_tree(self, widget, sequence, callback):
        widget.bind(sequence, callback, add="+")
        for child in widget.winfo_children():
            self._bind_tree(child, sequence, callback)

    def _option_row(self, parent, option, question):
        selected = option["id"] in self.answers.get(question["id"], [])
        var = tk.BooleanVar(value=selected)
        self.vars[option["id"]] = var

        row = tk.Frame(parent, bg=data.CARD, highlightbackground=data.BORDER,
                       highlightthickness=1, cursor="hand2")
        row.pack(fill="x", pady=4)

        check = tk.Canvas(row, width=19, height=19, bg=data.CARD,
                          highlightthickness=0, bd=0)
        check.grid(row=0, column=0, padx=(16, 10), pady=12)
        self._draw_check(check, selected)

        texts = tk.Frame(row, bg=data.CARD)
        texts.grid(row=0, column=1, sticky="w", pady=10)
        tk.Label(texts, text=option["label"], bg=data.CARD, fg=data.FG,
                 font=(data.FONT_BOLD, 12)).pack(anchor="w")
        tk.Label(texts, text=option["desc"], bg=data.CARD, fg=data.MUTED,
                 font=(data.FONT, 10), wraplength=760, justify="left").pack(anchor="w",
                                                                             pady=(3, 0))

        if option["badge"]:
            badge = tk.Label(row, text=option["badge"], bg=self._badge_color(option["badge"]),
                             fg=data.FG, font=(data.FONT_BOLD, 9), padx=10, pady=2)
            badge.grid(row=0, column=2, padx=(10, 16), pady=12)

        def reflect(*args):
            self._draw_check(check, var.get())
            row.configure(highlightbackground=data.ACCENT if var.get() else data.BORDER)

        def toggle(event=None):
            new_value = not var.get()
            if new_value and not question["multi"]:
                for other_id, other_var in self.vars.items():
                    if other_id != option["id"]:
                        other_var.set(False)
            var.set(new_value)

        var.trace_add("write", reflect)
        self._bind_tree(row, "<Button-1>", lambda event: toggle())
        self._bind_tree(row, "<Enter>",
                        lambda event: row.configure(highlightbackground=data.ACCENT))
        self._bind_tree(row, "<Leave>",
                        lambda event: row.configure(highlightbackground=data.BORDER))

    def _quick(self, mode):
        question = self.questions[self.index]
        for option in question["options"]:
            var = self.vars.get(option["id"])
            if var is None:
                continue
            if mode == "recommended":
                var.set(bool(option["recommended"]))
            elif mode == "all":
                var.set(True)
            else:
                var.set(False)
            if not question["multi"] and mode == "all":
                break

    def _collect(self):
        if self.index < len(self.questions) and self.vars:
            question = self.questions[self.index]
            self.answers[question["id"]] = [option_id for option_id, var in self.vars.items()
                                            if var.get()]

    def _next(self):
        self._collect()
        self._show_step(self.index + 1, 1)

    def _previous(self):
        self._collect()
        if self.index == 0:
            self._show_selector_screen()
        else:
            self._show_step(self.index - 1, -1)

    def _show_selector_screen(self):
        for child in list(self.container.winfo_children()):
            child.destroy()
        self.header = None
        self.stage = None
        self.footer = None
        self.progress_canvas = None
        self.progress_fill = None
        self.step_label = None
        self._show_selector()

    def _build_summary(self, parent):
        rows = data.summary_rows(self.questions, self.answers)
        steps = data.build_plan(self.questions, self.answers)
        commands = data.count_commands(steps)

        head = tk.Frame(parent, bg=data.BG)
        head.pack(fill="x", pady=(4, 18))
        tk.Label(head, text="Resumen de tus decisiones", bg=data.BG, fg=data.FG,
                 font=(data.FONT_BOLD, 24)).pack(anchor="w")
        tk.Label(head, text=f"{len(steps)} ajustes · {commands} comandos · "
                            "puedes volver a cualquier pregunta con «Editar».",
                 bg=data.BG, fg=data.MUTED, font=(data.FONT, 11)).pack(anchor="w", pady=(6, 0))

        for index, title, chosen in rows:
            row = tk.Frame(parent, bg=data.CARD, highlightbackground=data.BORDER,
                           highlightthickness=1)
            row.pack(fill="x", pady=3)
            left = tk.Frame(row, bg=data.CARD)
            left.pack(side="left", fill="x", expand=True, padx=16, pady=10)
            tk.Label(left, text=f"{index + 1:02d}. {title}", bg=data.CARD, fg=data.FG,
                     font=(data.FONT_BOLD, 11)).pack(anchor="w")
            tk.Label(left, text=chosen, bg=data.CARD, fg=data.MUTED,
                     font=(data.FONT, 10), wraplength=820, justify="left").pack(anchor="w",
                                                                                  pady=(3, 0))
            edit = tk.Button(row, text="Editar", command=lambda i=index: self._show_step(i, -1),
                             bg=data.CARD2, fg=data.ACCENT, bd=0, font=(data.FONT_BOLD, 10),
                             padx=14, pady=6, cursor="hand2")
            edit.pack(side="right", padx=14)

    def _apply(self):
        if self.busy:
            return
        try:
            plan = data.build_plan(self.questions, self.answers)
            self.cmd_total = max(1, data.count_commands(plan))
            self.cmd_done = 0
            self.busy = True

            for child in list(self.stage.winfo_children()):
                child.destroy()
            self.step_label.configure(text="Aplicando optimizaciones")
            self._set_progress(0.0)
            self.back_button.configure(state="disabled")
            self.next_button.configure(state="disabled")

            frame = tk.Frame(self.stage, bg=data.BG)
            frame.pack(fill="both", expand=True)
            head = tk.Frame(frame, bg=data.BG)
            head.pack(fill="x", pady=(4, 12))
            tk.Label(head, text="Aplicando tus optimizaciones", bg=data.BG, fg=data.FG,
                     font=(data.FONT_BOLD, 22)).pack(anchor="w", pady=(0, 4))
            self.status_label = tk.Label(head, text="Preparando tareas...", bg=data.BG,
                                         fg=data.MUTED, font=(data.FONT, 11))
            self.status_label.pack(anchor="w")

            content = tk.Frame(frame, bg=data.BG)
            content.pack(fill="both", expand=True)

            left = tk.Frame(content, bg=data.BG, width=300)
            left.pack(side="left", fill="y", padx=(0, 26))
            self.ring = tk.Canvas(left, width=260, height=260, bg=data.BG,
                                  highlightthickness=0, bd=0)
            self.ring.pack(pady=(10, 0))
            self.ring.create_arc(22, 22, 238, 238, start=90, extent=359.9,
                                 style="arc", outline=data.CARD, width=14)
            self.ring_arc = self.ring.create_arc(22, 22, 238, 238, start=90, extent=0,
                                                 style="arc", outline=data.ACCENT, width=14)
            self.ring_text = self.ring.create_text(130, 118, text=f"0/{self.cmd_total}",
                                                   font=(data.FONT_BOLD, 26), fill=data.FG)
            self.ring_sub = self.ring.create_text(130, 154, text="comandos",
                                                  font=(data.FONT, 11), fill=data.MUTED)
            tk.Label(left, text="Círculo de progreso", bg=data.BG, fg=data.MUTED,
                     font=(data.FONT, 10)).pack(pady=(2, 0))

            right = tk.Frame(content, bg=data.BG)
            right.pack(side="left", fill="both", expand=True)
            tk.Label(right, text="Registro en vivo", bg=data.BG, fg=data.FG,
                     font=(data.FONT_BOLD, 12)).pack(anchor="w", pady=(0, 8))
            box = tk.Frame(right, bg=data.CARD2, highlightbackground=data.BORDER,
                           highlightthickness=1)
            box.pack(fill="both", expand=True)
            self.log_widget = tk.Text(box, bg=data.CARD2, fg="#B8C4D9", bd=0,
                                      font=("Consolas", 9), wrap="none", padx=14, pady=10,
                                      insertbackground=data.FG)
            self.log_widget.pack(side="left", fill="both", expand=True)
            scroll = ttk.Scrollbar(box, orient="vertical", command=self.log_widget.yview)
            scroll.pack(side="right", fill="y")
            self.log_widget.configure(yscrollcommand=scroll.set, state="disabled")

            self.exec_buttons = tk.Frame(frame, bg=data.BG)
            self.exec_buttons.pack(fill="x", pady=(12, 0))

            threading.Thread(target=self._run_plan, args=(plan,), daemon=True).start()
            self.root.after(60, self._poll_exec)
        except Exception as exc:
            self.busy = False
            messagebox.showerror("Error", f"No se pudo iniciar la optimización: {exc}")

    def _run_plan(self, plan):
        total = sum(len(commands) for _, commands in plan)
        done = 0
        try:
            for index, (label, commands) in enumerate(plan, 1):
                self.exec_queue.put(("step", index, label, len(plan)))
                for command in commands:
                    self.exec_queue.put(("log", f"> {command}"))
                    try:
                        result = subprocess.run(
                            command, shell=True, cwd=str(_base_path()),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            creationflags=CREATE_NO_WINDOW,
                        )
                        output = result.stdout.decode("mbcs", errors="replace").strip()
                        for line in output.splitlines():
                            self.exec_queue.put(("log", line))
                    except Exception as exc:
                        self.exec_queue.put(("log", f"ERROR: {exc}"))
                    done += 1
                    self.exec_queue.put(("cmd", done, total))
        except Exception as exc:
            self.exec_queue.put(("log", f"ERROR: {exc}"))
        finally:
            self.exec_queue.put(("done",))

    def _poll_exec(self):
        try:
            while True:
                event = self.exec_queue.get_nowait()
                if event[0] == "log":
                    self._append_log(event[1])
                elif event[0] == "step":
                    _, index, label, count = event
                    self.status_label.configure(text=f"Paso {index}/{count}: {label}")
                elif event[0] == "cmd":
                    _, done, total = event
                    self.cmd_done = done
                    self.cmd_total = max(1, total)
                    self._set_ring(done, total)
                    self._set_progress(min(1.0, done / max(1, total)))
                elif event[0] == "done":
                    self._finish_exec(self.cmd_total)
                    return
        except queue.Empty:
            pass
        self.root.after(60, self._poll_exec)

    def _set_ring(self, done, total):
        if not getattr(self, "ring", None) or not self.ring.winfo_exists():
            return
        total = max(1, total)
        fraction = min(1.0, done / total)
        self.ring.itemconfigure(self.ring_arc, extent=360 * fraction,
                                outline=data.SUCCESS if done >= total else data.ACCENT)
        self.ring.itemconfigure(self.ring_text, text=f"{done}/{total}")

    def _append_log(self, text):
        self.log_widget.configure(state="normal")
        self.log_widget.insert("end", text + "\n")
        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

    def _finish_exec(self, total):
        self._set_progress(1.0)
        self._set_ring(total, total)
        self.ring.itemconfigure(self.ring_text, text="")
        self.ring.itemconfigure(self.ring_sub, text="¡Listo!",
                                font=(data.FONT_BOLD, 16), fill=data.SUCCESS)
        self.ring.coords(self.ring_sub, 130, 205)
        for step in range(1, 9):
            self.root.after(step * 20, lambda step=step: self._draw_ring_check(step / 8))
        self.step_label.configure(text="Optimización completada")
        self.status_label.configure(text=f"Completado · {total} comandos ejecutados")
        tk.Button(self.exec_buttons, text="Abrir modo avanzado", command=self._open_advanced,
                  bg=data.ACCENT, fg=data.FG, bd=0, font=(data.FONT_BOLD, 11),
                  padx=20, pady=10, cursor="hand2").pack(side="left", padx=8)
        tk.Button(self.exec_buttons, text="Reiniciar ahora", command=self._restart,
                  bg=data.SUCCESS, fg=data.FG, bd=0, font=(data.FONT_BOLD, 11),
                  padx=20, pady=10, cursor="hand2").pack(side="left", padx=8)
        self.busy = False

    def _draw_ring_check(self, t):
        if not getattr(self, "ring", None) or not self.ring.winfo_exists():
            return
        self.ring.delete("check")
        first = min(1.0, t * 2)
        self.ring.create_line(92, 130, 92 + 24 * first, 130 + 22 * first,
                              fill=data.SUCCESS, width=5, tag="check")
        if t > 0.5:
            second = min(1.0, (t - 0.5) * 2)
            self.ring.create_line(116, 152, 116 + 52 * second, 152 - 58 * second,
                                  fill=data.SUCCESS, width=5, tag="check")

    def _restart(self):
        if not messagebox.askyesno(
                "Reiniciar equipo",
                "Se reiniciará el equipo en 15 segundos. Guarda tu trabajo antes de continuar.\n\n"
                "¿Reiniciar ahora?"):
            return
        try:
            subprocess.Popen(
                'shutdown /r /t 15 /c "Reiniciando para aplicar las optimizaciones"',
                shell=True, creationflags=CREATE_NO_WINDOW)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo programar el reinicio: {exc}")


def run(root, on_open_advanced=None):
    return OnboardingApp(root, on_open_advanced=on_open_advanced)
