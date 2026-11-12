"""Exécution de commandes externes avec progression, log et annulation."""

import subprocess
import threading


class Cancelled(Exception):
    pass


class Runner:
    def __init__(self, log_cb=print, progress_cb=None):
        self.log_cb = log_cb
        self.progress_cb = progress_cb
        self.cancelled = False
        self._process = None
        self._lock = threading.Lock()

    def cancel(self):
        self.cancelled = True
        with self._lock:
            if self._process and self._process.poll() is None:
                try:
                    self._process.terminate()
                except OSError:
                    pass

    def _check_cancel(self):
        if self.cancelled:
            raise Cancelled("Opération annulée par l'utilisateur")

    def run(self, cmd: list[str], cwd=None, progress_re=None,
            progress_fn=None) -> None:
        """Lance une commande.

        progress_re : regex avec 2 groupes (courant, total).
        progress_fn : fonction(line) -> pourcentage [0..100] ou None.
        """
        self._check_cancel()
        self.log_cb("$ " + " ".join(str(c) for c in cmd))
        try:
            self._process = subprocess.Popen(
                cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, errors="replace",
            )
        except OSError as exc:
            raise RuntimeError(f"Impossible de lancer {cmd[0]} : {exc}") from exc
        with self._lock:
            proc, self._process = self._process, None
        assert proc is not None
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                self.log_cb(line)
            if self.progress_cb:
                percent = None
                if progress_fn:
                    percent = progress_fn(line)
                elif progress_re:
                    match = progress_re.search(line)
                    if match:
                        try:
                            current, total = float(match.group(1)), float(match.group(2))
                            if total > 0:
                                percent = min(100.0, current / total * 100.0)
                        except ValueError:
                            percent = None
                if percent is not None:
                    self.progress_cb(percent)
            self._check_cancel()
        code = proc.wait()
        self._check_cancel()
        if code != 0:
            raise RuntimeError(f"{cmd[0]} a échoué (code {code})")

    def run_quiet(self, cmd: list[str], timeout=60) -> str:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, errors="replace"
        ).stdout

    @staticmethod
    def rmtree(path: str) -> None:
        import shutil
        shutil.rmtree(path, ignore_errors=True)
