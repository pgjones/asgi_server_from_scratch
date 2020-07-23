# This can be used,
#    $ python asgi_http_parser_server.py localhost 5008
# and tested,
#    $ curl -v localhost:5008

import asyncio
import sys

from echo_app import app


class HTTPParser:
    def __init__(self):
        self.part = "REQUEST"
        self.headers = []
        self.body_length = 0

    def feed_line(self, line: bytes):
        if self.part == "REQUEST":
            self.method, self.path, self.version = line.split(b" ", 2)
            self.part = "HEADERS"
        elif self.part == "HEADERS" and line.strip() == b"":
            self.part = "BODY"
        elif self.part == "HEADERS":
            name, value = line.split(b":", 1)
            self.headers.append((name.strip(), value.strip()))
            if name.lower() == b"content-length":
                self.body_length = int(value)


async def asgi_http_parser_server(reader, writer):
    parser = HTTPParser()
    to_app = asyncio.Queue()
    read = 0
    while not reader.at_eof():
        if parser.part != "BODY":
            parser.feed_line(await reader.readline())
        elif parser.body_length == 0:
            await to_app.put(create_message(b"", False))
            break
        else:
            body = await reader.read(100)
            read += len(body)
            await to_app.put(create_message(body, read < parser.body_length))
            if read >= parser.body_length:
                break
    scope = create_scope(parser)
    from_app = asyncio.Queue()
    await app(scope, to_app.get, from_app.put)
    while True:
        message = await from_app.get()
        if message["type"] == "http.response.start":
            writer.write(b"HTTP/1.1 %d\r\n" % message["status"])
            for header in message["headers"]:
                writer.write(b"%s: %s\r\n" % (header))
            writer.write(b"\r\n")
        elif message["type"] == "http.response.body":
            if message.get("body") is not None:
                writer.write(message["body"])
            if not message.get("more_body", False):
                break

    await writer.drain()
    writer.close()


def create_scope(parser):
    return {
        "type": "http",
        "method": parser.method,
        "scheme": "http",
        "raw_path": parser.path,
        "path": parser.path.decode(),
        "headers": parser.headers,
    }


def create_message(body, more_body):
    return {
        "type": "http.request",
        "body": body,
        "more_body": more_body,
    }


async def main(host, port):
    server = await asyncio.start_server(asgi_http_parser_server, host, port)
    await server.serve_forever()


if __name__ == "__main__":
    host, port = sys.argv[1], sys.argv[2]
    asyncio.run(main(host, port))
