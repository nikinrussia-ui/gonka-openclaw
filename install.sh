#!/bin/bash
# Gonka × OpenClaw — автоустановка
# https://github.com/nikinrussia-ui/gonka-openclaw

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "🤖 Gonka × OpenClaw Installer"
echo "================================"
echo ""

# 1. Проверяем Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ Python3 не найден. Установи: apt install python3${NC}"
    exit 1
fi

# 2. Запрашиваем приватный ключ (НЕ отображается при вводе)
if [ -z "$GONKA_PRIVATE_KEY" ]; then
    echo -e "${YELLOW}Введи SDK приватный ключ с gonka.ai:${NC}"
    echo -e "${CYAN}(ввод скрыт, ключ нигде не сохраняется кроме локального .env)${NC}"
    read -rs GONKA_PRIVATE_KEY
    echo ""
fi

if [ -z "$GONKA_PRIVATE_KEY" ]; then
    echo -e "${RED}❌ Ключ не может быть пустым${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}▶ Устанавливаем gonka-openai SDK...${NC}"
pip install gonka-openai -q

echo -e "${GREEN}▶ Копируем прокси...${NC}"
mkdir -p /root/gonka

# Копируем proxy БЕЗ замены ключа в коде
cp "$(dirname "$0")/gonka_proxy.py" /root/gonka/gonka_proxy.py

# Ключ сохраняем в отдельный .env файл с правами только для root
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
    echo -e "${GREEN}✅ Гонка запущена! Прокси работает на http://127.0.0.1:8001${NC}"
    echo ""
    echo -e "${CYAN}🔒 Безопасность:${NC}"
    echo "   Ключ хранится только в /root/gonka/.env (права 600, только root)"
    echo "   Прокси слушает только 127.0.0.1 — снаружи недоступен"
    echo "   Запросы идут напрямую на node1.gonka.ai — через тебя ничего не проходит"
    echo ""
    echo "Следующий шаг → подключи к LiteLLM:"
    echo "  https://github.com/nikinrussia-ui/gonka-openclaw#шаг-5"
else
    echo -e "${RED}❌ Прокси не ответил. Проверь логи:${NC}"
    echo "  journalctl -u gonka-proxy -n 30"
    exit 1
fi
