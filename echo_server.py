# This can be used,
#    $ python echo_server.py localhost 5005
# and tested,
#    $ telnet localhost 5005

import asyncio
import sys


async def echo_server(reader, writer):
    while not reader.at_eof():
        data = await reader.read(100)
        writer.write(data)
        await writer.drain()
    writer.close()


async def main(host, port):
    server = await asyncio.start_server(echo_server, host, port)
    await server.serve_forever()


if __name__ == "__main__":
    host, port = sys.argv[1], sys.argv[2]
    asyncio.run(main(host, port))
