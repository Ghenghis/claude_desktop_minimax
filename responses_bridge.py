"""Stateless Responses <-> Chat Completions translation; never executes tools."""

import json
import time
import uuid

TEXT_MODELS = frozenset(
    (
        "MiniMax-M3",
        "MiniMax-M2.7",
        "MiniMax-M2.7-highspeed",
        "MiniMax-M2.5",
        "MiniMax-M2.5-highspeed",
        "MiniMax-M2.1",
        "MiniMax-M2.1-highspeed",
        "MiniMax-M2",
        "M2-her",
    )
)


def make_id(prefix="resp"):
    return f"{prefix}_{uuid.uuid4().hex[:24]}"


def content_parts(content):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        raise ValueError("message content must be text or an array")
    parts = []
    for part in content:
        if not isinstance(part, dict):
            raise ValueError("invalid content part")
        kind = part.get("type")
        if kind in ("input_text", "output_text", "text"):
            if not isinstance(part.get("text"), str):
                raise ValueError("text content must be a string")
            parts.append({"type": "text", "text": part["text"]})
        elif kind == "input_image" and isinstance(part.get("image_url"), str):
            parts.append(
                {"type": "image_url", "image_url": {"url": part["image_url"], "detail": part.get("detail", "auto")}}
            )
        else:
            raise ValueError(f"unsupported content type: {kind}; use an explicit MCP tool for this capability")
    if all(p["type"] == "text" for p in parts):
        return "\n".join(p["text"] for p in parts)
    return parts


def input_to_messages(body):
    if body.get("previous_response_id") or body.get("conversation"):
        raise ValueError("this gateway is stateless; send the full conversation input")
    messages, pending = [], []
    instructions = body.get("instructions")
    if instructions:
        if not isinstance(instructions, str):
            raise ValueError("instructions must be a string")
        messages.append({"role": "system", "content": instructions})
    inp = body.get("input")
    if isinstance(inp, str):
        return messages + [{"role": "user", "content": inp}]
    if not isinstance(inp, list):
        raise ValueError("input must be text or an array")

    def flush():
        if pending:
            messages.append({"role": "assistant", "content": None, "tool_calls": pending.copy()})
            pending.clear()

    for item in inp:
        if not isinstance(item, dict):
            raise ValueError("input items must be objects")
        kind = item.get("type", "message")
        if kind == "reasoning":
            continue  # Provider-specific private state is not a user message.
        if kind in ("function_call", "custom_tool_call"):
            call_id = item.get("call_id") or item.get("id")
            name = item.get("name")
            if not isinstance(call_id, str) or not isinstance(name, str):
                raise ValueError("tool call requires call_id and name")
            args = (
                item.get("arguments", "{}") if kind == "function_call" else json.dumps({"input": item.get("input", "")})
            )
            if not isinstance(args, str):
                raise ValueError("tool arguments must be a string")
            pending.append({"id": call_id, "type": "function", "function": {"name": name, "arguments": args}})
            continue
        flush()
        if kind in ("function_call_output", "custom_tool_call_output"):
            if not isinstance(item.get("call_id"), str):
                raise ValueError("tool output requires call_id")
            messages.append(
                {"role": "tool", "tool_call_id": item["call_id"], "content": content_parts(item.get("output", ""))}
            )
        elif kind == "message":
            role = item.get("role", "user")
            if role not in ("user", "assistant", "developer", "system"):
                raise ValueError("unsupported message role")
            messages.append(
                {"role": "system" if role == "developer" else role, "content": content_parts(item.get("content", ""))}
            )
        else:
            raise ValueError(f"unsupported input type: {kind}")
    flush()
    return messages


