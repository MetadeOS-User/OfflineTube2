
# OfflineTube - exemplo simplificado em um único arquivo
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.button import Button
from kivy.uix.video import Video
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen
import os

# Android: request permission to read videos from shared storage.
# This is ignored on desktop builds.
try:
    from android.permissions import request_permissions
    from jnius import autoclass
except ImportError:
    request_permissions = None
    autoclass = None

SEARCH_DIRS=[
"/storage/emulated/0/Vídeos",
"/storage/emulated/0/Movies",
]

class VideoList(RecycleView):
    def __init__(self, mode="long", callback=None, **kwargs):
        super().__init__(**kwargs)
        self.viewclass="Button"
        self.callback=callback
        self.mode=mode
        self.refresh()
    def refresh(self):
        suf="_long.mp4" if self.mode=="long" else "_short.mp4"
        data=[]
        for d in SEARCH_DIRS:
            if os.path.isdir(d):
                for f in sorted(os.listdir(d)):
                    if f.endswith(suf):
                        p=os.path.join(d,f)
                        data.append({"text":f[:-len(suf)],"on_release":lambda p=p:self.callback(p)})
        self.data=data

class Home(Screen):
    def __init__(self, sm, **kw):
        super().__init__(**kw)
        self.sm=sm
        self.mode="long"
        self.rootbox=BoxLayout(orientation="vertical")
        self.rv=VideoList("long", self.open_video)
        self.rootbox.add_widget(self.rv)
        nav=BoxLayout(size_hint_y=.1)
        b1=Button(text="Longos")
        b2=Button(text="Curtos")
        b1.bind(on_release=lambda *_:self.switch("long"))
        b2.bind(on_release=lambda *_:self.switch("short"))
        nav.add_widget(b1);nav.add_widget(b2)
        self.rootbox.add_widget(nav)
        self.add_widget(self.rootbox)
    def switch(self,m):
        self.rootbox.remove_widget(self.rv)
        self.rv=VideoList(m,self.open_video)
        self.rootbox.add_widget(self.rv,index=1)
    def open_video(self,path):
        self.sm.player.load(path)
        self.sm.current="player"

class Player(Screen):
    def __init__(self, sm, **kw):
        super().__init__(**kw)
        box=BoxLayout(orientation="vertical")
        self.video=Video(state="stop",options={"eos":"stop"})
        back=Button(text="Voltar",size_hint_y=.1)
        back.bind(on_release=lambda *_: setattr(sm,"current","home"))
        box.add_widget(self.video)
        box.add_widget(back)
        self.add_widget(box)
    def load(self,path):
        self.video.source=path
        self.video.state="play"

class SM(ScreenManager):
    def __init__(self,**kw):
        super().__init__(**kw)
        self.player=Player(self,name="player")
        self.home=Home(self,name="home")
        self.add_widget(self.home)
        self.add_widget(self.player)

class OfflineTube(App):
    def build(self):
        return SM()

    def on_start(self):
        if request_permissions is None or autoclass is None:
            return
        try:
            Build = autoclass("android.os.Build")
            if Build.VERSION.SDK_INT >= 33:
                request_permissions(["android.permission.READ_MEDIA_VIDEO"])
            else:
                request_permissions(["android.permission.READ_EXTERNAL_STORAGE"])
        except Exception:
            pass

if __name__=="__main__":
    OfflineTube().run()
