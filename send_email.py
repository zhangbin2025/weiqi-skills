#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单邮件发送脚本
支持 QQ 邮箱、163 邮箱等
支持附件发送

使用方法:
    # 发送纯文本邮件
    python3 send_email.py --to 195021300@qq.com --subject "测试邮件" --body "邮件内容"
    
    # 发送带附件的邮件
    python3 send_email.py --to 195021300@qq.com --subject "测试邮件" --body "邮件内容" --attach file.pdf
    
    # 发送多个附件
    python3 send_email.py --to 195021300@qq.com --subject "测试邮件" --body "邮件内容" --attach file1.pdf --attach file2.jpg
"""

import smtplib
import argparse
import os
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email.header import Header
from email import encoders

# ==================== 邮件配置 ====================
# 请修改以下配置

# 发件人邮箱（例如你的 QQ 邮箱）
FROM_EMAIL = "195021300@qq.com"

# SMTP 服务器配置
# QQ 邮箱: smtp.qq.com, 端口 465 (SSL)
# 163 邮箱: smtp.163.com, 端口 465 (SSL)
# Gmail: smtp.gmail.com, 端口 587 (TLS)
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465  # SSL 端口

# 邮箱授权码（不是登录密码！）
# QQ 邮箱授权码获取: 设置 -> 账户 -> 开启 SMTP -> 生成授权码
EMAIL_PASSWORD = "cvngujkpmwunbjci"

# 收件人邮箱（默认）
DEFAULT_TO_EMAIL = "195021300@qq.com"

# ==================================================

def encode_filename(filename):
    """对文件名进行 RFC 2047 编码，支持中文文件名"""
    from email.header import Header
    return Header(filename, 'utf-8').encode()


def add_attachment(msg, filepath):
    """
    添加附件到邮件
    
    参数:
        msg: MIMEMultipart 对象
        filepath: 附件文件路径
    """
    if not os.path.exists(filepath):
        print(f"⚠️  附件不存在，已跳过: {filepath}")
        return False
    
    try:
        filename = os.path.basename(filepath)
        
        # 猜测文件类型
        content_type, encoding = mimetypes.guess_type(filepath)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        main_type, sub_type = content_type.split('/', 1)
        
        # 读取文件内容
        with open(filepath, 'rb') as f:
            file_data = f.read()
        
        # 根据文件类型选择 MIME 类型
        if main_type == 'text':
            # 文本文件
            attachment = MIMEText(file_data.decode('utf-8', errors='ignore'), _subtype=sub_type, _charset='utf-8')
        elif main_type == 'image':
            # 图片文件
            from email.mime.image import MIMEImage
            attachment = MIMEImage(file_data, _subtype=sub_type)
        elif main_type == 'audio':
            # 音频文件
            from email.mime.audio import MIMEAudio
            attachment = MIMEAudio(file_data, _subtype=sub_type)
        elif main_type == 'application' and sub_type == 'pdf':
            # PDF 文件
            attachment = MIMEApplication(file_data, _subtype='pdf')
        else:
            # 其他文件类型
            attachment = MIMEBase(main_type, sub_type)
            attachment.set_payload(file_data)
            encoders.encode_base64(attachment)
        
        # 添加 Content-Disposition 头，使用 RFC 2047 编码文件名
        attachment.add_header('Content-Disposition', 'attachment', filename=encode_filename(filename))
        msg.attach(attachment)
        
        print(f"📎 已添加附件: {filename} ({len(file_data)} bytes)")
        return True
        
    except Exception as e:
        print(f"⚠️  添加附件失败 {filepath}: {e}")
        return False


def send_email(to_email, subject, body, attachments=None, from_email=None, password=None, smtp_server=None, smtp_port=None):
    """
    发送邮件
    
    参数:
        to_email: 收件人邮箱
        subject: 邮件主题
        body: 邮件内容
        attachments: 附件路径列表（可选）
        from_email: 发件人邮箱（可选，使用默认配置）
        password: 邮箱授权码（可选，使用默认配置）
        smtp_server: SMTP 服务器（可选，使用默认配置）
        smtp_port: SMTP 端口（可选，使用默认配置）
    """
    # 使用默认配置
    from_email = from_email or FROM_EMAIL
    password = password or EMAIL_PASSWORD
    smtp_server = smtp_server or SMTP_SERVER
    smtp_port = smtp_port or SMTP_PORT
    attachments = attachments or []
    
    # 检查配置
    if from_email == "your_email@qq.com" or not password or password == "your_auth_code":
        print("❌ 请先配置邮件信息！")
        print("请编辑脚本，修改以下配置:")
        print(f"  FROM_EMAIL = '你的邮箱地址'")
        print(f"  EMAIL_PASSWORD = '你的邮箱授权码'")
        print(f"  SMTP_SERVER = 'smtp.qq.com'  # 根据邮箱类型修改")
        print()
        print("获取 QQ 邮箱授权码:")
        print("  1. 登录 QQ 邮箱网页版")
        print("  2. 设置 -> 账户 -> 开启 SMTP 服务")
        print("  3. 生成授权码")
        return False
    
    try:
        # 创建混合类型邮件
        msg = MIMEMultipart('mixed')
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = Header(subject, 'utf-8')
        
        # 添加邮件正文
        text_part = MIMEText(body, 'plain', 'utf-8')
        msg.attach(text_part)
        
        # 添加附件
        if attachments:
            print(f"📎 正在处理 {len(attachments)} 个附件...")
            attached_count = 0
            for filepath in attachments:
                if add_attachment(msg, filepath):
                    attached_count += 1
            print(f"✅ 成功添加 {attached_count} 个附件")
        
        # 连接 SMTP 服务器并发送
        print(f"📧 正在连接 {smtp_server}:{smtp_port}...")
        
        if smtp_port == 465:
            # SSL 连接
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # TLS 连接
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        
        print(f"🔐 正在登录 {from_email}...")
        server.login(from_email, password)
        
        print(f"📤 正在发送邮件到 {to_email}...")
        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        
        print("✅ 邮件发送成功！")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ 登录失败: {e}")
        print("请检查邮箱地址和授权码是否正确")
        return False
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='发送邮件脚本（支持附件）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 发送纯文本邮件
  python3 send_email.py --to 195021300@qq.com --subject "测试" --body "内容"
  
  # 发送带附件的邮件
  python3 send_email.py --to 195021300@qq.com --subject "报告" --body "请查收附件" --attach report.pdf
  
  # 发送多个附件
  python3 send_email.py --to 195021300@qq.com --subject "资料" --body "附件" --attach file1.pdf --attach file2.jpg
        """
    )
    parser.add_argument('--to', default=DEFAULT_TO_EMAIL, help='收件人邮箱')
    parser.add_argument('--subject', '-s', default='测试邮件', help='邮件主题')
    parser.add_argument('--body', '-b', default='这是一封测试邮件。\n\n如果你收到这封邮件，说明邮件发送功能正常工作。\n\n发送时间: ' + __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'), help='邮件内容')
    parser.add_argument('--attach', '-a', action='append', help='附件路径（可多次使用添加多个附件）')
    parser.add_argument('--from-email', '-f', help='发件人邮箱（覆盖默认配置）')
    parser.add_argument('--password', '-p', help='邮箱授权码（覆盖默认配置）')

    args = parser.parse_args()

    # 如果没有提供密码，尝试从环境变量获取
    password = args.password or os.environ.get('EMAIL_PASSWORD') or EMAIL_PASSWORD

    # 如果没有提供发件人邮箱，尝试从环境变量获取
    from_email = args.from_email or os.environ.get('FROM_EMAIL') or FROM_EMAIL

    # 发送邮件
    send_email(
        to_email=args.to,
        subject=args.subject,
        body=args.body,
        attachments=args.attach,
        from_email=from_email,
        password=password
    )


if __name__ == "__main__":
    main()
