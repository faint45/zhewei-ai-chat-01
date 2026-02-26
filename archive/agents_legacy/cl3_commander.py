"""
CL3 指令台 - 民雄監控中心，圖形化對話介面
"""
from system_launcher import initialize_system
from chat_gui import ChatGUI

if __name__ == "__main__":
    initialize_system()
    app = ChatGUI()
    app.run()
