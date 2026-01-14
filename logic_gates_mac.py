import tkinter as tk
from itertools import product
import json
from tkinter import filedialog


BG = "#1a1a1a"
LEFT_BG = "#111111"
RIGHT_BG = "#111111"
ACCENT = "#c996ff"
GRID = "#333333"

NODE_W = 120
NODE_H = 60
PORT_R = 8


def AND(a, b): return a & b
def OR(a, b): return a | b
def XOR(a, b): return a ^ b
def NOT(a, b=0): return 1 - a
def NAND(a, b): return 1 - (a & b)
def NOR(a, b): return 1 - (a | b)
def XNOR(a, b): return 1 - (a ^ b)

GATES = {
    "AND": AND, "OR": OR, "XOR": XOR,
    "NAND": NAND, "NOR": NOR, "XNOR": XNOR,
    "NOT": NOT
}

GATE_LABELS = {
    "AND": "AND", "OR": "OR", "XOR": "XOR",
    "NOT": "NOT", "NAND": "NAND", "NOR": "NOR",
    "XNOR": "XNOR", "IN": "INPUT", "OUT": "OUTPUT"
}


class Gate:
    id_counter = {"IN": 0, "OUT": 0}

    def __init__(self, sim, kind, x, y):
        self.sim = sim
        self.kind = kind
        self.x = x
        self.y = y
        self.orientation = 0
        self.max_inputs = 1 if kind in ("NOT", "OUT") else 2
        self.inputs = [None] * self.max_inputs
        self.output_value = 0

        if kind == "IN":
            Gate.id_counter["IN"] += 1
            self.label_text = f"INPUT{Gate.id_counter['IN']}"
        elif kind == "OUT":
            Gate.id_counter["OUT"] += 1
            self.label_text = f"OUTPUT{Gate.id_counter['OUT']}"
        else:
            self.label_text = GATE_LABELS[kind]

        self.draw()

    def draw(self):
        c = self.sim.canvas
        x, y, w, h = self.x, self.y, NODE_W, NODE_H

        self.rect = c.create_rectangle(
            x, y, x + w, y + h,
            fill="#f3e7ff", outline=ACCENT, width=2
        )
        self.text = c.create_text(
            x + w // 2, y + h // 2,
            text=self.label_text,
            fill="black", font=("Arial", int(12*self.sim.scale_factor), "bold")
        )
        c.tag_bind(self.rect, "<Enter>", lambda e: c.itemconfig(self.rect, fill="#e0cfff"))
        c.tag_bind(self.rect, "<Leave>", lambda e: c.itemconfig(self.rect, fill="#f3e7ff"))
        c.tag_bind(self.rect, "<Button-1>", self.press)
        c.tag_bind(self.rect, "<B1-Motion>", self.drag)
        c.tag_bind(self.rect, "<Button-3>", lambda e: self.sim.delete_gate(self))
        c.tag_bind(self.text, "<Button-1>", self.press)
        c.tag_bind(self.text, "<B1-Motion>", self.drag)
        c.tag_bind(self.text, "<Button-3>", lambda e: self.sim.delete_gate(self))

        if self.kind == "IN":
            c.tag_bind(self.rect, "<Double-Button-1>", lambda e: self.toggle_input())

        self.in_ports = []
        for i in range(self.max_inputs):
            yp = y + 20 + i * 20
            p = c.create_oval(
                x - PORT_R, yp - PORT_R, x + PORT_R, yp + PORT_R,
                fill="#666", outline="white", width=2
            )
            self.in_ports.append(p)
            c.tag_bind(p, "<Button-1>", lambda e, g=self: self.sim.finish_wire(g))
            c.tag_bind(p, "<Enter>", lambda e, p=p: c.itemconfig(p, fill="#999"))
            c.tag_bind(p, "<Leave>", lambda e, p=p: c.itemconfig(p, fill="#666"))

        oy = y + h // 2
        self.out_port = c.create_oval(
            x + w - PORT_R, oy - PORT_R, x + w + PORT_R, oy + PORT_R,
            fill="#0f0", outline="white", width=2
        )
        c.tag_bind(self.out_port, "<Button-1>", lambda e, g=self: self.sim.start_wire(g))
        c.tag_bind(self.out_port, "<Enter>", lambda e: c.itemconfig(self.out_port, fill="#5f5"))
        c.tag_bind(self.out_port, "<Leave>", lambda e: c.itemconfig(self.out_port, fill="#0f0"))

    def press(self, e):
        self.start = (e.x, e.y)

    def drag(self, e):
        dx = e.x - self.start[0]
        dy = e.y - self.start[1]
        self.start = (e.x, e.y)
        for obj in [self.rect, self.text] + self.in_ports + [self.out_port]:
            self.sim.canvas.move(obj, dx, dy)
        self.x += dx
        self.y += dy
        self.sim.update_wires()

    def evaluate(self):
        if self.kind == "IN":
            return self.output_value
        if self.kind == "OUT":
            if self.inputs[0]:
                self.output_value = self.inputs[0].output_value
            return self.output_value
        fn = GATES[self.kind]
        if self.kind == "NOT":
            a = self.inputs[0].output_value if self.inputs[0] else 0
            self.output_value = fn(a)
        else:
            a = self.inputs[0].output_value if self.inputs[0] else 0
            b = self.inputs[1].output_value if self.inputs[1] else 0
            self.output_value = fn(a, b)
        return self.output_value

    def evaluate_recursive(self, visited=None):
        if visited is None:
            visited = set()
        if self in visited:
            return self.output_value
        visited.add(self)
        for inp in self.inputs:
            if inp:
                inp.evaluate_recursive(visited)
        return self.evaluate()

    def toggle_input(self):
        self.output_value = 1 - self.output_value
        self.sim.evaluate_all()
        self.sim.update_wires()

    def rotate(self):
        self.orientation = (self.orientation + 1) % 2
        self.sim.canvas.delete(self.rect)
        self.sim.canvas.delete(self.text)
        for p in self.in_ports:
            self.sim.canvas.delete(p)
        self.sim.canvas.delete(self.out_port)
        self.draw()
        self.sim.update_wires()


