"""
前言：该插件命名可能有些混乱（如有需要，可以重构），因为是直接从本人项目中单拎出来的插件，本人第一次上传代码，如有纰漏请指出
说明：该插件为Nonebot2插件，支持从QQ侧发送消息，直接修改服务端json文件，从而实现便捷的配置管理。本插件以键索引为基础，实现了类似于目录的操作效果
使用方法：Nonebot2的插件安装请参考Nonebot2的官方教程，下面command_list为具体的命令信息
配置信息（重要）：
1. 本插件只会响应SUPERUSER的操作，同时本插件无法修改SUPERUSER的信息，请在Nonebot2中自行配置
本插件需要进行的配置在导入库的下方
2. config_file 需要配置成自己使用的json文件名称
3. max_recursive_layers 将会影响在QQ侧所能控制的最大字典层数，不宜太大，除非有特殊需求
指令说明：
1. 字典递归访问 [key1] [key2]... 中间以空格隔开
2. 数据列表 [word1],[word2] 中间以逗号隔开
操作示例
/mt config help 将会直接显示下方的config_command_list 列表
/mt config show key1 key2 将会从key1开始遍历,然后进入到key2中,并且输出key2中的所有数据,若该数据为字典,则会访问其目录下是否存在"annotation",若存在则会输出其描述信息
/mt config add key1 key2 list 123 将会把字符串123传入到key2中,此时key2的格式为列表
/mt config add key1 key2 int/float/string 123 将会把对应格式覆盖到key2中,此时key2的格式为int/float/string
/mt config get key1 key2 将会输出key2的值,无论其是什么格式
/mt config del_key key1 key2 key3 遍历到key2层,然后删除掉key2中名为key3的键以及其数据
/mt config del key1 key2 123,345 将会遍历到key1层,然后查询key2中存在的123,345字符串进行删除操作,注：del操作只对列表有效,若想删除全部,请使用del_key
"""
mt_command_list = """\
当前/mt命令列表
/mt or /mt help 显示当前列表
/mt config help显示config操作列表
"""
config_command_list = """\
当前/mt config命令列表
/mt config help 显示当前列表
/mt config show [key1] [key2]...
显示当前配置的key,支持字典递归访问
/mt config get [key1] [key2]... 
显示目标值,支持字典递归访问
/mt config add [key]... [add_type] [add_word1],[add_word2]... 
给指定配置增加新的值,支持字典递归访问
/mt config del [key]... [del_word1],[del_word2]... 
给指定配置删除某一值,支持字典递归访问
/mt config del_key [key]...
删除指定配置的键，支持字典递归访问
"""
import os
import json
from typing import Dict, Callable, Tuple
from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.message import Message
from nonebot.log import logger
config_file = "monitor_config.json"  # 该插件支持的配置文件json格式
max_recursive_layers = 5  # 支持最大的递归层数，超过该层数的指令将返回参数不匹配

monitor_control = on_command("mt", permission=SUPERUSER)
@monitor_control.handle()
async def monitor_control_main(args: Message = CommandArg()):
    """
    monitor_control的主函数，用于指令控制
    :return:
    """
    command = args.extract_plain_text().split()
    await mt_handler.dispatch(command)
class MT_Command_Manager:
    def __init__(self):
        """
        初始化MT_Command_Manager类，可传入对象有name：函数名，func：实际执行函数名，param_range：函数参数数量范围
        :return:
        """
        self._command: Dict[str, Tuple[Callable, Tuple[int, int]]] = {}

    def register(self, name: str, param_range: Tuple[int,int]):
        """
        MT_Command_Manager的实际注册函数
        :param name:函数的外部调用名
        :param param_range:函数的外部调用参数范围
        :return:自身内部装饰器
        """
        def decorator(func: Callable):
            """
            进行函数的实际调用名注册
            :param func:实际调用的函数名
            :return:
            """
            self._command[name] = (func, param_range)
            return func
        return decorator

    async def dispatch(self, args: list):
        """
        命令转接处理函数，将主函数的调用传入到该函数进行筛选过滤，同时便于管理
        :param args: 传入的命令参数
        :return: 空/指定函数调用
        """
        if not args:  # 若没有参数则直接调用/mt help, 其等价与/mt == /mt help
            await mt_command_list_print()  # 调用打印函数
            return

        cmd = args[0]  # 将传入的第一个参数作为 mt的子命令进行后续操作
        if cmd not in self._command:  # 判断该子命令是否注册，若不存在则返回
            await monitor_control.send("该命令不存在，请使用/mt查看当前可用命令")
            return

        call_func, (min_param, max_param) = self._command[cmd]  # 将存储的命令与参数范围进行导出
        actual_args = args[1:]  # 去除掉上方的子命令
        if not (min_param <= len(actual_args) <= max_param):  # 进行参数范围判断
            await monitor_control.send(f"该命令参数数量存在问题,参数范围为{min_param}-{max_param}")
            return

        await call_func(actual_args)  # 指定函数调用


