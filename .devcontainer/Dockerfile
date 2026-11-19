FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    xvfb x11vnc xfce4 xfce4-terminal dbus-x11 sudo novnc websockify \
    firefox python3 python3-pip python3-venv git gh curl wget htop net-tools \
    nodejs npm build-essential ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/vscode/.echocloud /workspace-persist
RUN chown -R vscode:vscode /home/vscode/.echocloud /workspace-persist
