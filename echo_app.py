async def app(scope, receive, send):
    if scope["type"] != "http":
        raise NotImplementedError()

    body = bytearray()
    while True:
        event = await receive()
        if event["type"] == "http.request":
            body.extend(event.get("body", b""))
            if not event.get("more_body", False):
                break

    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [
            (b"Content-Length", b"%d" % len(body)),
            (b"Content-Type", b"text/plain"),
        ],
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })
