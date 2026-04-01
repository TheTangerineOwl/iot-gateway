import asyncio
import sys
from core.gateway import Gateway


def register_adapters(gateway: Gateway):
    # adapter =
    # gateway.register_adapter(adapter)
    pass


async def main():
    gateway = Gateway()
    register_adapters(gateway)
    await gateway.run_forever()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Stop')
        sys.exit(0)
