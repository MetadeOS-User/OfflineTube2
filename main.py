# OfflineTube - player de vídeos offline (Kivy)
import os
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.button import Button
from kivy.uix.recycleview import RecycleView
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.video import Video  # noqa: F401  (usado no KV abaixo)
from kivy.utils import platform

# Extensões aceitas e pastas ignoradas na busca
VIDEO_EXTS = (".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4v", ".3gp")
SKIP_DIRS = {"android", "lost.dir"}
MAX_DEPTH = 5  # quantos níveis de subpastas entrar

COLOR_ACTIVE = (0.98, 0.78, 0.05, 1)
COLOR_NORMAL = (1, 1, 1, 1)


# ----------------------------------------------------------------------
# Busca de vídeos
# ----------------------------------------------------------------------
def get_roots():
    """Retorna as pastas-raiz onde procurar (armazenamento interno e cartão SD)."""
    roots = []
    if platform == "android":
        try:
            from android.storage import (
                primary_external_storage_path,
                secondary_external_storage_path,
            )
            roots.append(primary_external_storage_path())
            roots.append(secondary_external_storage_path())
        except Exception:
            pass
        roots += ["/storage/emulated/0", "/sdcard"]
        try:
            for name in sorted(os.listdir("/storage")):
                if name not in ("self", "emulated"):
                    roots.append(os.path.join("/storage", name))
        except OSError:
            pass
    else:  # computador (para testes)
        home = os.path.expanduser("~")
        for n in ("Videos", "Vídeos", "Movies", "Downloads", "Download"):
            roots.append(os.path.join(home, n))

    result, seen = [], set()
    for r in roots:
        if not r or not os.path.isdir(r):
            continue
        real = os.path.realpath(r)  # evita repetir /sdcard == /storage/emulated/0
        if real not in seen:
            seen.add(real)
            result.append(r)
    return result


def find_videos(roots):
    """Procura vídeos nas raízes (com subpastas). Separa em 'long' e 'short'.

    - nome terminando em _short  -> Curtos   (ex.: piada_short.mp4)
    - qualquer outro vídeo       -> Longos   (ex.: aula_long.mp4, filme.mkv)
    """
    found = {"long": [], "short": []}
    seen = set()
    for root in roots:
        base = root.rstrip(os.sep).count(os.sep)
        for dirpath, dirnames, filenames in os.walk(root):
            depth = dirpath.rstrip(os.sep).count(os.sep) - base
            if depth >= MAX_DEPTH:
                dirnames[:] = []
            else:
                dirnames[:] = [
                    d for d in dirnames
                    if not d.startswith(".") and d.lower() not in SKIP_DIRS
                ]
            for f in filenames:
                name, ext = os.path.splitext(f)
                if f.startswith(".") or ext.lower() not in VIDEO_EXTS:
                    continue
                path = os.path.join(dirpath, f)
                real = os.path.realpath(path)
                if real in seen:
                    continue
                seen.add(real)
                low = name.lower()
                if low.endswith("_short"):
                    kind, title = "short", name[:-6]
                elif low.endswith("_long"):
                    kind, title = "long", name[:-5]
                else:
                    kind, title = "long", name
                found[kind].append({"text": title or name, "path": path})
    for kind in found:
        found[kind].sort(key=lambda d: d["text"].lower())
    return found


def permission_status():
    """Texto com o estado da permissão (só para ajudar a diagnosticar)."""
    if platform != "android":
        return None
    try:
        from jnius import autoclass
        sdk = autoclass("android.os.Build$VERSION").SDK_INT
        if sdk < 23:
            return "concedida na instalação"
        from android.permissions import check_permission
        perm = ("android.permission.READ_MEDIA_VIDEO" if sdk >= 33
                else "android.permission.READ_EXTERNAL_STORAGE")
        return "concedida" if check_permission(perm) else "NEGADA"
    except Exception:
        return "desconhecida"


# ----------------------------------------------------------------------
# Interface (KV)
# ----------------------------------------------------------------------
KV = """
<VideoButton>:
    size_hint_y: None
    height: dp(56)
    halign: "left"
    valign: "middle"
    padding_x: dp(14)
    shorten: True
    shorten_from: "right"
    text_size: self.width - dp(28), self.height

<VideoList>:
    viewclass: "VideoButton"
    # O RecycleView PRECISA de um layout manager, senão nenhum item aparece
    RecycleBoxLayout:
        orientation: "vertical"
        size_hint_y: None
        height: self.minimum_height
        default_size: None, dp(56)
        default_size_hint: 1, None
        spacing: dp(2)

<Home>:
    BoxLayout:
        orientation: "vertical"
        FloatLayout:
            VideoList:
                id: rv
                # FloatLayout só posiciona filhos que tenham pos_hint
                pos_hint: {"x": 0, "y": 0}
            Label:
                id: status
                text: ""
                halign: "center"
                size_hint: 1, None
                pos_hint: {"center_x": .5, "center_y": .5}
                text_size: self.width - dp(32), None
                height: self.texture_size[1]
        BoxLayout:
            size_hint_y: None
            height: dp(56)
            Button:
                id: b_long
                text: "Longos"
                on_release: root.set_mode("long")
            Button:
                id: b_short
                text: "Curtos"
                on_release: root.set_mode("short")
            Button:
                text: "Atualizar"
                on_release: root.reload()

<Player>:
    BoxLayout:
        orientation: "vertical"
        Video:
            id: video
            state: "stop"
            options: {"eos": "stop"}
        BoxLayout:
            size_hint_y: None
            height: dp(56)
            Button:
                text: "Voltar"
                on_release: app.go_home()
            Button:
                text: "Pausar" if video.state == "play" else "Continuar"
                on_release: root.toggle()
"""
Builder.load_string(KV)


