# 🤖 Gonka × OpenClaw

Подключаем [gonka.ai](https://gonka.ai) к [OpenClaw](https://openclaw.ai) — бесплатный **Qwen3-235B** во время тестового периода.

## Что это и зачем

[Gonka](https://gonka.ai) — децентрализованная сеть AI-инференса. Каждый запрос криптографически подписан через блокчейн, без централизованного сервера. Во время тестового периода токены **бесплатны и безлимитны**.

Этот репозиторий содержит:
- `gonka_proxy.py` — локальный прокси-сервер, который принимает запросы от OpenClaw/LiteLLM в стандартном OpenAI-формате и передаёт их в сеть Gonka
- `install.sh` — скрипт автоматической установки (устанавливает SDK, прокси, systemd-сервис)

## Открытый код — можешь проверить сам

Весь код открыт. Перед установкой можешь посмотреть что именно будет запущено:

- [`install.sh`](https://github.com/nikinrussia-ui/gonka-openclaw/blob/main/install.sh) — скрипт установки
- [`gonka_proxy.py`](https://github.com/nikinrussia-ui/gonka-openclaw/blob/main/gonka_proxy.py) — прокси-сервер

Приватный ключ вводится скрыто, сохраняется **только локально** в `/root/gonka/.env` с правами `600` (только root). В интернет не отправляется и в коде нигде не появляется.

---

## Быстрая установка — одна команда

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/nikinrussia-ui/gonka-openclaw/main/install.sh)
```

Скрипт спросит **SDK приватный ключ** с [gonka.ai](https://gonka.ai) и сам:
- установит `gonka-openai` SDK
- скачает и запустит локальный прокси на `http://127.0.0.1:8001`
- создаст и включит systemd-сервис

---

## Шаг 1 — Получи ключи на gonka.ai

1. Зарегистрируйся на [gonka.ai](https://gonka.ai/developer/quickstart/)
2. Создай аккаунт разработчика — получишь **приватный ключ** (hex-строка) и **адрес кошелька** (`gonka1...`)
3. Пополни баланс AI-токенами через faucet (бесплатно в тестовом периоде)

Где получить бесплатные токены GNK и полная инструкция по подключению — в Telegram-канале **[t.me/dairix_ai](https://t.me/dairix_ai)**

---

## Шаг 2 — Установка

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/nikinrussia-ui/gonka-openclaw/main/install.sh)
```

После успеха увидишь:
```
✅ Готово! Прокси работает на http://127.0.0.1:8001
```

---

## Шаг 3 — Подключи к LiteLLM

В `~/litellm/config.yaml` добавь в секцию `model_list`:

```yaml
- model_name: GonkaOriginal
  litellm_params:
    model: openai/Qwen/Qwen3-235B-A22B-Instruct-2507-FP8
    api_base: http://127.0.0.1:8001/v1
    api_key: gonka-direct
    timeout: 300
    stream_timeout: 300
  model_info:
    supports_function_calling: true
```

```bash
systemctl restart litellm
```

---

## Шаг 4 — Подключи к OpenClaw

В `~/.openclaw/openclaw.json` в секцию `models.providers.litellm.models` добавь:

```json
{
  "id": "GonkaOriginal",
  "name": "Gonka Qwen3-235B"
}
```

```bash
openclaw gateway config.apply --file ~/.openclaw/openclaw.json
```

В чате с агентом:
```
/models              — убедись что GonkaOriginal появился
/model GonkaOriginal — переключись на Гонку
```

---

## Проверка и диагностика

```bash
# Прокси жив?
curl http://127.0.0.1:8001/v1/models

# Логи в реальном времени
journalctl -u gonka-proxy -f

# Статус сервиса
systemctl status gonka-proxy
```

---

## Требования

- Linux (Ubuntu 20.04+)
- Python 3.10+
- `curl`, `pip3`
- OpenClaw + LiteLLM установлены
- Аккаунт на [gonka.ai](https://gonka.ai)

---

Made with 💜 by [@dairix_ai](https://t.me/dairix_ai)
