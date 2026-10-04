[app]
title = OfflineTube
package.name = offlinetube
package.domain = org.offlinetube

source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0

# ffpyplayer = backend de vídeo do Kivy no Android (kivy.uix.video)
requirements = python3,kivy==2.3.0,ffpyplayer,pyjnius,android

icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/icon.png
android.presplash_color = #F9C80E

orientation = portrait,landscape
fullscreen = 0

# Permissões declaradas no manifest (o main.py pede em tempo de execução)
android.permissions = android.permission.READ_EXTERNAL_STORAGE,android.permission.READ_MEDIA_VIDEO

android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True

# 32 bits (armeabi-v7a) + 64 bits (arm64-v8a) no MESMO APK
android.archs = arm64-v8a, armeabi-v7a

# Versão estável do python-for-android (casa com NDK 25b, Kivy 2.3.0 e ffpyplayer)
p4a.branch = v2024.01.21

android.allow_backup = True
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
