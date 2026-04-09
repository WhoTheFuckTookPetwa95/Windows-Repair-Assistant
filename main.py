import ctypes
import os
import queue
import subprocess
import sys
import threading
import time
import pygame

# ----------------------------
# Config
# ----------------------------
APP_TITLE = "Windows Repair Assistant"
WIDTH, HEIGHT = 1120, 720

BG = (14, 17, 23)
PANEL = (20, 24, 31)
PANEL_2 = (27, 33, 43)
BORDER = (44, 52, 66)
TEXT = (242, 245, 248)
MUTED = (168, 177, 190)
ACCENT = (0, 164, 239)
ACCENT_HOVER = (25, 176, 246)
SUCCESS = (61, 220, 151)
WARNING = (255, 189, 89)
ERROR = (255, 101, 101)

FONT_NAME = "segoeui"
MONO_NAME = "consolas"

DISM_CMD = ["DISM", "/Online", "/Cleanup-Image", "/RestoreHealth"]
SFC_CMD = ["sfc", "/scannow"]

# ----------------------------
# Admin helpers
# ----------------------------
def is_windows():
    return os.name == "nt"

def is_admin():
    if not is_windows():
        return False
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def relaunch_as_admin():
    params = subprocess.list2cmdline(sys.argv)
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )

# ----------------------------
# UI helpers
# ----------------------------
def make_font(name, size, bold=False):
    return pygame.font.SysFont(name, size, bold=bold)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

# ----------------------------
# Button
# ----------------------------
class Button:
    def __init__(self, rect, text, callback):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.enabled = True
        self.hover = False

    def handle(self, event):
        if not self.enabled:
            return
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()

    def draw(self, surf, font):
        color = ACCENT_HOVER if self.hover else ACCENT
        if not self.enabled:
            color = (70, 70, 70)

        pygame.draw.rect(surf, color, self.rect, border_radius=10)
        txt = font.render(self.text, True, TEXT)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

# ----------------------------
# App
# ----------------------------
class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(APP_TITLE)
        self.clock = pygame.time.Clock()

        self.font = make_font(FONT_NAME, 18)
        self.mono = make_font(MONO_NAME, 14)

        self.running = True
        self.queue = queue.Queue()

        self.logs = []
        self.status = "Ready"
        self.progress = 0

        self.button = Button((40, HEIGHT - 60, 200, 40), "Start Repair", self.start)

    def log(self, text):
        self.logs.append(text)

    def worker(self):
        steps = [
            ("Running DISM...", DISM_CMD),
            ("Running SFC...", SFC_CMD)
        ]

        for i, (label, cmd) in enumerate(steps):
            self.queue.put(("status", label))
            self.queue.put(("log", f"> {' '.join(cmd)}"))

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            for line in proc.stdout:
                self.queue.put(("log", line.strip()))

            proc.wait()
            self.queue.put(("progress", (i + 1) / len(steps)))

        self.queue.put(("status", "Done"))
        self.queue.put(("done",))

    def start(self):
        self.button.enabled = False
        threading.Thread(target=self.worker, daemon=True).start()

    def update(self):
        while not self.queue.empty():
            kind, *data = self.queue.get()
            if kind == "log":
                self.log(data[0])
            elif kind == "status":
                self.status = data[0]
            elif kind == "progress":
                self.progress = data[0]
            elif kind == "done":
                self.button.enabled = True

    def draw(self):
        self.screen.fill(BG)

        # Title
        title = self.font.render("Windows Repair Assistant", True, TEXT)
        self.screen.blit(title, (40, 30))

        # Status
        status = self.font.render(f"Status: {self.status}", True, MUTED)
        self.screen.blit(status, (40, 70))

        # Progress bar
        bar = pygame.Rect(40, 100, 400, 20)
        pygame.draw.rect(self.screen, PANEL, bar)
        pygame.draw.rect(self.screen, ACCENT, (bar.x, bar.y, int(bar.w * self.progress), bar.h))

        # Logs
        y = 140
        for line in self.logs[-20:]:
            txt = self.mono.render(line, True, TEXT)
            self.screen.blit(txt, (40, y))
            y += 18

        self.button.draw(self.screen, self.font)

        pygame.display.flip()

    def run(self):
        while self.running:
            self.clock.tick(60)
            self.update()

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                self.button.handle(e)

            self.draw()

        pygame.quit()

# ----------------------------
# Entry
# ----------------------------
def main():
    if is_windows() and not is_admin():
        relaunch_as_admin()
        return

    app = App()
    app.run()

if __name__ == "__main__":
    main()
