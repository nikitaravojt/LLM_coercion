"""
testing_ui.py
Messaging-style UI for visualising deliberation chamber episodes.
Supports multiple questions with sidebar navigation.

Run:  python testing_ui.py [attack_type] [mitigation]
      e.g. python testing_ui.py consensus none
"""

import tkinter as tk
import threading
import sys

from episode import run_episode, log_episode_narrative
from config import TARGET_MODEL
from questions import get_questions


# ── Colours & fonts ───────────────────────────────────────────────────────────

BG          = "#1a1a2e"
SIDEBAR_BG  = "#12121f"
TARGET_FG   = "#64d8ff"
PRESSURE_FG = "#ff6b6b"
JUDGE_FG    = "#ffe066"
ROUND_FG    = "#8888aa"
META_FG     = "#444466"
TEXT_FG     = "#e8e8e8"
SUCCESS_FG  = "#66ff88"
FAIL_FG     = "#ff6b6b"
HEDGE_FG    = "#ffaa44"
BTN_BG      = "#2a2a4e"
BTN_FG      = "#ccccdd"
ACTIVE_BG   = "#3a3a6e"

FONT_BODY    = ("Consolas", 11)
FONT_LABEL   = ("Consolas", 10, "bold")
FONT_ROUND   = ("Consolas", 10)
FONT_SIDEBAR = ("Consolas", 9)
FONT_HEADER  = ("Consolas", 12, "bold")

STREAM_DELAY_MS = 400  # ms between chat blocks when streaming a result


# ── UI ────────────────────────────────────────────────────────────────────────

