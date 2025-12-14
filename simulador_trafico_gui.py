#!/usr/bin/env python3
import json
import queue
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import ipaddress
from dataclasses import dataclass, asdict
from pathlib import Path

APP_TITLE = "Simulador de Tráfico"
CONFIG_FILE_DEFAULT = "app_config.json"

# -------------------------
# Config (allow-list + named targets)
# -------------------------
@dataclass
class AppConfig:
    mode: str = "student"  # "student" | "instructor"
    banner: str = "LAB MODE – Allowed targets only"
    allowed_targets: list = None  # CIDRs and/or exact IPs
    require_confirm: bool = True
    targets: list = None  # [{name, ip, expected_fortiguard}]

    def __post_init__(self):
        if self.allowed_targets is None:
            self.allowed_targets = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.1/32"]
        if self.targets is None:
            self.targets = []

def load_config(path: str) -> AppConfig:
    p = Path(path)
    if not p.exists():
        return AppConfig()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return AppConfig(**data)
    except Exception:
        return AppConfig()

def save_config(path: str, cfg: AppConfig):
    Path(path).write_text(json.dumps(cfg.__dict__, indent=2), encoding="utf-8")

def ip_in_allowlist(ip_str: str, allowlist: list) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        for item in allowlist:
            item = str(item).strip()
            if not item:
                continue
            if "/" in item:
                net = ipaddress.ip_network(item, strict=False)
                if ip in net:
                    return True
            else:
                if ip == ipaddress.ip_address(item):
                    return True
        return False
    except Exception:
        return False

# -------------------------
# Scenario model
# -------------------------
@dataclass
class Scenario:
    name: str = "default"
    target_ip: str = "192.168.1.10"
    interface: str = ""
    mode: str = "one-shot"       # "one-shot" | "loop"
    interval_sec: int = 5
    curl_timeout_sec: int = 5
    load_requests: int = 50
    load_concurrency: int = 10
    path_beacon: str = "/beacon"
    path_ips_test: str = "/exploit-test"
    user_agent: str = "Lab-Traffic-Sim"


IPS_TEST_PROFILES = {
    "1) Exploit Path (/exploit-test)": {"path": "/exploit-test", "ua": "Lab-Traffic-Sim"},
    "2) User-Agent Only (/)": {"path": "/", "ua": "Lab-Traffic-Sim"},
    "3) Beacon Path (/beacon)": {"path": "/beacon", "ua": "Lab-Traffic-Sim"},
}

FEATURE_MAP = {
    "Virus Download": {
        "feature": "Antivirus / SSL inspection / Logging",
        "notes": "Descarga de test file AV en entorno controlado."
    },
    "Tráfico Apps": {
        "feature": "App Control / SSL inspection / DNS Filter",
        "notes": "Conexiones HTTPS benignas a servicios tipo video, cloud e instant messaging para probar App Control y logs."
    },
    "Web Testing": {
        "feature": "Web Filter / DNS Filter / SSL inspection",
        "notes": "Conexiones HTTPS benignas a una lista fija de websites para probar categorización y políticas web."
    },
    "IPS Test": {
        "feature": "IPS (custom signatures) / Security Profiles / Logging",
        "notes": "Usa el selector IPS Test para disparar una de 3 firmas (Path, User-Agent o Beacon)."
    },
    "IOC Beacon": {
        "feature": "IOC/Threat Feed / External Connector / Policy block",
        "notes": "Beacon HTTP benigno a endpoint del lab para demostrar bloqueo por indicador."
    },
    "Controlled Load": {
        "feature": "DoS Policy (sin flood) / Traffic shaping / Sessions monitoring",
        "notes": "Carga controlada con límites (no flood). Útil para demo de políticas."
    }
}

def list_up_interfaces():
    try:
        out = subprocess.check_output(["ip", "-o", "link", "show", "up"], text=True)
        names = []
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 2:
                name = parts[1].strip()
                if name != "lo":
                    names.append(name)
        return names or ["(none)"]
    except Exception:
        return ["(none)"]