def build_chat_request(body, default_model=""):
    if not isinstance(body, dict):
        raise ValueError("JSON object required")
    if body.get("background"):
        raise ValueError("background execution is disabled")
    model = body.get("model") or default_model
    if not isinstance(model, str) or not model:
        raise ValueError("model is required")
    if model not in TEXT_MODELS:
        raise ValueError("unsupported model")
    if "stream" in body and not isinstance(body["stream"], bool):
        raise ValueError("stream must be boolean")
    req = {"model": model, "messages": input_to_messages(body), "stream": body.get("stream", False)}
    for src, dest in (
        ("temperature", "temperature"),
        ("top_p", "top_p"),
        ("max_output_tokens", "max_tokens"),
        ("parallel_tool_calls", "parallel_tool_calls"),
    ):
        if src in body:
            req[dest] = body[src]
    reasoning = body.get("reasoning")
    if isinstance(reasoning, dict) and reasoning.get("effort"):
        req["reasoning_effort"] = reasoning["effort"]
    custom = set()
    tools = body.get("tools", [])
    if not isinstance(tools, list):
        raise ValueError("tools must be an array")
    converted = []
    for tool in tools:
        if not isinstance(tool, dict):
            raise ValueError("tool must be an object")
        kind = tool.get("type")
        if kind == "function":
            fn = tool.get("function", tool)
            if not isinstance(fn, dict) or not isinstance(fn.get("name"), str):
                raise ValueError("function name is required")
            converted.append(
                {
                    "type": "function",
                    "function": {k: fn[k] for k in ("name", "description", "parameters", "strict") if k in fn},
                }
            )
        elif kind == "custom" and isinstance(tool.get("name"), str):
            custom.add(tool["name"])
            converted.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": {
                            "type": "object",
                            "properties": {"input": {"type": "string"}},
                            "required": ["input"],
                            "additionalProperties": False,
                        },
                    },
                }
            )
        else:
            raise ValueError(f"unsupported tool type: {kind}; use a client-side MCP function")
    if converted:
        req["tools"] = converted
    choice = body.get("tool_choice")
    if isinstance(choice, str):
        req["tool_choice"] = choice
    elif isinstance(choice, dict):
        if choice.get("type") not in ("function", "custom") or not isinstance(choice.get("name"), str):
            raise ValueError("unsupported tool_choice")
        req["tool_choice"] = {"type": "function", "function": {"name": choice["name"]}}
    text = body.get("text", {})
    if isinstance(text, dict) and text.get("format", {}).get("type", "text") != "text":
        raise ValueError("structured text formats are not supported by this gateway")
    if req["stream"]:
        req["stream_options"] = {"include_usage": True}
    return req, custom


def usage_from_chat(usage):
    return {
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)),
    }


def response_object(resp_id, model, output, status="completed", usage=None):
    return {
        "id": resp_id,
        "object": "response",
        "created_at": int(time.time()),
        "status": status,
        "model": model,
        "output": output,
        "usage": usage,
        "error": None,
        "incomplete_details": None,
        "parallel_tool_calls": True,
        "previous_response_id": None,
        "store": False,
    }


def tool_item(tc, custom, status="completed"):
    fn = tc.get("function", {})
    name = fn.get("name", "")
    call_id = tc.get("id")
    if not isinstance(call_id, str) or not call_id or not isinstance(name, str) or not name:
        raise ValueError("upstream tool call missing name or ID")
    args = fn.get("arguments", "")
    if not isinstance(args, str):
        raise ValueError("upstream tool arguments are not a string")
    item = {
        "id": make_id("fc"),
        "type": "function_call",
        "call_id": call_id,
        "name": name,
        "arguments": args,
        "status": status,
    }
    if name in custom:
        parsed = json.loads(args)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("input"), str):
            raise ValueError("custom tool requires a string input")
        item.update(type="custom_tool_call", input=parsed["input"])
        del item["arguments"]
    return item


def chat_response_to_responses(chat, model, resp_id, custom=()):
    choices = chat.get("choices") if isinstance(chat, dict) else None
    if not isinstance(choices, list) or not choices:
        raise ValueError("upstream response has no choices")
    choice = choices[0]
    reason = choice.get("finish_reason")
    if reason not in ("stop", "tool_calls", "length", "content_filter"):
        raise ValueError("upstream response did not finish")
    status = "incomplete" if reason in ("length", "content_filter") else "completed"
    msg = choice.get("message", {})
    output = []
    content = msg.get("content") or ""
    if not isinstance(content, str):
        raise ValueError("upstream output text is not a string")
    if content:
        output.append(
            {
                "id": make_id("msg"),
                "type": "message",
                "role": "assistant",
                "status": status,
                "content": [{"type": "output_text", "text": content, "annotations": []}],
            }
        )
    for tc in msg.get("tool_calls", []):
        output.append(tool_item(tc, custom, status))
    result = response_object(resp_id, model, output, status, usage_from_chat(chat.get("usage", {})))
    if status == "incomplete":
        result["incomplete_details"] = {"reason": "max_output_tokens" if reason == "length" else "content_filter"}
    return result


