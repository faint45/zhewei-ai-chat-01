#!/usr/bin/env python3
"""
築未科技大腦 - 密碼雜湊生成工具
Phase 1.4 安全加固：生成 SHA-256 密碼雜湊值

使用方法：
    python generate_password_hash.py

然後將生成的雜湊值複製到 .env 文件的 ADMIN_PASSWORD_HASH 欄位
"""
import hashlib
import getpass

def generate_password_hash(password: str) -> str:
    """生成 SHA-256 密碼雜湊"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def main():
    print("=" * 60)
    print("築未科技大腦 - 密碼雜湊生成工具")
    print("=" * 60)
    print()
    print("此工具將生成安全的密碼雜湊值，用於 .env 文件配置")
    print()

    # 輸入密碼（不顯示）
    password = getpass.getpass("請輸入管理員密碼: ")
    if not password:
        print("錯誤：密碼不能為空")
        return

    # 確認密碼
    password_confirm = getpass.getpass("請再次輸入密碼確認: ")
    if password != password_confirm:
        print("錯誤：兩次輸入的密碼不一致")
        return

    # 生成雜湊
    hashed = generate_password_hash(password)

    print()
    print("=" * 60)
    print("密碼雜湊生成成功！")
    print("=" * 60)
    print()
    print("請將以下內容添加到 .env 文件：")
    print()
    print(f"ADMIN_PASSWORD_HASH={hashed}")
    print()
    print("注意事項：")
    print("1. 請妥善保管此雜湊值，不要洩露")
    print("2. 建議同時移除 .env 中的 ADMIN_PASSWORD 明文密碼")
    print("3. 如需修改密碼，請重新運行此工具生成新的雜湊值")
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()