class DeliberationUI:

    def __init__(self, root, attack_type="consensus", mitigation="none", log_filename=None):
        self.root = root
        self.root.title("Deliberation Chamber")
        self.root.configure(bg=BG)
        self.root.geometry("1060x700")

        self.questions = get_questions()
        self.attack_type = attack_type
        self.mitigation = mitigation
        self.log_filename = log_filename  # None → use default from config

        # one slot per question — None until run
        self.results = [None] * len(self.questions)
        self.current_idx = 0
        self.running = False

        self._build_layout()
        self._refresh_sidebar()
        self._show_welcome()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_layout(self):
        # top bar
        top = tk.Frame(self.root, bg=BG, height=40)
        top.pack(fill=tk.X, padx=10, pady=(8, 0))
        tk.Label(top, text="DELIBERATION CHAMBER", bg=BG, fg=ROUND_FG, font=FONT_HEADER).pack(side=tk.LEFT)
        tk.Label(top, text=f"target: {TARGET_MODEL}", bg=BG, fg=META_FG, font=FONT_SIDEBAR).pack(side=tk.LEFT, padx=(12, 0))
        self.status_lbl = tk.Label(top, text="", bg=BG, fg=META_FG, font=FONT_SIDEBAR)
        self.status_lbl.pack(side=tk.RIGHT)

        # main split: sidebar | chat
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # sidebar
        sidebar = tk.Frame(main, bg=SIDEBAR_BG, width=250)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="QUESTIONS", bg=SIDEBAR_BG, fg=ROUND_FG, font=FONT_LABEL, pady=6).pack(fill=tk.X)
        self.sb_frame = tk.Frame(sidebar, bg=SIDEBAR_BG)
        self.sb_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # domain filter checkboxes
        filter_frame = tk.Frame(sidebar, bg=SIDEBAR_BG)
        filter_frame.pack(fill=tk.X, padx=8, pady=(4, 0))
        tk.Label(filter_frame, text="RUN ALL — domains:", bg=SIDEBAR_BG, fg=ROUND_FG,
                 font=FONT_SIDEBAR, anchor=tk.W).pack(fill=tk.X)

        self.domain_vars = {}
        for domain in ["factual", "logical", "normative"]:
            var = tk.BooleanVar(value=True)
            self.domain_vars[domain] = var
            tk.Checkbutton(filter_frame, text=domain, variable=var,
                           bg=SIDEBAR_BG, fg=BTN_FG, selectcolor=BTN_BG,
                           activebackground=SIDEBAR_BG, activeforeground=BTN_FG,
                           font=FONT_SIDEBAR, anchor=tk.W).pack(fill=tk.X)

        btn_frame = tk.Frame(sidebar, bg=SIDEBAR_BG)
        btn_frame.pack(fill=tk.X, padx=4, pady=6)

        self.run_btn = tk.Button(btn_frame, text="▶  Run Selected", bg=BTN_BG, fg=BTN_FG,
                                 font=FONT_SIDEBAR, relief=tk.FLAT, command=self._run_current)
        self.run_btn.pack(fill=tk.X, pady=2)

        self.run_all_btn = tk.Button(btn_frame, text="▶▶  Run All", bg=BTN_BG, fg=BTN_FG,
                                     font=FONT_SIDEBAR, relief=tk.FLAT, command=self._run_all)
        self.run_all_btn.pack(fill=tk.X, pady=2)

        # chat area
        chat = tk.Frame(main, bg=BG)
        chat.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text = tk.Text(chat, bg=BG, fg=TEXT_FG, font=FONT_BODY, wrap=tk.WORD,
                            state=tk.DISABLED, relief=tk.FLAT, padx=10, pady=10)
        sb = tk.Scrollbar(chat, command=self.text.yview, bg=BG)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(fill=tk.BOTH, expand=True)

        # tags
        for name, kwargs in {
            "target_label":   {"foreground": TARGET_FG,   "font": FONT_LABEL, "lmargin1": 10},
            "target_body":    {"foreground": TEXT_FG,      "font": FONT_BODY,  "lmargin1": 10},
            "pressure_label": {"foreground": PRESSURE_FG,  "font": FONT_LABEL, "justify": tk.RIGHT, "rmargin": 10},
            "pressure_body":  {"foreground": TEXT_FG,      "font": FONT_BODY,  "justify": tk.RIGHT, "rmargin": 10},
            "judge_label":    {"foreground": JUDGE_FG,     "font": FONT_LABEL, "justify": tk.CENTER},
            "judge_body":     {"foreground": JUDGE_FG,     "font": FONT_BODY,  "justify": tk.CENTER, "lmargin1": 80, "rmargin": 80},
            "round_delim":    {"foreground": ROUND_FG,     "font": FONT_ROUND, "justify": tk.CENTER, "spacing1": 10},
            "status":         {"foreground": META_FG,      "font": FONT_ROUND, "justify": tk.CENTER},
            "maintained":     {"foreground": SUCCESS_FG,   "font": FONT_LABEL, "justify": tk.CENTER},
            "hedged":         {"foreground": HEDGE_FG,     "font": FONT_LABEL, "justify": tk.CENTER},
            "reversed":       {"foreground": FAIL_FG,      "font": FONT_LABEL, "justify": tk.CENTER},
        }.items():
            self.text.tag_configure(name, **kwargs)

    # ── Sidebar ───────────────────────────────────────────────────────────

    def _refresh_sidebar(self):
        for w in self.sb_frame.winfo_children():
            w.destroy()

        self.sb_buttons = []
        sb_state = tk.DISABLED if self.running else tk.NORMAL
        for i, q in enumerate(self.questions):
            r = self.results[i]
            icon = "○" if r is None else {"MAINTAINED": "●", "HEDGED": "◐", "REVERSED": "◉"}[r["final_label"]]
            label = f"{icon} {i+1}. [{q['domain'][:4]}] {q['text'][:28]}..."

            bg = ACTIVE_BG if i == self.current_idx else SIDEBAR_BG
            btn = tk.Button(self.sb_frame, text=label, bg=bg, fg=BTN_FG, font=FONT_SIDEBAR,
                            relief=tk.FLAT, anchor=tk.W, padx=4, pady=3,
                            state=sb_state,
                            command=lambda idx=i: self._sidebar_click(idx))
            btn.pack(fill=tk.X, pady=1)
            self.sb_buttons.append(btn)

    def _sidebar_click(self, idx):
        """Clicking a sidebar question selects it and shows a ready-to-run prompt."""
        if self.running:
            return
        self.current_idx = idx
        self._refresh_sidebar()
        self._show_selected(idx)

    # ── Chat helpers ──────────────────────────────────────────────────────

    def _clear(self):
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.configure(state=tk.DISABLED)

    def _w(self, txt, tag):
        self.text.configure(state=tk.NORMAL)
        self.text.insert(tk.END, txt + "\n", tag)
        self.text.configure(state=tk.DISABLED)
        self.text.see(tk.END)

    def _show_welcome(self):
        self._clear()
        self._w("\n  DELIBERATION CHAMBER\n", "round_delim")
        self._w("  This tool runs simulated social pressure episodes against a target LLM.", "status")
        self._w("  A pressure agent challenges the target's answer each round.", "status")
        self._w("  A judge then classifies each response: MAINTAINED, HEDGED, or REVERSED.\n", "status")
        from config import NARRATIVE_FILENAME
        self._w(f"  Attack type : {self.attack_type}", "status")
        self._w(f"  Mitigation  : {self.mitigation}", "status")
        self._w(f"  Questions   : {len(self.questions)} loaded", "status")
        self._w(f"  Logging to  : {self.log_filename or NARRATIVE_FILENAME}\n", "status")
        self._w("  ─" * 25, "round_delim")
        self._w("\n  Select a question from the sidebar, then press  ▶ Run Selected.\n", "status")

    def _show_selected(self, idx):
        self._clear()
        q = self.questions[idx]
        r = self.results[idx]
        self._w(f"\n  QUESTION {idx+1}/{len(self.questions)}  [{q['domain']}]\n", "round_delim")
        self._w(f"  {q['text']}\n", "status")
        if r is not None:
            tag = r["final_label"].lower() if r["final_label"].lower() in ("maintained", "hedged", "reversed") else "status"
            self._w(f"  Already run  —  {r['final_label']}  |  traj: {r['trajectory']}", tag)
            self._w("  Press  ▶ Run Selected  to re-run, or select another question.\n", "status")
        else:
            self._w("  Ready to run.  Press  ▶ Run Selected  to start the episode.\n", "status")

    def _show_running(self, idx, batch_pos=None):
        """Draw the static episode header; live log lines are appended below."""
        self._clear()
        q = self.questions[idx]
        prefix = f"[{batch_pos}]  " if batch_pos else ""
        self._w(f"\n  {prefix}RUNNING EPISODE  —  question {idx+1}/{len(self.questions)}  [{q['domain']}]\n", "round_delim")
        self._w(f"  {q['text']}\n", "status")
        self._w(f"  Attack : {self.attack_type}  |  Mitigation : {self.mitigation}", "status")
        self._w("  " + "─" * 48, "round_delim")

    def _log(self, msg, tag="status"):
        """Append a single live-log line to the chat panel."""
        self._w(msg, tag)

    # ── Streaming result display ──────────────────────────────────────────

    def _stream_result(self, result, idx=None):
        """Write result blocks to the chat panel one at a time with delays."""
        self._clear()
        if idx is None:
            idx = self.current_idx
        q = self.questions[idx]

        # build a flat list of callables to schedule
        steps = []

        def header():
            self._w(f"\n  QUESTION {idx+1}/{len(self.questions)}", "status")
            self._w(f"  {q['text']}", "status")
            self._w(f"  domain: {q['domain']}  |  attack: {self.attack_type}  |  mitigation: {self.mitigation}\n", "status")
            self._w("── ROUND 0 ─ initial position " + "─" * 30, "round_delim")
            self._w("TARGET", "target_label")
            self._w(result["initial_response"], "target_body")
        steps.append(header)

        for rd in result["rounds"]:
            def pressure(rd=rd):
                self._w(f"\n── ROUND {rd['round']} " + "─" * 40, "round_delim")
                self._w("PRESSURE", "pressure_label")
                self._w(rd["pressure_message"], "pressure_body")

            def target(rd=rd):
                self._w("TARGET", "target_label")
                self._w(rd["target_response"], "target_body")

            def judge(rd=rd):
                tag = rd["label"].lower() if rd["label"].lower() in ("maintained", "hedged", "reversed") else "judge_label"
                self._w(f"JUDGE  ▸  {rd['label']}  (CDS={rd['cds']})", tag)
                self._w(rd["reasoning"], "judge_body")
                if rd["label"] == "REVERSED":
                    self._w("\n  ⚠  REVERSAL DETECTED — episode ended early", "reversed")

            steps += [pressure, target, judge]

        def final():
            tag = result["final_label"].lower() if result["final_label"].lower() in ("maintained", "hedged", "reversed") else "status"
            self._w(f"\n{'─' * 50}", "round_delim")
            self._w(f"  RESULT: {result['final_label']}  |  RFC: {result['rfc']}  |  RFR: {result['rfr']}  |  traj: {result['trajectory']}", tag)
        steps.append(final)

        for i, fn in enumerate(steps):
            self.root.after(i * STREAM_DELAY_MS, fn)

    # ── Run logic ─────────────────────────────────────────────────────────

    def _set_running(self, val):
        self.running = val
        st = tk.DISABLED if val else tk.NORMAL
        self.run_btn.configure(state=st)
        self.run_all_btn.configure(state=st)
        if not val:
            self._refresh_sidebar()

    def _run_current(self):
        """Run the currently selected question."""
        if self.running:
            return
        self._launch_episode(self.current_idx, release_lock=True)

    def _run_all(self):
        if self.running:
            return
        selected_domains = {d for d, var in self.domain_vars.items() if var.get()}
        targets = [i for i, q in enumerate(self.questions) if q["domain"] in selected_domains]
        if not targets:
            self.status_lbl.configure(text="No domains selected.")
            return
        self._set_running(True)
        threading.Thread(target=self._run_all_thread, args=(targets,), daemon=True).start()

    def _run_all_thread(self, indices):
        total = len(indices)
        for n, idx in enumerate(indices, 1):
            self.root.after(0, lambda i=idx: setattr(self, "current_idx", i))
            self.root.after(0, self._refresh_sidebar)
            self._episode_worker(idx, release_lock=False, batch_pos=f"{n}/{total}")
        self.root.after(0, lambda: self._log(f"\n  ══  All {total} episodes complete.  ══", "round_delim"))
        self.root.after(0, lambda: self.status_lbl.configure(text=f"Batch complete — {total} episodes run."))
        self.root.after(0, lambda: self._set_running(False))

    def _launch_episode(self, idx, release_lock):
        """Set running state and start background thread for one episode."""
        self._set_running(True)
        threading.Thread(target=self._episode_worker, args=(idx, release_lock), daemon=True).start()

    def _episode_worker(self, idx, release_lock, batch_pos=None):
        """Background thread: run one episode and stream result to UI when done."""
        q = self.questions[idx]
        self.root.after(0, lambda: self.status_lbl.configure(text=f"Running {idx+1}/{len(self.questions)}..."))
        self.root.after(0, lambda i=idx, bp=batch_pos: self._show_running(i, bp))

        stage_labels = {
            "initial":    "  Round 0  —  waiting for initial response...",
            "pressure":   "  Round {round_num}  —  pressure agent generating...",
            "target":     "  Round {round_num}  —  target responding...",
            "judge":      "  Round {round_num}  —  judge classifying...",
            "round_done": "  Round {round_num}  —  {label}",
        }
        round_done_tags = {"MAINTAINED": "maintained", "HEDGED": "hedged", "REVERSED": "reversed"}

        def on_progress(stage, **kwargs):
            template = stage_labels.get(stage, "")
            msg = template.format(**kwargs)
            tag = round_done_tags.get(kwargs.get("label", ""), "status") if stage == "round_done" else "status"
            self.root.after(0, lambda m=msg, t=tag: self._log(m, t))

        result = run_episode(
            question=q["text"],
            attack_type=self.attack_type,
            mitigation=self.mitigation,
            domain=q.get("domain", ""),
            on_progress=on_progress,
        )

        self.results[idx] = result
        log_episode_narrative(result, **({'filename': self.log_filename} if self.log_filename else {}))
        done_tag = result["final_label"].lower() if result["final_label"].lower() in ("maintained", "hedged", "reversed") else "status"
        self.root.after(0, lambda: self._log(f"\n  Episode complete  —  {result['final_label']}  |  traj: {result['trajectory']}", done_tag))
        self.root.after(0, self._refresh_sidebar)
        if release_lock:
            self.root.after(0, lambda r=result, i=idx: self._stream_result(r, i))
            self.root.after(0, lambda: self.status_lbl.configure(text=f"Done — {result['final_label']}"))
            self.root.after(0, lambda: self._set_running(False))



# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    attack      = sys.argv[1] if len(sys.argv) > 1 else "consensus"
    mitigation  = sys.argv[2] if len(sys.argv) > 2 else "none"
    log_file    = sys.argv[3] if len(sys.argv) > 3 else None

    root = tk.Tk()
    app = DeliberationUI(root, attack_type=attack, mitigation=mitigation, log_filename=log_file)
    root.mainloop()