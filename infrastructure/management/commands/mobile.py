"""python manage.py mobile   (or: make mobile)

Serves the web mirror through a temporary https link (free ssh tunnel from localhost.run) and prints a QR code
to open it with your phone's camera. The browser camera only works over https, hence the tunnel.
"""
import re
import subprocess
import sys
import time

from django.core.management.base import BaseCommand

URL = re.compile(r"https://[a-z0-9-]+\.lhr\.life")


class Command(BaseCommand):
    help = "Web mirror on your phone: https tunnel + QR code (Ctrl+C to stop)."

    def add_arguments(self, parser):
        parser.add_argument("--port", type=int, default=8010)
        parser.add_argument("--no-debug", dest="debug", action="store_false", help="Without the diagnostics panel")

    def handle(self, *args, **options):
        port = options["port"]
        server = subprocess.Popen([sys.executable, "manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        tunnel = None
        try:
            time.sleep(1.5)
            self.stdout.write("Opening the tunnel… (takes a few seconds)")
            tunnel = subprocess.Popen(["ssh", "-T", "-o", "StrictHostKeyChecking=accept-new", "-o", "ServerAliveInterval=30",
                                       "-R", f"80:127.0.0.1:{port}", "nokey@localhost.run"],
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            shown = False
            for line in tunnel.stdout:
                m = URL.search(line)
                if m and not shown:
                    shown = True
                    self.show(m.group(0) + ("/?debug" if options["debug"] else "/"))
                elif any(w in line.lower() for w in ("failed", "error", "timeout")):
                    self.stdout.write(f"  warning: {line.strip()}")
        except KeyboardInterrupt:
            pass
        finally:
            for p in (tunnel, server):
                if p and p.poll() is None:
                    p.terminate()

    def show(self, url):
        bar = "=" * 58
        self.stdout.write(f"\n{bar}\n  SCAN THIS QR CODE WITH YOUR PHONE'S CAMERA:\n  {url}\n{bar}")
        try:
            import qrcode

            q = qrcode.QRCode(border=2)
            q.add_data(url)
            q.make()
            q.print_ascii(invert=True)
        except ImportError:
            self.stdout.write("(Install qrcode to see the QR code: make install)")
        self.stdout.write("(Keep this window open while testing. Ctrl+C to stop.)")
