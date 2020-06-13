# This can be used,
#    $ python h11_server.py localhost 5007
# and tested,
#    $ curl -v localhost:5007

import asyncio
import sys

import h11


async def h11_server(reader, writer):
    connection = h11.Connection(h11.SERVER)
    body = bytearray()
    complete = False
    while not complete and not reader.at_eof():
        connection.receive_data(await reader.read(100))
        while True:
           event = connection.next_event()
           if isinstance(event, h11.Request):
               print(event.method, event.target, event.headers)
           elif isinstance(event, h11.Data):
               body.extend(event.data)
           elif isinstance(event, (h11.ConnectionClosed, h11.EndOfMessage)):
               complete = True
               break
           elif event is h11.NEED_DATA:
               break
    writer.write(connection.send(h11.Response(status_code=200, headers=[])))
    writer.write(connection.send(h11.EndOfMessage()))
    await writer.drain()
    writer.close()


async def main(host, port):
    server = await asyncio.start_server(h11_server, host, port)
    await server.serve_forever()


if __name__ == "__main__":
    host, port = sys.argv[1], sys.argv[2]
    asyncio.run(main(host, port))
