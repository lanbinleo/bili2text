from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from b2t.i18n import tr
from b2t.inputs import parse_source_list
from b2t.models import TranscriptResult
from b2t.pipeline import B2TPipeline


class WindowApp:
    def __init__(
        self,
        *,
        pipeline_factory: Callable[[str, str, Path | None], B2TPipeline],
        default_provider: str = "whisper",
        default_model: str = "small",
        default_workspace: Path | None = None,
        language: str = "zh-CN",
    ) -> None:
        self.pipeline_factory = pipeline_factory
        self.language = language
        self.event_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.latest_result: TranscriptResult | None = None
        self.is_running = False

        self.root = tk.Tk()
        self.root.title(tr(self.language, "window_title"))
        self.root.geometry("980x700")
        self.root.minsize(840, 620)

        self.provider_var = tk.StringVar(value=default_provider)
        self.model_var = tk.StringVar(value=default_model)
        self.workspace_var = tk.StringVar(value=str(default_workspace or Path(".b2t").resolve()))
        self.status_var = tk.StringVar(value=tr(self.language, "window_status_ready"))

        self._build_layout()
        self.root.after(100, self._drain_events)

    def run(self) -> None:
        self.root.mainloop()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        top = ttk.Frame(self.root, padding=16)
        top.grid(row=0, column=0, sticky="nsew")
        top.columnconfigure(1, weight=1)
        top.columnconfigure(3, weight=1)

        ttk.Label(top, text=tr(self.language, "window_source")).grid(row=0, column=0, sticky="w")
        self.source_text = tk.Text(top, height=3, wrap="word")
        self.source_text.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(8, 8))

        ttk.Button(top, text=tr(self.language, "window_choose_file"), command=self._choose_file).grid(row=0, column=4, sticky="ew")

        ttk.Label(top, text=tr(self.language, "window_provider")).grid(row=1, column=0, sticky="w", pady=(10, 0))
        provider_box = ttk.Combobox(
            top,
            textvariable=self.provider_var,
            values=["whisper", "sensevoice", "volcengine"],
            state="readonly",
        )
        provider_box.grid(row=1, column=1, sticky="ew", padx=(8, 16), pady=(10, 0))

        ttk.Label(top, text=tr(self.language, "window_model")).grid(row=1, column=2, sticky="w", pady=(10, 0))
        model_box = ttk.Combobox(
            top,
            textvariable=self.model_var,
            values=["tiny", "base", "small", "medium", "large"],
            state="normal",
        )
        model_box.grid(row=1, column=3, sticky="ew", padx=(8, 8), pady=(10, 0))

        ttk.Label(top, text=tr(self.language, "window_workspace")).grid(row=2, column=0, sticky="w", pady=(10, 0))
        workspace_entry = ttk.Entry(top, textvariable=self.workspace_var)
        workspace_entry.grid(row=2, column=1, columnspan=3, sticky="ew", padx=(8, 8), pady=(10, 0))
        ttk.Button(top, text=tr(self.language, "window_browse"), command=self._choose_workspace).grid(row=2, column=4, sticky="ew", pady=(10, 0))

        ttk.Label(top, text=tr(self.language, "window_prompt")).grid(row=3, column=0, sticky="nw", pady=(10, 0))
        self.prompt_text = tk.Text(top, height=5, wrap="word")
        self.prompt_text.grid(row=3, column=1, columnspan=4, sticky="nsew", padx=(8, 0), pady=(10, 0))
        self.prompt_text.insert("1.0", "以下是普通话的句子。")

        button_row = ttk.Frame(top)
        button_row.grid(row=4, column=0, columnspan=5, sticky="ew", pady=(12, 0))
        for column in range(5):
            button_row.columnconfigure(column, weight=1)

        self.transcribe_button = ttk.Button(button_row, text=tr(self.language, "window_start"), command=self.start_transcribe)
        self.transcribe_button.grid(row=0, column=0, sticky="ew")
        ttk.Button(button_row, text=tr(self.language, "window_clear_log"), command=self._clear_log).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Button(button_row, text=tr(self.language, "window_open_transcript"), command=self._open_transcript).grid(row=0, column=2, sticky="ew", padx=(8, 0))
        ttk.Button(button_row, text=tr(self.language, "window_open_workspace"), command=self._open_workspace).grid(row=0, column=3, sticky="ew", padx=(8, 0))
        ttk.Button(button_row, text=tr(self.language, "window_open_repo"), command=self._open_repo).grid(row=0, column=4, sticky="ew", padx=(8, 0))

        body = ttk.Panedwindow(self.root, orient=tk.VERTICAL)
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        log_frame = ttk.Labelframe(body, text=tr(self.language, "window_log"), padding=8)
        result_frame = ttk.Labelframe(body, text=tr(self.language, "window_result_preview"), padding=8)
        body.add(log_frame, weight=1)
        body.add(result_frame, weight=1)

        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=14, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.result_text = tk.Text(result_frame, height=14, wrap="word", state="disabled")
        self.result_text.grid(row=0, column=0, sticky="nsew")
        result_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_text.yview)
        result_scroll.grid(row=0, column=1, sticky="ns")
        self.result_text.configure(yscrollcommand=result_scroll.set)

        status_bar = ttk.Frame(self.root, padding=(16, 0, 16, 12))
        status_bar.grid(row=2, column=0, sticky="ew")
        status_bar.columnconfigure(0, weight=1)
        ttk.Label(status_bar, textvariable=self.status_var).grid(row=0, column=0, sticky="w")

    def start_transcribe(self) -> None:
        if self.is_running:
            return

        source_text = self.source_text.get("1.0", "end").strip()
        try:
            sources = parse_source_list(source_text)
        except ValueError:
            messagebox.showwarning("bili2text", tr(self.language, "window_missing_source"))
            return

        workspace_text = self.workspace_var.get().strip()
        workspace = Path(workspace_text).expanduser() if workspace_text else None
        provider = self.provider_var.get().strip() or "whisper"
        model = self.model_var.get().strip() or "small"
        prompt = self.prompt_text.get("1.0", "end").strip() or None

        self.is_running = True
        self.transcribe_button.state(["disabled"])
        self.status_var.set(tr(self.language, "window_status_running"))
        self._append_log(tr(self.language, "window_starting", provider=provider, model=model))
        if len(sources) > 1:
            self._append_log(tr(self.language, "window_batch_submitted", count=len(sources)))

        thread = threading.Thread(
            target=self._run_pipeline,
            args=(sources, provider, model, workspace, prompt),
            daemon=True,
        )
        thread.start()

    def _run_pipeline(
        self,
        sources: list[str],
        provider: str,
        model: str,
        workspace: Path | None,
        prompt: str | None,
    ) -> None:
        completed = 0
        failed = 0
        pipeline = None
        for index, source in enumerate(sources, start=1):
            try:
                if pipeline is None:
                    pipeline = self.pipeline_factory(provider, model, workspace)
                    self.event_queue.put(("log", tr(self.language, "window_pipeline_ready", workspace=pipeline.settings.workspace_root)))
                self.event_queue.put(("log", tr(self.language, "window_batch_item_start", index=index, total=len(sources), source=source)))
                result = pipeline.transcribe(source, prompt=prompt)
                completed += 1
                self.event_queue.put(("result", result))
            except Exception as exc:
                failed += 1
                self.event_queue.put(("log", tr(self.language, "window_batch_item_failed", index=index, source=source, message=exc)))
        self.event_queue.put(("done", {"completed": completed, "failed": failed}))

    def _drain_events(self) -> None:
        while True:
            try:
                kind, payload = self.event_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "log":
                self._append_log(str(payload))
            elif kind == "result":
                result = payload
                assert isinstance(result, TranscriptResult)
                self.latest_result = result
                self._append_log(tr(self.language, "transcript_saved", path=result.transcript_path))
                self._append_log(tr(self.language, "metadata_saved", path=result.metadata_path))
                self._set_result_text(result.text)
            elif kind == "done":
                assert isinstance(payload, dict)
                self._append_log(tr(self.language, "window_batch_finished", completed=payload["completed"], failed=payload["failed"]))
                status_key = "window_status_failed" if payload["completed"] == 0 and payload["failed"] > 0 else "window_status_completed"
                self.status_var.set(tr(self.language, status_key))
                self.is_running = False
                self.transcribe_button.state(["!disabled"])
            elif kind == "error":
                self._append_log(tr(self.language, "window_error", message=payload))
                self.status_var.set(tr(self.language, "window_status_failed"))
                self.is_running = False
                self.transcribe_button.state(["!disabled"])
                messagebox.showerror("bili2text", str(payload))

        self.root.after(100, self._drain_events)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_result_text(self, value: str) -> None:
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", value)
        self.result_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title=tr(self.language, "window_choose_file"),
            filetypes=[
                ("Media", "*.mp4 *.mkv *.mov *.flv *.avi *.webm *.mp3 *.wav *.m4a *.flac *.ogg *.aac"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.source_text.delete("1.0", "end")
            self.source_text.insert("1.0", path)

    def _choose_workspace(self) -> None:
        directory = filedialog.askdirectory(title=tr(self.language, "window_choose_workspace"))
        if directory:
            self.workspace_var.set(directory)

    def _open_transcript(self) -> None:
        if not self.latest_result:
            messagebox.showinfo("bili2text", tr(self.language, "window_no_result"))
            return
        _open_path(self.latest_result.transcript_path)

    def _open_workspace(self) -> None:
        workspace = Path(self.workspace_var.get()).expanduser()
        workspace.mkdir(parents=True, exist_ok=True)
        _open_path(workspace)

    def _open_repo(self) -> None:
        webbrowser.open_new_tab("https://github.com/lanbinleo/bili2text")


def run_window(
    *,
    pipeline_factory: Callable[[str, str, Path | None], B2TPipeline],
    default_provider: str = "whisper",
    default_model: str = "small",
    default_workspace: Path | None = None,
    language: str = "zh-CN",
) -> None:
    app = WindowApp(
        pipeline_factory=pipeline_factory,
        default_provider=default_provider,
        default_model=default_model,
        default_workspace=default_workspace,
        language=language,
    )
    app.run()


def _open_path(path: Path) -> None:
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    webbrowser.open(path.as_uri())
