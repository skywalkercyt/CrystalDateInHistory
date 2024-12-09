import requests
import random
from datetime import datetime
from bs4 import BeautifulSoup
import json
import tkinter as tk
from tkinter import scrolledtext
import logging
from PIL import Image, ImageTk
import io
import base64

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_today_in_history():
    """获取历史上的今天事件"""
    today = datetime.now()
    month = today.month
    day = today.day
    
    # 使用中文维基百科的API
    url = "https://zh.wikipedia.org/api/rest_v1/feed/onthisday/events/" + f"{month:02d}/{day:02d}"
    headers = {
        "User-Agent": "HistoryBot/1.0 (yuetian@example.com)",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # 获取历史事件列表
        events = []
        for event in data.get('events', []):
            year = event.get('year')
            content = event.get('text', '')
            # 获取维基百科链接
            wiki_link = None
            if event.get('pages') and len(event['pages']) > 0:
                wiki_link = event['pages'][0].get('content_urls', {}).get('desktop', {}).get('page', '')
            
            if year and content:
                events.append({
                    'year': year,
                    'content': content,
                    'wiki_link': wiki_link
                })
        
        # 随机选择一个事件
        if events:
            event = random.choice(events)
            # 获取额外的相关链接
            related_links = get_bing_links(f"{event['year']} {event['content']}")
            # 如果有维基百科链接，添加到相关链接的开头
            if event.get('wiki_link'):
                related_links.insert(0, f"维基百科原文: {event['wiki_link']}")
            return format_message(month, day, event, related_links)
        else:
            return f"今天是{month}月{day}日，暂无历史事件信息。"
            
    except requests.exceptions.RequestException as e:
        logger.error(f"获取历史上的今天信息失败: {str(e)}")
        return f"获取历史上的今天信息失败，请稍后重试。"
    except json.JSONDecodeError as e:
        logger.error(f"解析JSON数据失败: {str(e)}")
        return "数据解析失败，请稍后重试。"
    except Exception as e:
        logger.error(f"未知错误: {str(e)}")
        return "发生未知错误，请稍后重试。"

def get_bing_links(keyword):
    """从Bing获取相关链接"""
    url = f"https://cn.bing.com/search?q={keyword}&ensearch=0"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        
        results = soup.find_all('li', class_='b_algo')[:5]
        for result in results:
            try:
                link_elem = result.find('a')
                title_elem = result.find('h2')
                if link_elem and title_elem:
                    link = link_elem.get('href', '')
                    title = title_elem.get_text(strip=True)
                    if link and title and link.startswith('http'):
                        links.append(f"{title}: {link}")
            except Exception as e:
                logger.error(f"处理搜索结果时出错: {str(e)}")
                continue
        
        return links
    except Exception as e:
        logger.error(f"获取Bing搜索结果时发生错误: {str(e)}")
        return []

def format_message(month, day, event, related_links):
    """格式化消息"""
    try:
        message = f"今天是{month}月{day}日\n"
        message += f"历史上的{event['year']}年的今天：\n"
        message += f"{event['content']}\n\n"
        
        if related_links:
            message += "相关链接：\n"
            for i, link in enumerate(related_links, 1):
                message += f"{i}. {link}\n"
        else:
            message += "暂无相关链接。\n"
        
        return message
    except Exception as e:
        logger.error(f"格式化消息失败: {str(e)}")
        return "消息格式化失败，请稍后重试。"

def show_history_window():
    """显示历史上的今天窗口"""
    # 创建主窗口
    root = tk.Tk()
    root.title("历史上的今天")
    
    # 设置窗口大小
    window_width = 400
    window_height = 400
    
    # 获取屏幕尺寸
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # 计算窗口居中的位置
    center_x = int((screen_width - window_width) / 2)
    center_y = int((screen_height - window_height) / 2)
    
    # 设置窗口大小和位置
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    
    # 创建可滚动文本框，设置字体为黑体，大小为12
    text_area = scrolledtext.ScrolledText(
        root, 
        wrap=tk.WORD, 
        width=40,
        height=20,
        font=('SimHei', 12)
    )
    text_area.pack(padx=10, pady=10, expand=True, fill='both')
    
    # 添加超链接支持
    text_area.tag_config("hyperlink", foreground="blue", underline=1)
    
    def open_link(url):
        import webbrowser
        webbrowser.open(url)
    
    def format_and_insert_content():
        content = get_today_in_history()
        text_area.delete(1.0, tk.END)
        
        # 分割内容，分别处理普通文本和链接
        lines = content.split('\n')
        for line in lines:
            if line.startswith("维基百科原文: ") or line.startswith("相关链接"):
                text_area.insert(tk.END, line + '\n')
            elif ": http" in line:  # 这是一个链接行
                title, url = line.split(": ", 1)
                if title.isdigit():  # 如果是数字编号
                    text_area.insert(tk.END, f"{title}. ")
                    text_area.insert(tk.END, url, "hyperlink")
                    text_area.insert(tk.END, "\n")
                else:
                    text_area.insert(tk.END, f"{title}: ")
                    text_area.insert(tk.END, url, "hyperlink")
                    text_area.insert(tk.END, "\n")
                
                # 为每个链接添加点击事件
                tag_name = f"link_{text_area.index('end-2c linestart')}"
                text_area.tag_add(tag_name, f"end-{len(url)+1}c", "end-1c")
                text_area.tag_config(tag_name, foreground="blue", underline=1)
                text_area.tag_bind(tag_name, "<Button-1>", lambda e, url=url: open_link(url))
                text_area.tag_bind(tag_name, "<Enter>", lambda e: text_area.config(cursor="hand2"))
                text_area.tag_bind(tag_name, "<Leave>", lambda e: text_area.config(cursor=""))
            else:
                text_area.insert(tk.END, line + '\n')
    
    # 显示初始内容
    format_and_insert_content()
    text_area.config(state='disabled')
    
    # 创建按钮框架
    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)
    
    # 定义刷新函数
    def refresh():
        text_area.config(state='normal')
        format_and_insert_content()
        text_area.config(state='disabled')
    
    # 创建刷新按钮
    refresh_btn = tk.Button(
        button_frame,
        text="↻ 刷新",
        command=refresh,
        font=('SimHei', 14),
        width=8,  # 减小横向宽度
        height=12,  # 增加纵向高度
        relief=tk.RAISED,
        bd=3
    )
    refresh_btn.pack(pady=10)
    
    # 运行窗口
    root.mainloop()

if __name__ == "__main__":
    show_history_window()
