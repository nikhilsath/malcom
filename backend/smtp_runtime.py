from __future__ import annotations

import logging
import itertools
import socketserver
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from email import policy
from email.parser import Parser


MAX_RECENT_MESSAGES = 25


def normalize_email_address(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized.startswith("<") and normalized.endswith(">"):
        normalized = normalized[1:-1]
    normalized = normalized.strip().lower()
    return normalized or None


def build_message_preview(message_data: str, *, max_characters: int = 500) -> str | None:
    stripped = "\n".join(line.rstrip() for line in message_data.splitlines()).strip()
    if not stripped:
        return None
    if len(stripped) <= max_characters:
        return stripped
    return f"{stripped[:max_characters]}..."


def extract_message_subject(message_data: str) -> str | None:
    try:
        parsed_message = Parser(policy=policy.default).parsestr(message_data, headersonly=True)
    except Exception:
        return None
    subject = parsed_message.get("subject")
    if subject is None:
        return None
    normalized = str(subject).strip()
    return normalized or None


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class SmtpMachineAssignment:
    worker_id: str
    name: str
    hostname: str
    address: str
    status: str
    is_local: bool
    capabilities: tuple[str, ...]


class ManagedSmtpServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], manager: "SmtpRuntimeManager") -> None:
        self.manager = manager
        super().__init__(server_address, SmtpSessionHandler)


class SmtpSessionHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        self.server.manager.record_session()  # type: ignore[attr-defined]
        self._write_line("220 Malcom SMTP ready")
        mail_from: str | None = None
        recipients: list[str] = []

        while True:
            raw_line = self.rfile.readline(65537)
            if not raw_line:
                return

            try:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            except Exception:
                self._write_line("500 Unable to decode input")
                continue

            if not line:
                self._write_line("500 Empty command")
                continue

            verb, _, remainder = line.partition(" ")
            command = verb.upper()
            argument = remainder.strip()

            if command in {"EHLO", "HELO"}:
                self._write_line("250-malcom")
                self._write_line("250 SIZE 10485760")
                continue

            if command == "NOOP":
                self._write_line("250 OK")
                continue

            if command == "RSET":
                mail_from = None
                recipients = []
                self._write_line("250 OK")
                continue

            if command == "QUIT":
                self._write_line("221 Bye")
                return

            if command == "MAIL" and argument.upper().startswith("FROM:"):
                mail_from = argument[5:].strip().split(" ", 1)[0]
                recipients = []
                self._write_line("250 Sender accepted")
                continue

            if command == "RCPT" and argument.upper().startswith("TO:"):
                if mail_from is None:
                    self._write_line("503 MAIL required before RCPT")
                    continue
                recipient = argument[3:].strip().split(" ", 1)[0]
                if not self.server.manager.accepts_recipient(recipient):  # type: ignore[attr-defined]
                    self._write_line("550 Recipient not configured")
                    continue
                recipients.append(recipient)
                self._write_line("250 Recipient accepted")
                continue

            if command == "DATA":
                if mail_from is None or not recipients:
                    self._write_line("503 MAIL and RCPT required before DATA")
                    continue

                self._write_line("354 End data with <CR><LF>.<CR><LF>")
                message_lines: list[str] = []

                while True:
                    raw_message_line = self.rfile.readline(65537)
                    if not raw_message_line:
                        return

                    decoded_line = raw_message_line.decode("utf-8", errors="replace").rstrip("\r\n")
                    if decoded_line == ".":
                        break
                    if decoded_line.startswith(".."):
                        decoded_line = decoded_line[1:]
                    message_lines.append(decoded_line)

                peer_host, peer_port = self.client_address[:2]
                self.server.manager.record_message(  # type: ignore[attr-defined]
                    mail_from=mail_from,
                    recipients=recipients,
                    message_data="\n".join(message_lines),
                    peer=f"{peer_host}:{peer_port}",
                )
                mail_from = None
                recipients = []
                self._write_line("250 Message accepted")
                continue

            self._write_line("502 Command not implemented")

    def _write_line(self, value: str) -> None:
        self.wfile.write(f"{value}\r\n".encode("utf-8"))


