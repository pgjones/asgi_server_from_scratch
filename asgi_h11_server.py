# This can be used,
#    $ python asgi_h11_server.py localhost 5009
# and tested,
#    $ curl -v localhost:5009

import asyncio
import sys

import h11

from echo_app import app


async def asgi_server(reader, writer):
    connection = h11.Connection(h11.SERVER)
    to_app = asyncio.Queue()
    from_app = asyncio.Queue()
    scope = None
    complete = False
    while not complete and not reader.at_eof():
        connection.receive_data(await reader.read(100))
        while True:
           event = connection.next_event()
           if isinstance(event, h11.Request):
               scope = create_scope(event)
           elif isinstance(event, h11.Data):
              await to_app.put(create_message(event))
           elif isinstance(event, h11.EndOfMessage):
              await to_app.put(create_message(event))
              complete = True
              break
           elif isinstance(event, h11.ConnectionClosed):
               complete = True
               break
           elif event is h11.NEED_DATA:
               break
    await app(scope, to_app.get, from_app.put)
    while True:
        message = await from_app.get()
        if message["type"] == "http.response.start":
            writer.write(
                connection.send(
                    h11.Response(status_code=message["status"], headers=message["headers"])
                )
            )
        elif message["type"] == "http.response.body":
            writer.write(connection.send(h11.Data(data=message.get("body", b""))))
            if not message.get("more_body", False):
                writer.write(connection.send(h11.EndOfMessage()))
                break
    await writer.drain()
    writer.close()


def create_scope(request):
    return {
        "type": "http",
        "method": request.method.decode(),
        "scheme": "http",
        "raw_path": request.target,
        "path": request.target.decode(),
        "headers": request.headers,
    }


def create_message(event):
    if isinstance(event, h11.EndOfMessage):
        return {
            "type": "http.request",
            "more_body": False,
        }
    elif isinstance(event, h11.Data):
        return {
            "type": "http.request",
            "body": event.data,
            "more_body": True,
        }


async def main(host, port):
    server = await asyncio.start_server(asgi_server, host, port)
    await server.serve_forever()


if __name__ == "__main__":
    host, port = sys.argv[1], sys.argv[2]
    asyncio.run(main(host, port))