class VideoButton(Button):
    path = StringProperty("")

    def on_release(self):
        App.get_running_app().open_video(self.path)


class VideoList(RecycleView):
    pass


class Home(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.mode = "long"
        self.videos = {"long": [], "short": []}
        self.roots = []
        self.perm = None
        self.error = None
        self.scanning = False
        self.refresh_view()

    def reload(self):
        """Procura os vídeos em segundo plano (não trava a tela)."""
        if self.scanning:
            return
        self.scanning = True
        self.ids.status.text = "Procurando vídeos..."
        threading.Thread(target=self._scan, daemon=True).start()

    def _scan(self):
        roots, found, error = [], {"long": [], "short": []}, None
        try:
            roots = get_roots()
            found = find_videos(roots)
        except Exception as e:  # mostra o erro na tela em vez de falhar calado
            error = "%s: %s" % (type(e).__name__, e)
        perm = permission_status()
        Clock.schedule_once(lambda dt: self._done(roots, found, perm, error), 0)

    def _done(self, roots, found, perm, error):
        self.roots, self.videos, self.perm, self.error = roots, found, perm, error
        self.scanning = False
        self.refresh_view()

    def set_mode(self, mode):
        self.mode = mode
        self.refresh_view()

    def refresh_view(self):
        items = self.videos[self.mode]
        self.ids.rv.data = [dict(i) for i in items]
        self.ids.b_long.background_color = COLOR_ACTIVE if self.mode == "long" else COLOR_NORMAL
        self.ids.b_short.background_color = COLOR_ACTIVE if self.mode == "short" else COLOR_NORMAL
        if items:
            self.ids.status.text = ""
            return
        if self.scanning:
            self.ids.status.text = "Procurando vídeos..."
            return
        if self.mode == "short":
            msg = ("Nenhum vídeo curto.\nPara aparecer aqui, o nome do arquivo "
                   "deve terminar com _short (ex.: piada_short.mp4).")
        else:
            msg = "Nenhum vídeo encontrado.\nCopie arquivos .mp4 para Movies, Download ou DCIM."
        if self.error:
            msg += "\n\nErro na busca: " + self.error
        if self.perm:
            msg += "\n\nPermissão de leitura: " + self.perm
        msg += "\n\nPastas verificadas:\n" + ("\n".join(self.roots) or "(nenhuma encontrada)")
        self.ids.status.text = msg


class Player(Screen):
    def load(self, path):
        video = self.ids.video
        video.source = path
        video.state = "play"

    def toggle(self):
        video = self.ids.video
        video.state = "pause" if video.state == "play" else "play"

    def stop(self):
        self.ids.video.state = "stop"


class OfflineTube(App):
    def build(self):
        from kivy.core.window import Window
        self.sm = ScreenManager()
        self.home = Home(name="home")
        self.player = Player(name="player")
        self.sm.add_widget(self.home)
        self.sm.add_widget(self.player)
        Window.bind(on_keyboard=self.on_keyboard)
        return self.sm

    # --- navegação -----------------------------------------------------
    def open_video(self, path):
        self.player.load(path)
        self.sm.current = "player"

    def go_home(self):
        self.player.stop()  # sem isso o vídeo continuava tocando ao voltar
        self.sm.current = "home"

    def on_keyboard(self, window, key, *args):
        # Botão "voltar" do Android (código 27): volta à lista em vez de fechar o app
        if key == 27 and self.sm.current == "player":
            self.go_home()
            return True
        return False

    # --- ciclo de vida / permissões ---------------------------------------
    def on_start(self):
        if platform != "android":
            self.home.reload()
            return
        try:
            from jnius import autoclass
            sdk = autoclass("android.os.Build$VERSION").SDK_INT
            if sdk < 23:  # Android 5.x: permissão já vem concedida na instalação
                self.home.reload()
                return
            from android.permissions import request_permissions
            perm = ("android.permission.READ_MEDIA_VIDEO" if sdk >= 33
                    else "android.permission.READ_EXTERNAL_STORAGE")
            request_permissions([perm], self._on_permissions)
        except Exception:
            self.home.reload()

    def _on_permissions(self, permissions, grants):
        Clock.schedule_once(lambda dt: self.home.reload(), 0)

    def on_pause(self):
        if self.player.ids.video.state == "play":
            self.player.ids.video.state = "pause"
        return True

    def on_resume(self):
        self.home.reload()


if __name__ == "__main__":
    OfflineTube().run()