class Wire:
    def __init__(self, sim, src, dst, in_idx):
        self.sim = sim
        self.src = src
        self.dst = dst
        self.in_idx = in_idx
        self.dst.inputs[in_idx] = self.src
        self.draw()

    def draw(self):
        c = self.sim.canvas
        self.line = c.create_line(0, 0, 0, 0, width=3, smooth=True)
        self.label = c.create_text(0, 0, fill="white")
        c.tag_bind(self.line, "<Button-3>", lambda e: self.sim.delete_wire(self))
        self.update()

    def update(self):
        self.sim.evaluate_all()
        c = self.sim.canvas
        x1 = self.src.x + NODE_W
        y1 = self.src.y + NODE_H // 2
        x2 = self.dst.x
        y2 = self.dst.y + 20 + self.in_idx * 20
        color = "#4CAF50" if self.src.output_value else "#F44336"
        c.coords(self.line, x1, y1, (x1 + x2)//2, y1, (x1 + x2)//2, y2, x2, y2)
        c.itemconfig(self.line, fill=color)
        c.coords(self.label, (x1 + x2)//2, (y1 + y2)//2 - 10)
        c.itemconfig(self.label, text=str(self.src.output_value))


class Simulator:
    def __init__(self, root):
        self.root = root
        root.title("Logic Simulator")
        root.configure(bg=BG)
        self.scale_factor = 1.0
        self.theme = "dark"

        self.left = tk.Frame(root, width=250, bg=LEFT_BG)
        self.left.pack(side="left", fill="y")
        self.right = tk.Frame(root, width=300, bg=RIGHT_BG)
        self.right.pack(side="right", fill="y")

        self.header_label = tk.Label(root, text="Logic Gate Simulator", bg=BG, fg=ACCENT, font=("Arial",18,"bold"))
        self.header_label.pack(side="top", pady=(10,2))
        self.top_label = tk.Label(root, text="Workspace", bg=BG, fg=ACCENT, font=("Arial",14,"bold"))
        self.top_label.pack(side="top", pady=(0,5))

        self.canvas = tk.Canvas(root, bg=BG, highlightthickness=0, scrollregion=(0,0,4000,3000))
        self.canvas.pack(fill="both", expand=True)

        self.gates = []
        self.wires = []
        self.wire_start_gate = None

        self.draw_grid()
        self.build_menu()
        self.evaluate_all()

    def draw_grid(self):
        for i in range(0,4000,40):
            self.canvas.create_line(i,0,i,3000,fill=GRID,width=1)
        for j in range(0,3000,40):
            self.canvas.create_line(0,j,4000,j,fill=GRID,width=1)

    def rounded_button(self, parent, text, command, width=200, height=40, radius=12, bg="#ffffff", fg="black"):
        c = tk.Canvas(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0)
        x0, y0, x1, y1 = 2, 2, width-2, height-2
        c.create_arc(x0, y0, x0+2*radius, y0+2*radius, start=90, extent=90, fill=bg, outline=bg)
        c.create_arc(x1-2*radius, y0, x1, y0+2*radius, start=0, extent=90, fill=bg, outline=bg)
        c.create_arc(x0, y1-2*radius, x0+2*radius, y1, start=180, extent=90, fill=bg, outline=bg)
        c.create_arc(x1-2*radius, y1-2*radius, x1, y1, start=270, extent=90, fill=bg, outline=bg)
        c.create_rectangle(x0+radius, y0, x1-radius, y1, fill=bg, outline=bg)
        c.create_rectangle(x0, y0+radius, x1, y1-radius, fill=bg, outline=bg)
        c.create_text(width//2, height//2, text=text, font=("Arial", 12, "bold"), fill=fg)
        c.pack(pady=4)
        c.bind("<Button-1>", lambda e: command())
        return c

    def build_menu(self):
        tk.Label(self.left, text="INPUT / OUTPUT", bg=LEFT_BG, fg=ACCENT,
                 font=("Arial",12,"bold")).pack(pady=8)
        self.rounded_button(self.left, "INPUT", lambda:self.add_gate("IN"))
        self.rounded_button(self.left, "OUTPUT", lambda:self.add_gate("OUT"))

        tk.Label(self.left, text="LOGIC GATES", bg=LEFT_BG, fg=ACCENT,
                 font=("Arial",12,"bold")).pack(pady=8)
        for g in GATES:
            self.rounded_button(self.left, g, lambda k=g:self.add_gate(k))

        tk.Label(self.left, text="ACTIONS", bg=LEFT_BG, fg=ACCENT,
                 font=("Arial",12,"bold")).pack(pady=8)
        self.rounded_button(self.left, "Truth Table", self.truth_table)
        self.rounded_button(self.left, "Clear Workspace", self.clear_workspace)
        self.rounded_button(self.left, "Zoom In", self.zoom_in)
        self.rounded_button(self.left, "Zoom Out", self.zoom_out)
        self.rounded_button(self.left, "Toggle Theme", self.toggle_theme)
        self.rounded_button(self.left, "Save Circuit", self.save_circuit)
        self.rounded_button(self.left, "Load Circuit", self.load_circuit)

    
    def add_gate(self, kind, x=400, y=300):
        g = Gate(self, kind, x, y)
        self.gates.append(g)
        return g

    def add_wire(self, src, dst):
        for i, inp in enumerate(dst.inputs):
            if inp is None:
                self.wires.append(Wire(self, src, dst, i))
                return
        print("No free inputs!")

    def start_wire(self, gate):
        self.wire_start_gate = gate

    def finish_wire(self, gate):
        if self.wire_start_gate and gate != self.wire_start_gate:
            self.add_wire(self.wire_start_gate, gate)
        self.wire_start_gate = None

    def update_wires(self):
        for w in self.wires:
            w.update()

    def evaluate_all(self):
        visited = set()
        for g in self.gates:
            g.evaluate_recursive(visited)

   
    def truth_table(self):
        for w in self.right.winfo_children():
            w.destroy()
        tk.Label(self.right, text="Truth Table", bg=RIGHT_BG, fg=ACCENT,
                 font=("Arial",16,"bold")).pack(pady=10)

        ins = [g for g in self.gates if g.kind=="IN"]
        outs = [g for g in self.gates if g.kind=="OUT"]

        if not ins or not outs:
            tk.Label(self.right, text="Add at least 1 INPUT and 1 OUTPUT", bg=RIGHT_BG, fg="white").pack()
            return

       
        class TempGate:
            def __init__(self, gate):
                self.kind = gate.kind
                self.inputs = []
                self.output_value = gate.output_value
                self.gate_obj = gate

            def evaluate_recursive(self, visited=None):
                if visited is None:
                    visited = set()
                if self in visited:
                    return self.output_value
                visited.add(self)
                for inp in self.inputs:
                    inp.evaluate_recursive(visited)
                if self.kind == "IN":
                    return self.output_value
                if self.kind == "OUT":
                    self.output_value = self.inputs[0].output_value if self.inputs else 0
                    return self.output_value
                fn = GATES[self.kind]
                if self.kind == "NOT":
                    a = self.inputs[0].output_value if self.inputs and self.inputs[0] else 0
                    self.output_value = fn(a)
                else:
                    a = self.inputs[0].output_value if self.inputs and self.inputs[0] else 0
                    b = self.inputs[1].output_value if self.inputs and self.inputs[1] else 0
                    self.output_value = fn(a, b)
                return self.output_value

        temp_gates = [TempGate(g) for g in self.gates]
        gate_map = {g: tg for g, tg in zip(self.gates, temp_gates)}

        for g, tg in zip(self.gates, temp_gates):
            tg.inputs = [gate_map[i] for i in g.inputs if i is not None]

        frame = tk.Frame(self.right, bg=RIGHT_BG)
        frame.pack(padx=10, pady=10)

        col = 0
        for g in ins:
            tk.Label(frame, text=g.label_text, bg=ACCENT, fg="black", width=8).grid(row=0, column=col)
            col += 1
        for g in outs:
            tk.Label(frame, text=g.label_text, bg=ACCENT, fg="black", width=8).grid(row=0, column=col)
            col += 1

        row = 1
        for bits in product([0,1], repeat=len(ins)):
            for g, b in zip(ins, bits):
                gate_map[g].output_value = b
            for o in outs:
                gate_map[o].evaluate_recursive()
            col = 0
            for b in bits:
                tk.Label(frame, text=b, bg="#555", fg="white", width=8).grid(row=row, column=col)
                col += 1
            for o in outs:
                tk.Label(frame, text=gate_map[o].output_value, bg="#333", fg="white", width=8).grid(row=row, column=col)
                col += 1
            row += 1

  
    def clear_workspace(self):
        for g in self.gates:
            self.sim_delete_gate_canvas(g)
        for w in self.wires:
            self.canvas.delete(w.line)
            self.canvas.delete(w.label)
        self.gates.clear()
        self.wires.clear()
        self.wire_start_gate=None
        Gate.id_counter = {"IN":0,"OUT":0}

    def delete_gate(self, gate):
        wires_to_remove = [w for w in self.wires if w.src==gate or w.dst==gate]
        for w in wires_to_remove:
            self.delete_wire(w)
        self.sim_delete_gate_canvas(gate)
        if gate in self.gates:
            self.gates.remove(gate)
        self.evaluate_all()

    def sim_delete_gate_canvas(self, gate):
        self.canvas.delete(gate.rect)
        self.canvas.delete(gate.text)
        for p in gate.in_ports:
            self.canvas.delete(p)
        self.canvas.delete(gate.out_port)

    def delete_wire(self, wire):
        self.canvas.delete(wire.line)
        self.canvas.delete(wire.label)
        if wire.dst.inputs[wire.in_idx] == wire.src:
            wire.dst.inputs[wire.in_idx] = None
        if wire in self.wires:
            self.wires.remove(wire)
        self.evaluate_all()

    def zoom_in(self):
        self.zoom(1.2)

    def zoom_out(self):
        self.zoom(0.8)

    def zoom(self, factor):
        self.scale_factor *= factor
        self.canvas.scale("all", 0, 0, factor, factor)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        for g in self.gates:
            self.canvas.itemconfig(g.text, font=("Arial", int(12*self.scale_factor), "bold"))
        for w in self.wires:
            w.update()

    def toggle_theme(self):
        self.theme = "light" if self.theme=="dark" else "dark"
        colors = {"dark": BG, "light": "#f0f0f0"}
        self.canvas.config(bg=colors[self.theme])
        for g in self.gates:
            self.sim_delete_gate_canvas(g)
            g.draw()
        self.update_wires()

    def save_circuit(self):
        data = {"gates":[], "wires":[]}
        for g in self.gates:
            data["gates"].append({
                "kind": g.kind, "x": g.x, "y": g.y,
                "label": g.label_text, "orientation": g.orientation
            })
        for w in self.wires:
            data["wires"].append({
                "src": self.gates.index(w.src),
                "dst": self.gates.index(w.dst),
                "in_idx": w.in_idx
            })
        filename = filedialog.asksaveasfilename(defaultextension=".json")
        if filename:
            with open(filename,"w") as f:
                json.dump(data, f, indent=2)

    def load_circuit(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON files","*.json")])
        if not filename:
            return
        with open(filename) as f:
            data = json.load(f)
        self.clear_workspace()
        gate_objs = []
        for gdata in data["gates"]:
            g = self.add_gate(gdata["kind"], gdata["x"], gdata["y"])
            g.orientation = gdata.get("orientation",0)
            g.draw()
            gate_objs.append(g)
        for wdata in data["wires"]:
            src = gate_objs[wdata["src"]]
            dst = gate_objs[wdata["dst"]]
            self.wires.append(Wire(self, src, dst, wdata["in_idx"]))
        self.evaluate_all()



root = tk.Tk()
Simulator(root)
root.mainloop()
