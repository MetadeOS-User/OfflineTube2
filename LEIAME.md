# OfflineTube – build Android (32 e 64 bits)

O `buildozer.spec` já está configurado com `android.archs = arm64-v8a, armeabi-v7a`,
gerando **um único APK** que roda em aparelhos de 32 e de 64 bits.

## Opção A – GitHub Actions (sem instalar nada)
1. Crie um repositório no GitHub e envie todos os arquivos desta pasta (inclusive `.github/`).
2. Aba **Actions → Build OfflineTube APK** (roda sozinho a cada push).
3. Ao terminar (~30-60 min na 1ª vez), baixe o APK em **Artifacts → OfflineTube-apk**.

## Opção B – Linux / WSL2 (Ubuntu 22.04)
```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool \
  pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake \
  libffi-dev libssl-dev automake ccache
pip install --user --upgrade buildozer "cython<3" virtualenv
cd OfflineTube
buildozer -v android debug
```
O APK sai em `bin/offlinetube-1.0-arm64-v8a_armeabi-v7a-debug.apk`.

Instalar no celular: `buildozer android deploy run` (USB com depuração ativada)
ou copie o APK e instale manualmente.
