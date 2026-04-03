"""
Gonka Local Proxy — принимает OpenAI запросы с tool_calls,
передаёт tools в модель, возвращает tool_calls или контент.
"""
import json, logging, os, sys, time, uuid
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn, TCPServer
from gonka_openai import GonkaOpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s [gonka-proxy] %(message)s")

GONKA_PRIVATE_KEY = os.environ.get("GONKA_PRIVATE_KEY", "")
if not GONKA_PRIVATE_KEY:
    logging.error("GONKA_PRIVATE_KEY не задан. Проверь /root/gonka/.env")
    sys.exit(1)
GONKA_NODE_URL = "http://node1.gonka.ai:8000"
PROXY_PORT = 8001
MODEL = "Qwen/Qwen3-235B-A22B-Instruct-2507-FP8"

client = GonkaOpenAI(gonka_private_key=GONKA_PRIVATE_KEY, source_url=GONKA_NODE_URL)

class ThreadingHTTPServer(ThreadingMixIn, TCPServer):
    allow_reuse_address = True
    daemon_threads = True

def normalize_messages(raw_messages):
    messages = []
    for msg in raw_messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
            content = "\n".join(parts)
        messages.append({**msg, "content": content})
    return messages

class GonkaProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logging.info(format % args)

    def _write_sse_chunk(self, json_str):
        line = f"data: {json_str}\n\n".encode()
        self.wfile.write(f"{len(line):x}\r\n".encode() + line + b"\r\n")

    def do_POST(self):
        if self.path not in ("/v1/chat/completions", "/chat/completions"):
            self.send_response(404); self.end_headers(); return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        messages = normalize_messages(body.get("messages", []))
        max_tokens = body.get("max_tokens", 1024)
        temperature = body.get("temperature", 0.7)
        tools = body.get("tools", None)
        want_stream = body.get("stream", False)
        req_id = "gonka-" + str(uuid.uuid4())[:8]
        ts = int(time.time())

        try:
            # Передаём tools в модель если они есть
            kwargs = dict(model=MODEL, messages=messages, max_tokens=max_tokens,
                         temperature=temperature, stream=True)
            if tools:
                kwargs["tools"] = tools

            response = client.chat.completions.create(**kwargs)

            # Собираем стрим
            content = ""
            finish_reason = "stop"
            tool_calls = []

            for chunk in response:
                if not hasattr(chunk, 'choices') or not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.delta if hasattr(choice, 'delta') else None
                if delta:
                    if hasattr(delta, 'content') and delta.content:
                        content += delta.content
                    # Собираем tool_calls если модель вызывает инструменты
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index if hasattr(tc, 'index') else 0
                            while len(tool_calls) <= idx:
                                tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                            if hasattr(tc, 'id') and tc.id:
                                tool_calls[idx]["id"] = tc.id
                            if hasattr(tc, 'function'):
                                if hasattr(tc.function, 'name') and tc.function.name:
                                    tool_calls[idx]["function"]["name"] += tc.function.name
                                if hasattr(tc.function, 'arguments') and tc.function.arguments:
                                    tool_calls[idx]["function"]["arguments"] += tc.function.arguments
                if choice.finish_reason:
                    finish_reason = choice.finish_reason

            # Формируем message
            message = {"role": "assistant"}
            if tool_calls:
                message["tool_calls"] = tool_calls
                message["content"] = None
                finish_reason = "tool_calls"
            else:
                message["content"] = content

            result = {
                "id": req_id, "object": "chat.completion", "model": MODEL, "created": ts,
                "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
                "usage": {"prompt_tokens": 0, "completion_tokens": len(content.split()), "total_tokens": 0},
            }

            if want_stream:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                if tool_calls:
                    # Стрим с tool_calls по стандарту OpenAI SSE:
                    # 1. role chunk
                    role_chunk = {"id": req_id, "created": ts, "model": MODEL, "object": "chat.completion.chunk",
                                  "choices": [{"index": 0, "delta": {"role": "assistant", "content": None}, "finish_reason": None}]}
                    self._write_sse_chunk(json.dumps(role_chunk))
                    # 2. tool_call chunks (по одному на каждый tool call)
                    for i, tc in enumerate(tool_calls):
                        tc_chunk = {"id": req_id, "created": ts, "model": MODEL, "object": "chat.completion.chunk",
                                    "choices": [{"index": 0, "delta": {"tool_calls": [{
                                        "index": i,
                                        "id": tc["id"],
                                        "type": "function",
                                        "function": {"name": tc["function"]["name"], "arguments": ""}
                                    }]}, "finish_reason": None}]}
                        self._write_sse_chunk(json.dumps(tc_chunk))
                        # arguments chunk
                        args_chunk = {"id": req_id, "created": ts, "model": MODEL, "object": "chat.completion.chunk",
                                      "choices": [{"index": 0, "delta": {"tool_calls": [{
                                          "index": i,
                                          "function": {"arguments": tc["function"]["arguments"]}
                                      }]}, "finish_reason": None}]}
                        self._write_sse_chunk(json.dumps(args_chunk))
                    # 3. finish chunk
                    done_chunk = {"id": req_id, "created": ts, "model": MODEL, "object": "chat.completion.chunk",
                                  "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}
                    self._write_sse_chunk(json.dumps(done_chunk))
                else:
                    # Обычный текстовый стрим
                    chunk_data = {"id": req_id, "created": ts, "model": MODEL, "object": "chat.completion.chunk",
                                  "choices": [{"index": 0, "delta": {"role": "assistant", "content": content}, "finish_reason": None}]}
                    self._write_sse_chunk(json.dumps(chunk_data))
                    done_chunk = {"id": req_id, "created": ts, "model": MODEL, "object": "chat.completion.chunk",
                                  "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}]}
                    self._write_sse_chunk(json.dumps(done_chunk))
                # DONE
                done_line = "data: [DONE]\n\n".encode()
                self.wfile.write(f"{len(done_line):x}\r\n".encode() + done_line + b"\r\n")
                self.wfile.write(b"0\r\n\r\n")
            else:
                data = json.dumps(result).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        except Exception as e:
            logging.error("Error: %s", e)
            err = json.dumps({"error": {"message": str(e), "type": "server_error", "code": 500}}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            self.wfile.write(err)

    def do_GET(self):
        if self.path in ("/v1/models", "/models"):
            data = json.dumps({"object": "list", "data": [{"id": MODEL, "object": "model"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404); self.end_headers()

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PROXY_PORT), GonkaProxyHandler)
    logging.info("Gonka proxy started on http://127.0.0.1:%d (tools support enabled)", PROXY_PORT)
    server.serve_forever()