mt_handler = MT_Command_Manager()  # mt 的函数管理装置
@mt_handler.register("help", (0, 0))
async def mt_command_list_print():
    """
    打印出命令列表
    :return:
    """
    await monitor_control.send(mt_command_list)
    return

config_handler = MT_Command_Manager()  # mt_config 的函数管理装置
@mt_handler.register("config", (0, max_recursive_layers+1))
async def mt_config_manager(args):
    """
    mt_config的主函数，mt_config各函数的入口
    """
    await config_handler.dispatch(args=args)
    return

@config_handler.register("help", (0, 0))
async def config_command_list_print(args):
    """
    用于打印mt_config的信息
    :param args: 防止传参时报错
    :return:
    """
    await monitor_control.send(config_command_list)
    return

@config_handler.register("show", (0, max_recursive_layers))
async def config_command_show(args):
    """
    用于展示monitor_config的各key值以及配置信息
    :param args: 防止传参报错
    :return:
    """
    monitor_config: dict = json_file_read(config_file)  # 加载配置文件
    show_result = ""  # 最终发送的消息
    result_message = ""
    result_message, result_dict = dict_traversal(monitor_config,args)  # 返回递归搜寻结果
    show_result += result_message + "\n"  # 在显示首部添加信息
    for key in result_dict.keys():
        try:
            show_result += f"{key} {result_dict[key]["annotation"]}\n"  # 若存在描述信息则添加
        except KeyError:
            show_result += f"{key} 该字典暂无描述\n"  # 若不存在描述信息则显示暂无描述
        except TypeError:
            show_result += f"{key} {str(result_dict[key])}\n"  # 若不为字典则显示具体值
    if not show_result:
        await monitor_control.send("未查询到有效配置，请检查代码是否错误")
    await monitor_control.send(show_result)

@config_handler.register("get",(2, max_recursive_layers))
async def config_command_get(args):
    get_result = ""  # 最终发送的消息
    get_result_key = args.pop()  # 将需要查询的键从列表中取出
    monitor_config: dict = json_file_read(config_file)  # 加载配置文件
    result_message, result_dict = dict_traversal(monitor_config, args)  # 返回递归搜寻结果
    get_result += result_message + "\n"  # 将查询字典层的消息放入
    try:
        get_result += str(result_dict[get_result_key])  # 加入查询的结果值
    except KeyError:
        get_result = f"目标{args.pop()}层处不存在{get_result_key}的键"  # 不存在则直接覆盖返回消息
    await monitor_control.send(get_result)
    return

@config_handler.register("add",(3, max_recursive_layers))
async def config_command_add(args: list):
    datas: str = args.pop()
    add_type:str = args.pop()
    if add_type not in ("str", "list","int","float"):
        await monitor_control.send(f"{add_type}不属于 str,list,int,float 类型之一")
        return
    data_list = datas.split(",")  # 需要增加的数据
    monitor_config: dict = json_file_read(config_file)  # 加载配置文件
    current_dict, logs = dict_traversal_add(monitor_config,args,add_type,data_list)
    json_file_write(config_file, current_dict)
    add_result = "\n".join(log for log in logs)
    await monitor_control.send(add_result)
    return

@config_handler.register("del_key",(1, max_recursive_layers))
async def config_command_del_key(args: list):
    monitor_config: dict = json_file_read(config_file)  # 加载配置文件
    current_dict, logs = dict_traversal_del_key(monitor_config, args)
    json_file_write(config_file,current_dict)
    del_key_result = "\n".join(log for log in logs)
    await monitor_control.send(del_key_result)
    return

@config_handler.register("del",(2, max_recursive_layers))
async def config_command_del(args: list):
    delete_item = args.pop()
    monitor_config: dict = json_file_read(config_file)  # 加载配置文件
    current_dict, logs = dict_traversal_del(monitor_config, args,delete_item)
    json_file_write(config_file,current_dict)
    del_result = "\n".join(log for log in logs)
    await monitor_control.send(del_result)
    return


def json_file_read(file_name: str):
    """
    json文件读取函数
    :param file_name: 需要read的json文件
    :return: 字典格式的json文件
    """
    current_directory = os.path.dirname(os.path.abspath(__file__))
    # 拼接完整的文件路径
    file_path = os.path.join(current_directory, file_name)
    with open(file_path, mode='r',encoding='utf-8',newline='')as file:
        return json.load(file)
def json_file_write(file_name: str, json_data:dict):
    """
        json文件写入函数
        :param file_name: 需要read的json文件
        :return: 字典格式的json文件
        """
    current_directory = os.path.dirname(os.path.abspath(__file__))
    # 拼接完整的文件路径
    file_path = os.path.join(current_directory, file_name)
    with open(file_path, mode='w', encoding='utf-8', newline='') as file:
        json.dump(json_data, file, ensure_ascii=False, indent=4)
        return

