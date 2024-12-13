import requests
import random
from datetime import datetime
from bs4 import BeautifulSoup
import json
import tkinter as tk
from tkinter import scrolledtext
import logging
from PIL import Image, ImageTk, ImageDraw, ImageFont
import io
import base64
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
import threading
from queue import Queue


# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class HistoricalEvent:
    year: int
    content: str
    wiki_link: str
    related_links: List[str] = field(default_factory=list)
    is_read: bool = False

class HistoryManager:
    def __init__(self):
        self.events: List[HistoricalEvent] = []
        self.today = datetime.now()
        self.event_queue = Queue()
        self.is_loading = False
        
    def fetch_events_async(self):
        """异步获取历史事件"""
        if self.is_loading:
            return
            
        def background_fetch():
            self.is_loading = True
            url = f"https://zh.wikipedia.org/api/rest_v1/feed/onthisday/events/{self.today.month:02d}/{self.today.day:02d}"
            try:
                response = requests.get(url, headers={"User-Agent": "HistoryBot/1.0"}, timeout=10)
                data = response.json()
                
                for event in data.get('events', []):
                    year = event.get('year')
                    content = event.get('text', '')
                    wiki_link = None
                    if event.get('pages'):
                        wiki_link = event['pages'][0].get('content_urls', {}).get('desktop', {}).get('page', '')
                    
                    if year and content and not any(e.year == year for e in self.events):
                        new_event = HistoricalEvent(year=year, content=content, wiki_link=wiki_link)
                        self.events.append(new_event)
                        self.event_queue.put(new_event)
                        
                        # 异步获取相关链接
                        def fetch_links():
                            try:
                                related_links = get_bing_links(f"{year} {content}")
                                if not related_links and wiki_link:  # 如果Bing链接获取失败且有维基链接
                                    new_event.related_links = [f"维基百科详情: {wiki_link}"]
                                else:
                                    new_event.related_links = related_links
                            except Exception as e:
                                logger.error(f"获取相关链接失败: {str(e)}")
                                if wiki_link:  # 发生异常时使用维基链接
                                    new_event.related_links = [f"维基百科详情: {wiki_link}"]
                        threading.Thread(target=fetch_links).start()
                        
            except Exception as e:
                logger.error(f"获取历史事件失败: {str(e)}")
            finally:
                self.is_loading = False
        
        thread = threading.Thread(target=background_fetch)
        thread.daemon = True
        thread.start()
    
    def get_next_event(self) -> Optional[HistoricalEvent]:
        """获取下一个事件"""
        # 如果队列为空且没有在加载，开始异步加载
        if self.event_queue.empty() and not self.is_loading:
            self.fetch_events_async()
        
        # 尝试从队列获取事件
        try:
            event = self.event_queue.get_nowait()
            event.is_read = True
            return event
        except:
            return None

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

def show_history_window():
    root = tk.Tk()
    root.title("历史上的今天")
    
    # 设置窗口大小
    window_width = 400
    window_height = 400
    
    # 获取屏幕尺寸
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # 计算窗口居中的位���
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
    
    # 创建史管理器
    history_manager = HistoryManager()
    
    def format_and_insert_content():
        event = history_manager.get_next_event()
        if event is None:
            if history_manager.is_loading:
                content = "正在加载更多历史事件..."
            else:
                content = "已显示完所有历史上的今天发生的著名事件。"
        else:
            content = f"今天是{history_manager.today.month}月{history_manager.today.day}日\n"
            content += f"历史上的{event.year}年的今天：\n"
            content += f"{event.content}\n\n"
            
            if event.wiki_link:
                content += f"维基百科原文: {event.wiki_link}\n"
            
            if event.related_links:
                content += "\n相关链接：\n"
                for i, link in enumerate(event.related_links, 1):
                    content += f"{i}. {link}\n"
        
        text_area.delete(1.0, tk.END)
        lines = content.split('\n')
        for line in lines:
            if "http" in line:
                text_area.insert(tk.END, line + '\n', "hyperlink")
                text_area.tag_bind("hyperlink", "<Button-1>", 
                    lambda e, url=line.split(": ")[1]: open_link(url))
            else:
                text_area.insert(tk.END, line + '\n')
    
    # 开始异步加载数据
    history_manager.fetch_events_async()
    # 显示第一条内容
    format_and_insert_content()
    
    # 定义自动刷新函数
    def auto_refresh():
        if history_manager.is_loading:
            format_and_insert_content()
            root.after(1000, auto_refresh)  # 每秒检查一次新数据
    
    # 启动自动刷新
    auto_refresh()
    
    root.mainloop()

if __name__ == "__main__":
    show_history_window()
