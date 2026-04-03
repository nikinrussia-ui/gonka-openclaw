# 🤖 Gonka × OpenClaw

Подключаем [gonka.ai](https://gonka.ai) к [OpenClaw](https://openclaw.ai) — бесплатный **Qwen3-235B** во время тестового периода.

> Gonka — децентрализованная сеть AI-инференса. Каждый запрос криптографически подписан через блокчейн. Никакой централизации, никаких лимитов токенов в тестовом периоде.

---

## Быстрая установка (шаги 1–4)

```bash
git clone https://github.com/nikinrussia-ui/gonka-openclaw
cd gonka-openclaw
chmod +x install.sh
sudo ./install.sh
```

Скрипт спросит твой **SDK приватный ключ** с [gonka.ai](https://gonka.ai) и сам:
- установит `gonka-openai` SDK
- развернёт локальный прокси на `http://127.0.0.1:8001`
- создаст и запустит systemd сервис

---

## Шаг 1 — Получи ключи на gonka.ai

1. Зарегистрируйся на [gonka.ai](https://gonka.ai/developer/quickstart/)
2. Создай аккаунт разработчика — получишь **приватный ключ** (hex-строка) и **адрес кошелька** (`gonka1...`)
3. Пополни баланс AI-токенами через faucet (бесплатно в тестовом периоде)

---

## Шаг 2–4 — Автоматически

```bash
sudo ./install.sh
```

После успеха увидишь:
```
✅ Гонка запущена! Прокси работает на http://127.0.0.1:8001
```

---

## Шаг 5 — Подключи к LiteLLM

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

## Шаг 6 — Подключи к OpenClaw

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
/models             — убедись что GonkaOriginal появился
/model GonkaOriginal — переключись на Гонку
```

---

## Проверка

```bash
# Прокси жив?
curl http://127.0.0.1:8001/v1/models

# Логи
journalctl -u gonka-proxy -f

# Статус сервиса
systemctl status gonka-proxy
```

---

## Требования

- Linux (Ubuntu 20.04+)
- Python 3.10+
- OpenClaw + LiteLLM установлены
- Аккаунт на [gonka.ai](https://gonka.ai)

---

Made with 💜 for [@dairix_ai](https://t.me/dairix_ai)