def dict_traversal(query_dict: dict,keys: list):
    """
    用于查询字典中的子项，支持嵌套查询
    :param query_dict: 查询的起始字典
    :param keys: 查询的嵌套列表
    :return:
    """
    if not keys:
        return f"Success",query_dict
    key = keys[0]  # 获取当前层key
    try:
        queried_dict = query_dict[key]  # 查询当前层key
        if type(queried_dict) is not dict:
            return f"{key}层不为字典", query_dict
    except KeyError:
        return f"{key}处发生了KeyError", query_dict  # 报错后范围已查询位置与错误信息
    return dict_traversal(queried_dict,keys[1:])  # 递归查询

def dict_traversal_add(query_dict: dict,path_keys: list,add_type:str,add_datas: list):
    """
    支持list的追加，支持str,int,float的覆写
    :param query_dict: 根字典
    :param path_keys: 路径键列表
    :param add_type: 添加数据的类型
    :param add_datas: 添加的数据
    :return:
    """
    current_dict = query_dict
    logs = []
    # 遍历中间键，逐层创建缺失的字典
    for depth, key in enumerate(path_keys[:-1], start=1):
        if key not in current_dict:
            current_dict[key] = {}
            logs.append(f"第{depth}层不存在 '{key}'，已新创建\n")
        current_dict = current_dict[key]
    # 处理最后一个键
    last_key = path_keys[-1]
    if last_key in current_dict:
        # 根据 add_type 进行数据操作
        if add_type == "str":
            current_dict[last_key] = "".join(add_datas)
            logs.append(f"键 '{last_key}' 已存在，字符串已覆盖")
        elif add_type == "list":
            add_string = "".join(add_datas)
            if isinstance(current_dict[last_key], list):

                current_dict[last_key].append(add_string)
                logs.append(f"键 '{last_key}' 已存在，列表已追加")
            else:
                current_dict[last_key] = [current_dict[last_key], add_string]
                logs.append(f"键 '{last_key}' 类型不匹配，已转换为列表并追加")
        elif add_type == "int":
            current_dict[last_key] = int(add_datas[0])
        elif add_type == "float":
            current_dict[last_key] = float(add_datas[0])
        else:
            logs.append(f"错误：不支持的 add_type '{add_type}'")
    else:
        # 键不存在，直接赋值
        current_dict[last_key] = add_datas
        logs.append(f"键 '{last_key}' 不存在，已新创建并赋值")
    return query_dict, logs


def dict_traversal_del_key(query_dict: dict, path_keys: list) -> tuple[dict, list]:
    """
    动态遍历字典并删除指定路径的键
    :param query_dict: 目标字典
    :param path_keys: 键路径（如 ["a", "b", "c"]）
    :return: 修改后的字典和操作日志
    """
    current_dict = query_dict
    logs = []

    # 遍历中间键
    for depth, key in enumerate(path_keys[:-1], start=1):
        if key not in current_dict:
            logs.append(f"第{depth}层不存在 '{key}'，无法删除\n")
            return query_dict, logs
        current_dict = current_dict[key]

    # 处理最后一个键
    last_key = path_keys[-1]
    if last_key in current_dict:
        # 删除键
        del current_dict[last_key]
        logs.append(f"键 '{last_key}' 已删除")
    else:
        logs.append(f"键 '{last_key}' 不存在，无法删除")

    return query_dict, logs


def dict_traversal_del(query_dict: dict, path_keys: list, items_to_delete) -> tuple[dict, list]:
    """
    动态遍历字典并从列表中删除指定元素
    :param query_dict: 目标字典
    :param path_keys: 键路径（如 ["a", "b", "c"]）
    :param items_to_delete: 要删除的元素（可以是单个元素或列表）
    :return: 修改后的字典和操作日志
    """
    current_dict = query_dict
    logs = []

    # 遍历中间键
    for depth, key in enumerate(path_keys[:-1], start=1):
        if key not in current_dict:
            logs.append(f"第{depth}层不存在 '{key}'，无法删除\n")
            return query_dict, logs
        current_dict = current_dict[key]

    # 处理最后一个键
    last_key = path_keys[-1]
    if last_key in current_dict:
        if isinstance(current_dict[last_key], list):
            # 如果 items_to_delete 是列表，删除所有匹配的元素
            if isinstance(items_to_delete, list):
                for item in items_to_delete:
                    if item in current_dict[last_key]:
                        current_dict[last_key].remove(item)
                        logs.append(f"键 '{last_key}' 的列表已删除元素 '{item}'\n")
                    else:
                        logs.append(f"键 '{last_key}' 的列表中不存在元素 '{item}'\n")
            else:
                # 如果 items_to_delete 是单个元素，删除匹配的元素
                if items_to_delete in current_dict[last_key]:
                    current_dict[last_key].remove(items_to_delete)
                    logs.append(f"键 '{last_key}' 的列表已删除元素 '{items_to_delete}'\n")
                else:
                    logs.append(f"键 '{last_key}' 的列表中不存在元素 '{items_to_delete}'\n")
        else:
            logs.append(f"键 '{last_key}' 不是列表，无法删除元素\n")
    else:
        logs.append(f"键 '{last_key}' 不存在，无法删除元素\n")

    return query_dict, logs
