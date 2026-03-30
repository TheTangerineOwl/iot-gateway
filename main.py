import asyncio
import sys


async def main():
    # await
    pass


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Stop')
        sys.exit(0)
