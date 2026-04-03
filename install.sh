#!/bin/bash
# Gonka x OpenClaw — автоустановка
# Разработано каналом @dairix_ai — t.me/dairix_ai

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}🤖 Gonka x OpenClaw Installer${NC}"
echo -e "${CYAN}   Разработано каналом @dairix_ai | t.me/dairix_ai${NC}"
echo ""

# 1. Проверяем зависимости
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ Python3 не найден. Установи: apt install python3${NC}"
    exit 1
fi

if ! command -v curl &>/dev/null; then
    echo -e "${RED}❌ curl не найден. Установи: apt install curl${NC}"
    exit 1
fi

PIP=$(command -v pip3 2>/dev/null || command -v pip 2>/dev/null || true)
if [ -z "$PIP" ]; then
    echo -e "${RED}❌ pip не найден. Установи: apt install python3-pip${NC}"
    exit 1
fi

# 2. Запрашиваем приватный ключ (ввод с терминала, скрыт)
if [ -z "$GONKA_PRIVATE_KEY" ]; then
    echo -e "${YELLOW}Введи SDK приватный ключ с gonka.ai:${NC}"
    echo -e "${CYAN}(ввод скрыт — ключ сохранится только локально в /root/gonka/.env)${NC}"
    read -rs GONKA_PRIVATE_KEY < /dev/tty
    echo ""
fi

if [ -z "$GONKA_PRIVATE_KEY" ]; then
    echo -e "${RED}❌ Ключ не может быть пустым${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}▶ Устанавливаем gonka-openai SDK...${NC}"
$PIP install gonka-openai -q

echo -e "${GREEN}▶ Скачиваем прокси...${NC}"
mkdir -p /root/gonka
curl -fsSL https://raw.githubusercontent.com/nikinrussia-ui/gonka-openclaw/main/gonka_proxy.py \
    -o /root/gonka/gonka_proxy.py

# Ключ сохраняем в .env с правами только для root
cat > /root/gonka/.env << ENVEOF
GONKA_PRIVATE_KEY=${GONKA_PRIVATE_KEY}
ENVEOF
chmod 600 /root/gonka/.env

echo -e "${GREEN}▶ Создаём systemd сервис...${NC}"
cat > /etc/systemd/system/gonka-proxy.service << 'EOF'
[Unit]
Description=Gonka Local Proxy (signed OpenAI-compat API)
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/gonka
EnvironmentFile=/root/gonka/.env
ExecStart=/usr/bin/python3 /root/gonka/gonka_proxy.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now gonka-proxy

echo ""
echo -e "${GREEN}▶ Проверяем запуск...${NC}"
sleep 2

if curl -s http://127.0.0.1:8001/v1/models | grep -q "Qwen"; then
    echo ""
    echo -e "${GREEN}✅ Готово! Прокси работает на http://127.0.0.1:8001${NC}"
    echo ""
    echo -e "${CYAN}🔒 Безопасность:${NC}"
    echo "   Ключ хранится только в /root/gonka/.env (права 600, только root)"
    echo "   Прокси слушает только 127.0.0.1 — снаружи недоступен"
    echo "   Запросы идут напрямую на node1.gonka.ai — через тебя ничего не проходит"
    echo ""
    echo -e "${CYAN}📱 Следующие шаги — читай в Telegram-канале:${NC}"
    echo ""
    echo -e "   ${YELLOW}👉 t.me/dairix_ai${NC}"
    echo ""
    echo "   Там найдёшь:"
    echo "   • Где получить бесплатные токены GNK"
    echo "   • Как подключить Гонку к LiteLLM и OpenClaw"
    echo "   • Обновления и новые инструкции"
    echo ""
else
    echo -e "${RED}❌ Прокси не ответил. Проверь логи:${NC}"
    echo "   journalctl -u gonka-proxy -n 30"
    exit 1
fi