class Runner:
    def __init__(self, log_func):
        self.log = log_func
        self.loop_threads = {}

    def _run_cmd(self, cmd, label):
        try:
            self.log(f"[{label}] Ejecutando: {' '.join(cmd)}")
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in p.stdout:
                self.log(f"[{label}] {line.rstrip()}")
            rc = p.wait()
            self.log(f"[{label}] Finalizado con código {rc}")
        except FileNotFoundError:
            self.log(f"[{label}] ERROR: Script/ejecutable no encontrado.")
        except Exception as e:
            self.log(f"[{label}] ERROR: {e}")

    def run_one_shot(self, cmd, label):
        t = threading.Thread(target=self._run_cmd, args=(cmd, label), daemon=True)
        t.start()

    def start_loop(self, key, cmd_builder, label, interval_sec):
        if key in self.loop_threads:
            self.log(f"[{label}] Ya está corriendo en loop. Usa Stop Loops.")
            return
        stop_event = threading.Event()
        self.loop_threads[key] = stop_event

        def loop():
            self.log(f"[{label}] LOOP iniciado (cada {interval_sec}s).")
            while not stop_event.is_set():
                cmd = cmd_builder()
                self._run_cmd(cmd, label)
                for _ in range(max(1, interval_sec * 10)):
                    if stop_event.is_set():
                        break
                    time.sleep(0.1)
            self.log(f"[{label}] LOOP detenido.")

        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def stop_loop(self, key, label):
        ev = self.loop_threads.get(key)
        if not ev:
            self.log(f"[{label}] No hay loop activo.")
            return
        ev.set()
        del self.loop_threads[key]

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x620")

        self.config_path = CONFIG_FILE_DEFAULT
        self.cfg = load_config(self.config_path)
        self.scenario = Scenario()

        self.log_q = queue.Queue()
        self.runner = Runner(self._log)

        # target label -> dict
        self.target_catalog = {}
        self._build_target_catalog()

        self._build_ui()
        self._refresh_interfaces()
        self._apply_banner()
        self._update_feature_panel("Virus Download")
        self.after(100, self._drain_logs)

    def _build_target_catalog(self):
        self.target_catalog = {}
        for t in self.cfg.targets or []:
            name = str(t.get("name","")).strip() or "Target"
            ip = str(t.get("ip","")).strip()
            exp = str(t.get("expected_fortiguard","")).strip()
            if not ip:
                continue
            label = f"{name} – {ip}"
            if exp:
                label += f" (FortiGuard: {exp})"
            self.target_catalog[label] = {"ip": ip, "expected": exp, "name": name}

    # ---------- UI ----------
    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text=APP_TITLE, font=("Arial", 16, "bold")).grid(row=0, column=0, sticky="w")

        self.banner_var = tk.StringVar(value="")
        ttk.Label(top, textvariable=self.banner_var, font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", padx=(12, 0))

        ttk.Button(top, text="Config (JSON)", command=self._open_config_info).grid(row=0, column=5, sticky="e")

        # Target selector (editable combobox)
        ttk.Label(top, text="IP destino / Target:").grid(row=1, column=0, sticky="w", pady=(10, 2))
        self.ip_var = tk.StringVar(value=self.scenario.target_ip)

        self.ip_combo = ttk.Combobox(top, textvariable=self.ip_var, width=48, state="normal")
        self.ip_combo["values"] = list(self.target_catalog.keys())
        self.ip_combo.grid(row=1, column=1, columnspan=2, sticky="w", padx=6, pady=(10, 2))
        self.ip_combo.bind("<<ComboboxSelected>>", self._on_target_selected)

        self.expected_var = tk.StringVar(value="Expected FortiGuard: (manual / config)")
        ttk.Label(top, textvariable=self.expected_var).grid(row=2, column=1, columnspan=3, sticky="w", padx=6, pady=(0, 6))
        # IPS Test selector
        ttk.Label(top, text="IPS Test:").grid(row=2, column=3, sticky="e", padx=(16, 2), pady=(0, 6))
        self.ips_test_var = tk.StringVar(value=list(IPS_TEST_PROFILES.keys())[0])
        self.ips_test_combo = ttk.Combobox(top, textvariable=self.ips_test_var, width=28, state="readonly")
        self.ips_test_combo["values"] = list(IPS_TEST_PROFILES.keys())
        self.ips_test_combo.grid(row=2, column=4, sticky="w", pady=(0, 6))

        # Interface selector
        ttk.Label(top, text="Interfaz:").grid(row=1, column=3, sticky="w", padx=(16, 2), pady=(10, 2))
        self.if_var = tk.StringVar()
        self.if_combo = ttk.Combobox(top, textvariable=self.if_var, width=18, state="readonly")
        self.if_combo.grid(row=1, column=4, sticky="w", pady=(10, 2))
        ttk.Button(top, text="Refresh", command=self._refresh_interfaces).grid(row=1, column=5, padx=6, pady=(10, 2))

        # Mode
        ttk.Label(top, text="Modo:").grid(row=3, column=0, sticky="w", pady=(6, 2))
        self.mode_var = tk.StringVar(value="one-shot")
        ttk.Radiobutton(top, text="One-shot", value="one-shot", variable=self.mode_var).grid(row=3, column=1, sticky="w", pady=(6, 2))
        ttk.Radiobutton(top, text="Loop", value="loop", variable=self.mode_var).grid(row=3, column=1, sticky="e", pady=(6, 2))

        ttk.Label(top, text="Intervalo (s):").grid(row=3, column=3, sticky="w", padx=(16, 2), pady=(6, 2))
        self.interval_var = tk.IntVar(value=self.scenario.interval_sec)
        ttk.Spinbox(top, from_=1, to=3600, textvariable=self.interval_var, width=7).grid(row=3, column=4, sticky="w", pady=(6, 2))

        main = ttk.Frame(self, padding=(10, 0, 10, 10))
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="y", padx=(0, 10))

        ttk.Label(left, text="Acciones", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 6))

        self._add_action_button(left, "Virus Download", self._action_virus)
        self._add_action_button(left, "Tráfico Apps", self._action_apps)
        self._add_action_button(left, "Web Testing", self._action_web_testing)
        self._add_action_button(left, "IPS Test", self._action_ips_test)
        self._add_action_button(left, "IOC Beacon", self._action_ioc_beacon)
        self._add_action_button(left, "Controlled Load", self._action_controlled_load)

        ttk.Separator(left).pack(fill="x", pady=10)
        ttk.Button(left, text="Stop Loops", command=self._stop_all_loops).pack(fill="x", pady=(0, 6))
        ttk.Button(left, text="Export Scenario JSON", command=self._export_scenario_json).pack(fill="x", pady=(0, 6))
        ttk.Button(left, text="Import Scenario JSON", command=self._import_scenario_json).pack(fill="x")

        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True)

        feat = ttk.LabelFrame(right, text="¿Qué se prueba en FortiGate?", padding=10)
        feat.pack(fill="x")

        self.feature_title = ttk.Label(feat, text="", font=("Arial", 11, "bold"))
        self.feature_title.pack(anchor="w")

        self.feature_body = ttk.Label(feat, text="", wraplength=700, justify="left")
        self.feature_body.pack(anchor="w", pady=(6, 0))

        logs = ttk.LabelFrame(right, text="Logs", padding=8)
        logs.pack(fill="both", expand=True, pady=(10, 0))

        self.log_text = tk.Text(logs, height=12, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

        bottom = ttk.Frame(self, padding=(10, 0, 10, 10))
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Clear Logs", command=self._clear_logs).pack(side="left")

    def _on_target_selected(self, _evt=None):
        sel = self.ip_var.get().strip()
        info = self.target_catalog.get(sel)
        if info:
            exp = info.get("expected") or "(no definido en config)"
            self.expected_var.set(f"Expected FortiGuard: {exp}")
        else:
            self.expected_var.set("Expected FortiGuard: (manual / config)")

    def _add_action_button(self, parent, label, cmd):
        ttk.Button(parent, text=label, command=lambda: self._on_action(label, cmd)).pack(fill="x", pady=4)

    def _on_action(self, label, cmd):
        self._update_feature_panel(label)
        cmd()

    def _update_feature_panel(self, label):
        info = FEATURE_MAP.get(label, {"feature": "", "notes": ""})
        self.feature_title.config(text=f"{label}  |  {info.get('feature','')}")
        self.feature_body.config(text=info.get("notes", ""))

    def _apply_banner(self):
        self.banner_var.set(self.cfg.banner)

    def _open_config_info(self):
        msg = (
            f"Config: {self.config_path}\n\n"
            "Este simulador usa una allow-list de destinos (allowed_targets).\n"
            "También puedes definir targets con nombre y categoría esperada (targets).\n\n"
            "Ejemplo (targets):\n"
            '  {"name":"Target #1","ip":"1.2.3.4","expected_fortiguard":"Anti-Botnet"}\n'
        )
        messagebox.showinfo("Config JSON", msg)

    def _refresh_interfaces(self):
        items = list_up_interfaces()
        self.if_combo["values"] = items
        if items and self.if_var.get() not in items:
            self.if_var.set(items[0])

    def _get_target_ip(self) -> str:
        raw = self.ip_var.get().strip()
        # If selection is one of the catalog labels, use its exact IP
        if raw in self.target_catalog:
            return self.target_catalog[raw]["ip"]
        # Otherwise treat it as a direct IP entry
        return raw.split()[0] if raw else raw

    # ---------- Scenario import/export ----------
    def _current_scenario(self) -> Scenario:
        sc = Scenario(**asdict(self.scenario))
        sc.target_ip = self._get_target_ip()
        sc.interface = self.if_var.get().strip()
        sc.mode = self.mode_var.get()
        sc.interval_sec = int(self.interval_var.get())
        return sc

    def _export_scenario_json(self):
        sc = self._current_scenario()
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], title="Export scenario JSON")
        if not path:
            return
        payload = {"scenario": asdict(sc)}
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        messagebox.showinfo("Exportado", f"Escenario guardado en:\n{path}")

    def _import_scenario_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")], title="Import scenario JSON")
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            sc_dict = payload.get("scenario", {})
            sc = Scenario(**sc_dict)
            self.scenario = sc
            self.ip_var.set(sc.target_ip)
            self.mode_var.set(sc.mode)
            self.interval_var.set(sc.interval_sec)
            if sc.interface:
                self.if_var.set(sc.interface)
            self._on_target_selected()
            messagebox.showinfo("Importado", f"Escenario cargado:\n{sc.name}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo importar JSON:\n{e}")

    # ---------- Policy checks ----------
    def _target_allowed(self, ip_str: str) -> bool:
        if not ip_str.strip():
            messagebox.showwarning("IP requerida", "Ingrese una IP destino.")
            return False
        if not ip_in_allowlist(ip_str, self.cfg.allowed_targets):
            messagebox.showerror(
                "Destino no permitido",
                "Este destino no está en la allow-list.\n\n"
                "Edita app_config.json > allowed_targets para agregar tu red/IP de laboratorio."
            )
            return False
        if self.cfg.mode == "instructor" and self.cfg.require_confirm:
            if not messagebox.askyesno("Confirmación", "Confirma que este destino pertenece a un laboratorio controlado. ¿Continuar?"):
                return False
        return True

    # ---------- Logging ----------
    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log_q.put(f"{ts} {msg}")

    def _drain_logs(self):
        try:
            while True:
                msg = self.log_q.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._drain_logs)

    def _clear_logs(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ---------- Execution helper ----------
    def _exec_by_mode(self, key, cmd_builder, label, sc: Scenario):
        if sc.mode == "one-shot":
            self.runner.run_one_shot(cmd_builder(), label)
        else:
            self.runner.start_loop(key, cmd_builder, label, sc.interval_sec)

    # ---------- Actions ----------
    def _action_virus(self):
        sc = self._current_scenario()
        self._exec_by_mode("virus", lambda: ["./virus.sh"], "Virus Download", sc)

    def _action_apps(self):
        sc = self._current_scenario()
        self._exec_by_mode("apps", lambda: ["./app_traffic.sh"], "Tráfico Apps", sc)

    def _action_web_testing(self):
        sc = self._current_scenario()
        self._exec_by_mode("webtest", lambda: ["./web_testing.sh"], "Web Testing", sc)

    def _action_ips_test(self):
        sc = self._current_scenario()
        if not self._target_allowed(sc.target_ip):
            return

        profile_name = self.ips_test_var.get() if hasattr(self, "ips_test_var") else list(IPS_TEST_PROFILES.keys())[0]
        prof = IPS_TEST_PROFILES.get(profile_name, list(IPS_TEST_PROFILES.values())[0])
        path = prof.get("path", sc.path_ips_test)
        ua = prof.get("ua", sc.user_agent)

        self._exec_by_mode(
            "ips",
            lambda: ["./ips_test.sh", sc.target_ip, path, ua, str(sc.curl_timeout_sec)],
            "IPS Test",
            sc
        )

    def _action_ioc_beacon(self):
        sc = self._current_scenario()
        if not self._target_allowed(sc.target_ip):
            return
        self._exec_by_mode("ioc", lambda: ["./ioc_beacon.sh", sc.target_ip, sc.path_beacon, sc.user_agent, str(sc.curl_timeout_sec)], "IOC Beacon", sc)

    def _action_controlled_load(self):
        sc = self._current_scenario()
        if not self._target_allowed(sc.target_ip):
            return
        self._exec_by_mode("load", lambda: ["./controlled_load.sh", sc.target_ip, str(sc.load_requests), str(sc.load_concurrency), str(sc.curl_timeout_sec)], "Controlled Load", sc)

    def _stop_all_loops(self):
        for k, lbl in [
            ("virus","Virus Download"),
            ("apps","Tráfico Apps"),
            ("webtest","Web Testing"),
            ("ips","IPS Test"),
            ("ioc","IOC Beacon"),
            ("load","Controlled Load")
        ]:
            self.runner.stop_loop(k, lbl)

if __name__ == "__main__":
    if not Path(CONFIG_FILE_DEFAULT).exists():
        save_config(CONFIG_FILE_DEFAULT, AppConfig())
    App().mainloop()