class SmtpRuntimeManager:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger
        self._lock = threading.Lock()
        self._server: ManagedSmtpServer | None = None
        self._thread: threading.Thread | None = None
        self._status = "stopped"
        self._message = "SMTP server is stopped."
        self._listening_host: str | None = None
        self._listening_port: int | None = None
        self._selected_machine_id: str | None = None
        self._selected_machine_name: str | None = None
        self._last_started_at: str | None = None
        self._last_stopped_at: str | None = None
        self._last_error: str | None = None
        self._session_count = 0
        self._message_count = 0
        self._last_message_at: str | None = None
        self._last_mail_from: str | None = None
        self._last_recipient: str | None = None
        self._configured_recipient_email: str | None = None
        self._recent_messages: list[dict[str, object]] = []
        self._message_sequence = itertools.count(1)

    def sync(
        self,
        *,
        enabled: bool,
        bind_host: str,
        port: int,
        recipient_email: str | None,
        machine: SmtpMachineAssignment | None,
    ) -> None:
        normalized_recipient_email = normalize_email_address(recipient_email)
        with self._lock:
            self._configured_recipient_email = normalized_recipient_email

        if not enabled:
            self.stop()
            return

        if machine is None:
            self.stop()
            with self._lock:
                self._status = "error"
                self._message = "Selected machine is unavailable."
                self._last_error = "Selected machine is unavailable."
            return

        if not machine.is_local:
            self.stop()
            with self._lock:
                self._status = "assigned"
                self._message = f"Assigned to {machine.name}. Remote SMTP execution is not wired yet."
                self._selected_machine_id = machine.worker_id
                self._selected_machine_name = machine.name
                self._last_error = None
            return

        with self._lock:
            restart_required = (
                self._server is None
                or self._listening_host != bind_host
                or self._listening_port != port
            )

        if restart_required:
            self._start_local(bind_host=bind_host, port=port, machine=machine)
            return

        with self._lock:
            self._status = "running"
            self._message = f"SMTP server is running on {bind_host}:{port}."
            self._selected_machine_id = machine.worker_id
            self._selected_machine_name = machine.name
            self._last_error = None

    def accepts_recipient(self, recipient: str) -> bool:
        normalized_recipient = normalize_email_address(recipient)
        with self._lock:
            configured_recipient = self._configured_recipient_email
        return configured_recipient is None or configured_recipient == normalized_recipient

    def stop(self) -> None:
        with self._lock:
            server = self._server
            thread = self._thread
            was_active = server is not None
            self._server = None
            self._thread = None
            self._listening_host = None
            self._listening_port = None
            self._status = "stopped"
            self._message = "SMTP server is stopped."
            self._selected_machine_id = None
            self._selected_machine_name = None
            self._last_error = None
            if was_active:
                self._last_stopped_at = utc_now_iso()

        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)

    def shutdown(self) -> None:
        self.stop()

    def record_session(self) -> None:
        with self._lock:
            self._session_count += 1

    def record_message(self, *, mail_from: str, recipients: list[str], message_data: str, peer: str) -> None:
        received_at = utc_now_iso()
        subject = extract_message_subject(message_data)
        body_preview = build_message_preview(message_data)
        message_id = f"smtp_{next(self._message_sequence)}"
        with self._lock:
            self._message_count += 1
            self._last_message_at = received_at
            self._last_mail_from = mail_from
            self._last_recipient = recipients[0] if recipients else None
            self._recent_messages.insert(
                0,
                {
                    "id": message_id,
                    "received_at": received_at,
                    "mail_from": mail_from,
                    "recipients": list(recipients),
                    "peer": peer,
                    "size_bytes": len(message_data.encode("utf-8")),
                    "subject": subject,
                    "body_preview": body_preview,
                },
            )
            self._recent_messages = self._recent_messages[:MAX_RECENT_MESSAGES]

        if self._logger is not None:
            self._logger.info(
                '{"event": "smtp_message_received", "mail_from": "%s", "recipient_count": %d, "peer": "%s", "size_bytes": %d, "subject": "%s"}',
                mail_from,
                len(recipients),
                peer,
                len(message_data.encode("utf-8")),
                subject or "",
            )

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "status": self._status,
                "message": self._message,
                "listening_host": self._listening_host,
                "listening_port": self._listening_port,
                "selected_machine_id": self._selected_machine_id,
                "selected_machine_name": self._selected_machine_name,
                "last_started_at": self._last_started_at,
                "last_stopped_at": self._last_stopped_at,
                "last_error": self._last_error,
                "session_count": self._session_count,
                "message_count": self._message_count,
                "last_message_at": self._last_message_at,
                "last_mail_from": self._last_mail_from,
                "last_recipient": self._last_recipient,
                "recent_messages": [dict(message) for message in self._recent_messages],
            }

    def _start_local(self, *, bind_host: str, port: int, machine: SmtpMachineAssignment) -> None:
        self.stop()

        try:
            server = ManagedSmtpServer((bind_host, port), self)
        except OSError as exc:
            with self._lock:
                self._status = "error"
                self._message = f"Unable to start SMTP server on {bind_host}:{port}."
                self._last_error = str(exc)
                self._selected_machine_id = machine.worker_id
                self._selected_machine_name = machine.name
            return

        actual_host, actual_port = server.server_address[:2]
        thread = threading.Thread(target=server.serve_forever, name="malcom-smtp-server", daemon=True)
        thread.start()

        with self._lock:
            self._server = server
            self._thread = thread
            self._status = "running"
            self._message = f"SMTP server is running on {actual_host}:{actual_port}."
            self._listening_host = str(actual_host)
            self._listening_port = int(actual_port)
            self._selected_machine_id = machine.worker_id
            self._selected_machine_name = machine.name
            self._last_started_at = utc_now_iso()
            self._last_error = None
