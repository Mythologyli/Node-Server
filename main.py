import sys
import time
import json
import asyncio

from loguru import logger


# 记录上次收到的字符串
last_str: str = ''


async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global last_str

    data: bytes = await reader.read(100)

    # 尝试解码
    try:
        req_str: str = data.decode('utf-8')
    except UnicodeDecodeError:  # 捕获解码错误异常
        writer.close()
        return

    addr: tuple = writer.get_extra_info('peername')
    logger.debug(f"从 {addr!r} 接收：{req_str!r}")

    str_list = req_str.split('&')  # 分割字符串

    if len(str_list) != 5:  # 数据缺失
        print('数据缺失！')
        writer.close()
        return

    if (req_str != last_str):  # 检测数据是否重复
        last_str = req_str

        try:  # 转换数据
            seq: int = int(str_list[0])
            humi: float = round(float(str_list[1]), 1)
            temp: float = round(float(str_list[2]), 1)
            light: float = round(float(str_list[3]), 1)

        except Exception:
            print('数据错误！')
            writer.close()  # 数据错误，等待重传
            return

        print(f"节点：{seq}    湿度：{humi}%    温度：{temp}°C    光照度：{light}lx")

        # 写入 json 文件
        data = json.loads(open('./data.json', 'r', encoding='utf-8').read())

        data['node' + str(seq)]['humi'] = humi
        data['node' + str(seq)]['temp'] = temp
        data['node' + str(seq)]['light'] = light
        data['time'] = time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

        with open('./data.json', 'w') as fp:
            fp.write(json.dumps(data))
            fp.close()

    else:
        print('数据重复！')

    logger.debug(f"发送：OK")
    writer.write(('OK').encode('utf-8'))
    await writer.drain()

    logger.debug("关闭连接")
    writer.close()


async def main():
    server = await asyncio.start_server(handler, '0.0.0.0', 2333)

    # 在此处更改日志等级
    logger.remove()
    logger.add(
        sys.stdout,
        level="DEBUG",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <9}</level> | <level>{message}</level>"
    )

    addr = server.sockets[0].getsockname()
    logger.debug(f"Node Server 开始运行：{addr}")

    async with server:
        await server.serve_forever()

asyncio.run(main())