class ResponseStream:
    def __init__(self, model, resp_id, custom=()):
        self.model, self.resp_id, self.custom = model, resp_id, custom
        self.output, self.calls, self.message = [], {}, None
        self.usage, self.reason, self.sequence = {}, None, 0

    def event(self, kind, **data):
        result = {"type": kind, "sequence_number": self.sequence, **data}
        self.sequence += 1
        # Serialize now: later mutations cannot change previously emitted events.
        return "event: " + kind + "\ndata: " + json.dumps(result) + "\n\n"

    def begin(self):
        response = response_object(self.resp_id, self.model, [], "in_progress")
        return [
            self.event("response.created", response=response),
            self.event("response.in_progress", response=response),
        ]

    def accept(self, chunk):
        if not isinstance(chunk, dict) or chunk.get("error"):
            raise ValueError("upstream stream error")
        if chunk.get("usage"):
            self.usage = chunk["usage"]
        choices = chunk.get("choices", [])
        if not choices:
            return []
        choice = choices[0]
        if choice.get("finish_reason"):
            self.reason = choice["finish_reason"]
        delta, events = choice.get("delta", {}), []
        text = delta.get("content")
        if text:
            if not isinstance(text, str):
                raise ValueError("invalid text delta")
            if self.message is None:
                index = len(self.output)
                self.message = {
                    "id": make_id("msg"),
                    "type": "message",
                    "role": "assistant",
                    "status": "in_progress",
                    "content": [],
                }
                self.message_index = index
                self.output.append(self.message)
                events.append(self.event("response.output_item.added", output_index=index, item=self.message))
                self.message["content"].append({"type": "output_text", "text": "", "annotations": []})
                events.append(
                    self.event(
                        "response.content_part.added",
                        output_index=index,
                        item_id=self.message["id"],
                        content_index=0,
                        part=self.message["content"][0],
                    )
                )
            self.message["content"][0]["text"] += text
            events.append(
                self.event(
                    "response.output_text.delta",
                    output_index=self.message_index,
                    item_id=self.message["id"],
                    content_index=0,
                    delta=text,
                    logprobs=[],
                )
            )
        # reasoning_content stays private; it is not a delta on a message item.
        for tc in delta.get("tool_calls", []):
            index = tc.get("index", 0)
            if not isinstance(index, int) or index < 0 or index > 127:
                raise ValueError("invalid upstream tool index")
            fn = tc.get("function", {})
            if index not in self.calls:
                call_id, name = tc.get("id"), fn.get("name")
                if not call_id or not name:
                    raise ValueError("initial tool delta missing name or ID")
                item = {
                    "id": make_id("fc"),
                    "type": "function_call",
                    "call_id": call_id,
                    "name": name,
                    "arguments": "",
                    "status": "in_progress",
                }
                self.calls[index] = {"item": item, "output_index": len(self.output), "raw": ""}
                self.output.append(item)
                if name in self.custom:
                    item.update(type="custom_tool_call", input="")
                    del item["arguments"]
                events.append(self.event("response.output_item.added", output_index=len(self.output) - 1, item=item))
            call = self.calls[index]
            if tc.get("id") not in (None, call["item"]["call_id"]):
                raise ValueError("upstream changed tool call ID")
            if fn.get("name") not in (None, "", call["item"]["name"]):
                raise ValueError("upstream changed tool name")
            args = fn.get("arguments", "")
            if not isinstance(args, str):
                raise ValueError("invalid tool argument delta")
            call["raw"] += args
            if call["item"]["type"] == "function_call":
                call["item"]["arguments"] += args
                if args:
                    events.append(
                        self.event(
                            "response.function_call_arguments.delta",
                            item_id=call["item"]["id"],
                            output_index=call["output_index"],
                            delta=args,
                        )
                    )
        return events

    def finish(self):
        if self.reason not in ("stop", "tool_calls", "length", "content_filter"):
            raise ValueError("upstream stream ended before a finish reason")
        status = "incomplete" if self.reason in ("length", "content_filter") else "completed"
        events = []
        for index, item in enumerate(self.output):
            item["status"] = status
            if item["type"] == "message":
                part = item["content"][0]
                events.append(
                    self.event(
                        "response.output_text.done",
                        item_id=item["id"],
                        output_index=index,
                        content_index=0,
                        text=part["text"],
                        logprobs=[],
                    )
                )
                events.append(
                    self.event(
                        "response.content_part.done", item_id=item["id"], output_index=index, content_index=0, part=part
                    )
                )
            elif item["type"] == "function_call":
                events.append(
                    self.event(
                        "response.function_call_arguments.done",
                        item_id=item["id"],
                        output_index=index,
                        arguments=item["arguments"],
                        name=item["name"],
                    )
                )
            else:
                call = next(c for c in self.calls.values() if c["item"] is item)
                parsed = json.loads(call["raw"])
                if not isinstance(parsed, dict) or not isinstance(parsed.get("input"), str):
                    raise ValueError("invalid custom tool input")
                item["input"] = parsed["input"]
                events.append(
                    self.event(
                        "response.custom_tool_call_input.delta",
                        item_id=item["id"],
                        output_index=index,
                        delta=item["input"],
                    )
                )
                events.append(
                    self.event(
                        "response.custom_tool_call_input.done",
                        item_id=item["id"],
                        output_index=index,
                        input=item["input"],
                    )
                )
            events.append(self.event("response.output_item.done", output_index=index, item=item))
        response = response_object(self.resp_id, self.model, self.output, status, usage_from_chat(self.usage))
        if status == "incomplete":
            response["incomplete_details"] = {
                "reason": "max_output_tokens" if self.reason == "length" else "content_filter"
            }
        events.append(self.event("response." + status, response=response))
        return events

    def fail(self, message="Upstream request failed or stream was interrupted"):
        response = response_object(self.resp_id, self.model, self.output, "failed")
        response["error"] = {"code": "upstream_error", "message": message}
        return self.event("response.failed", response=response)
