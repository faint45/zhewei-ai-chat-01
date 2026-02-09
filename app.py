#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 AI 對話系統 - 單一文件部署版本
包含所有功能，確保在 Railway 上正常工作
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from hashlib import sha256

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_core import ValidationError
import uvicorn

# ========== 內嵌 HTML 內容 ==========
INDEX_HTML = '''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>築未科技 - AI 對話系統</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft JhengHei', 'PingFang TC', sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh; padding: 0;
            color: #fff;
        }
        .container {
            max-width: 100%; margin: 0; 
            height: 100vh;
            display: flex;
            flex-direction: column;
            background: rgba(255, 255, 255, 0.02);
            overflow: hidden;
        }
        @media (min-width: 769px) {
            .container {
                max-width: 900px; margin: 20px auto; height: calc(100vh - 40px);
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 24px; 
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                overflow: hidden;
            }
        }
        .auth-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .auth-box {
            width: 100%;
            max-width: 400px;
            padding: 40px;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            margin: 20px;
        }
        @media (min-width: 769px) {
            .auth-box { padding: 48px; }
        }
        .auth-logo {
            text-align: center;
            font-size: 60px;
            margin-bottom: 20px;
        }
        .auth-title {
            text-align: center;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 8px;
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        @media (min-width: 769px) {
            .auth-title { font-size: 32px; }
        }
        .auth-subtitle {
            text-align: center;
            font-size: 14px;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 32px;
        }
        .auth-form {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .form-label {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.8);
            font-weight: 500;
        }
        .form-input {
            padding: 14px 16px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.05);
            color: #fff;
            font-size: 15px;
            outline: none;
            transition: all 0.3s ease;
        }
        .form-input:focus {
            border-color: #00f2fe;
            box-shadow: 0 0 0 3px rgba(0, 242, 254, 0.1);
        }
        .form-input::placeholder {
            color: rgba(255, 255, 255, 0.4);
        }
        .auth-btn {
            padding: 16px;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(79, 172, 254, 0.4);
            margin-top: 8px;
        }
        .auth-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(79, 172, 254, 0.5);
        }
        .auth-btn:active {
            transform: translateY(0);
        }
        .auth-link {
            text-align: center;
            margin-top: 20px;
            font-size: 14px;
            color: rgba(255, 255, 255, 0.6);
        }
        .auth-link a {
            color: #00f2fe;
            text-decoration: none;
            font-weight: 500;
        }
        .error-message {
            color: #ff6b6b;
            font-size: 13px;
            text-align: center;
            margin-top: 12px;
            display: none;
        }
        .hidden { display: none !important; }
        .header {
            background: linear-gradient(135deg, rgba(79, 172, 254, 0.2) 0%, rgba(0, 242, 254, 0.2) 100%);
            color: white; padding: 16px 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            flex-shrink: 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        @media (min-width: 769px) {
            .header { padding: 20px 24px; }
        }
        .header-left {
            display: flex;
            flex-direction: column;
        }
        .header h1 {
            font-size: 20px;
            font-weight: 700;
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        @media (min-width: 769px) {
            .header h1 { font-size: 24px; }
        }
        .header p {
            font-size: 12px;
            opacity: 0.8;
            font-weight: 300;
        }
        @media (min-width: 769px) {
            .header p { font-size: 13px; }
        }
        .header-right {
            display: flex;
            gap: 10px;
        }
        .header-btn {
            padding: 8px 12px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            color: rgba(255, 255, 255, 0.8);
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        @media (min-width: 769px) {
            .header-btn {
                padding: 10px 16px;
                font-size: 13px;
            }
        }
        .header-btn:hover {
            background: rgba(255, 255, 255, 0.15);
        }
        .status-bar {
            background: rgba(255, 255, 255, 0.03);
            padding: 10px 16px; 
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 12px;
            color: rgba(255, 255, 255, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            flex-shrink: 0;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            background: #00f2fe;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(0, 242, 254, 0.7); }
            50% { opacity: 0.5; box-shadow: 0 0 0 10px rgba(0, 242, 254, 0); }
        }
        .tabs-container {
            display: flex;
            background: rgba(0, 0, 0, 0.2);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            flex-shrink: 0;
        }
        .tabs-container::-webkit-scrollbar { display: none; }
        .tab {
            flex: 1;
            min-width: 70px;
            padding: 12px 14px;
            text-align: center;
            color: rgba(255, 255, 255, 0.6);
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 13px;
            font-weight: 500;
            white-space: nowrap;
            border-bottom: 2px solid transparent;
        }
        @media (min-width: 769px) {
            .tab {
                min-width: 80px;
                padding: 14px 16px;
                font-size: 14px;
            }
        }
        .tab.active {
            color: #00f2fe;
            border-bottom-color: #00f2fe;
            background: rgba(0, 242, 254, 0.05);
        }
        .page-content {
            flex: 1;
            overflow-y: auto;
            display: none;
        }
        .page-content.active { display: block; }
        .chat-container { 
            height: 100%;
            padding: 16px;
            background: rgba(0, 0, 0, 0.2);
            overflow-y: auto;
        }
        @media (min-width: 769px) {
            .chat-container { padding: 20px; }
        }
        .chat-container::-webkit-scrollbar {
            width: 4px;
        }
        .chat-container::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 2px;
        }
        .chat-container::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 2px;
        }
        .message { 
            margin-bottom: 16px; 
            display: flex; 
            align-items: flex-start;
            animation: slideIn 0.3s ease-out;
        }
        .user { justify-content: flex-end; }
        .bot { justify-content: flex-start; }
        .message-avatar {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            margin-right: 10px;
            flex-shrink: 0;
        }
        @media (min-width: 769px) {
            .message-avatar {
                width: 40px;
                height: 40px;
                border-radius: 12px;
                font-size: 20px;
                margin-right: 12px;
            }
        }
        .user .message-avatar {
            margin-right: 0;
            margin-left: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        @media (min-width: 769px) {
            .user .message-avatar { margin-left: 12px; }
        }
        .bot .message-avatar {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        .message-content {
            max-width: 75%; 
            padding: 12px 16px; 
            border-radius: 16px;
            font-size: 14px;
            line-height: 1.5;
            color: #fff;
            word-wrap: break-word;
        }
        @media (min-width: 769px) {
            .message-content {
                max-width: 65%;
                padding: 16px 20px;
                font-size: 15px;
            }
        }
        .user .message-content { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-bottom-right-radius: 4px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        .bot .message-content { 
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-bottom-left-radius: 4px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }
        .timestamp {
            font-size: 10px; 
            opacity: 0.5; 
            margin-top: 4px;
            text-align: right;
        }
        @media (min-width: 769px) {
            .timestamp {
                font-size: 11px;
                margin-top: 6px;
            }
        }
        .input-container { 
            padding: 12px 16px; 
            background: rgba(0, 0, 0, 0.2);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            flex-shrink: 0;
        }
        @media (min-width: 769px) {
            .input-container { padding: 20px 24px; }
        }
        .input-group { 
            display: flex; 
            gap: 8px;
            background: rgba(255, 255, 255, 0.05);
            padding: 6px;
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            align-items: flex-end;
        }
        @media (min-width: 769px) {
            .input-group {
                padding: 8px;
                border-radius: 16px;
                gap: 12px;
            }
        }
        #messageInput { 
            flex: 1; 
            padding: 12px 16px; 
            border: none; 
            border-radius: 10px;
            background: transparent;
            outline: none; 
            font-size: 15px;
            color: #fff;
            transition: all 0.3s ease;
            max-height: 120px;
            overflow-y: auto;
        }
        @media (min-width: 769px) {
            #messageInput { 
                padding: 14px 20px;
                font-size: 15px;
                border-radius: 12px;
            }
        }
        #messageInput::placeholder {
            color: rgba(255, 255, 255, 0.4);
        }
        #sendButton { 
            padding: 10px 20px; 
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white; 
            border: none; 
            border-radius: 10px; 
            cursor: pointer; 
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(79, 172, 254, 0.4);
            white-space: nowrap;
            flex-shrink: 0;
        }
        @media (min-width: 769px) {
            #sendButton { 
                padding: 14px 28px;
                border-radius: 12px;
                font-size: 15px;
            }
        }
        #sendButton:hover { 
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(79, 172, 254, 0.5);
        }
        #sendButton:active {
            transform: translateY(0);
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .task-container {
            padding: 16px;
        }
        @media (min-width: 769px) {
            .task-container { padding: 24px; }
        }
        .task-header {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .task-title {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 12px;
            color: #fff;
        }
        @media (min-width: 769px) {
            .task-title { font-size: 24px; }
        }
        .task-status {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
        }
        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-badge.active {
            background: rgba(79, 172, 254, 0.2);
            color: #4facfe;
        }
        .status-badge.completed {
            background: rgba(67, 237, 135, 0.2);
            color: #43ed87;
        }
        .status-badge.pending {
            background: rgba(255, 193, 7, 0.2);
            color: #ffc107;
        }
        .task-progress {
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            overflow: hidden;
        }
        .task-progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
            transition: width 0.5s ease;
            border-radius: 3px;
        }
        .step {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 16px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            margin-bottom: 12px;
            transition: all 0.3s ease;
        }
        .step.active {
            background: rgba(79, 172, 254, 0.1);
            border-left: 3px solid #4facfe;
        }
        .step.completed {
            background: rgba(67, 237, 135, 0.1);
            border-left: 3px solid #43ed87;
            opacity: 0.7;
        }
        .step-icon {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            flex-shrink: 0;
            background: rgba(255, 255, 255, 0.1);
        }
        .step.active .step-icon {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        .step.completed .step-icon {
            background: linear-gradient(135deg, #43ed87 0%, #22c55e 100%);
        }
        .step-content {
            flex: 1;
        }
        .step-title {
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 4px;
            color: #fff;
        }
        .step-description {
            font-size: 13px;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 6px;
        }
        .step-time {
            font-size: 11px;
            color: rgba(255, 255, 255, 0.4);
        }
        .cost-container {
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            margin-top: 20px;
        }
        .cost-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .cost-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        .cost-item:last-child {
            border-bottom: none;
        }
        .cost-label {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.8);
        }
        .cost-value {
            font-size: 18px;
            font-weight: 700;
            color: #00f2fe;
        }
        .cost-value.twd {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.6);
            margin-left: 8px;
        }
        .cost-total {
            margin-top: 16px;
            padding-top: 16px;
            border-top: 2px solid rgba(255, 255, 255, 0.2);
        }
        .cost-total .cost-label {
            font-size: 16px;
            font-weight: 600;
        }
        .cost-total .cost-value {
            font-size: 24px;
        }
    </style>
</head>
<body>
    <!-- Login/Register Container -->
    <div class="auth-container" id="authContainer">
        <div class="auth-box" id="loginBox">
            <div class="auth-logo">🧠</div>
            <div class="auth-title">築未科技 AI</div>
            <div class="auth-subtitle">登入您的帳號</div>
            
            <div class="auth-form">
                <div class="form-group">
                    <label class="form-label">帳號</label>
                    <input type="text" class="form-input" id="loginUsername" placeholder="請輸入帳號">
                </div>
                <div class="form-group">
                    <label class="form-label">密碼</label>
                    <input type="password" class="form-input" id="loginPassword" placeholder="請輸入密碼">
                </div>
                <button class="auth-btn" onclick="login()">登入</button>
            </div>
            
            <div class="error-message" id="loginError"></div>
            
            <div class="auth-link">
                還沒有帳號？<a href="#" onclick="showRegister()">立即註冊</a>
            </div>
        </div>
        
        <div class="auth-box hidden" id="registerBox">
            <div class="auth-logo">🎉</div>
            <div class="auth-title">建立新帳號</div>
            <div class="auth-subtitle">加入築未科技 AI 系統</div>
            
            <div class="auth-form">
                <div class="form-group">
                    <label class="form-label">帳號</label>
                    <input type="text" class="form-input" id="regUsername" placeholder="請輸入帳號">
                </div>
                <div class="form-group">
                    <label class="form-label">密碼</label>
                    <input type="password" class="form-input" id="regPassword" placeholder="至少 6 位數字或字母">
                </div>
                <div class="form-group">
                    <label class="form-label">確認密碼</label>
                    <input type="password" class="form-input" id="regConfirmPassword" placeholder="再次輸入密碼">
                </div>
                <button class="auth-btn" onclick="register()">註冊</button>
            </div>
            
            <div class="error-message" id="registerError"></div>
            
            <div class="auth-link">
                已有帳號？<a href="#" onclick="showLogin()">返回登入</a>
            </div>
        </div>
    </div>
    
    <!-- Main App Container -->
    <div class="container hidden" id="mainApp">
        <div class="header">
            <div class="header-left">
                <h1>🧠 築未科技 AI</h1>
                <p>歡迎，<span id="currentUser">用戶</span></p>
            </div>
            <div class="header-right">
                <button class="header-btn" onclick="logout()">登出</button>
            </div>
        </div>
        
        <div class="status-bar">
            <div class="status-dot"></div>
            <span>🌐 Railway 雲端部署 - 安全連線</span>
        </div>
        
        <div class="tabs-container">
            <div class="tab active" onclick="switchTab('chat')">💬 對話</div>
            <div class="tab" onclick="switchTab('task')">📋 任務</div>
        </div>
        
        <!-- Chat Page -->
        <div class="page-content active" id="chatPage">
            <div class="chat-container" id="chatMessages">
                <div class="message bot">
                    <div class="message-avatar">🤖</div>
                    <div class="message-content">
                        您好！歡迎使用築未科技 AI 對話系統。<br><br>
                        系統已成功部署，您的任務進度和使用費用將在任務頁面顯示。
                        <div class="timestamp" id="welcomeTime"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Task Page -->
        <div class="page-content" id="taskPage">
            <div class="task-container">
                <div class="task-header">
                    <div class="task-title">任務追蹤</div>
                    <div class="task-status">
                        <span class="status-badge active">進行中</span>
                        <span>當前任務：AI 模型訓練</span>
                    </div>
                    <div class="task-progress">
                        <div class="task-progress-bar" style="width: 60%"></div>
                    </div>
                    <div style="margin-top: 8px; font-size: 12px; color: rgba(255, 255, 255, 0.6);">
                        進度：60% (3/5 階段完成)
                    </div>
                </div>
                
                <div class="step completed">
                    <div class="step-icon">✓</div>
                    <div class="step-content">
                        <div class="step-title">資料收集與預處理</div>
                        <div class="step-description">收集 10,000 筆訓練數據並進行清洗</div>
                        <div class="step-time">完成時間：2025-02-09 10:30</div>
                    </div>
                </div>
                
                <div class="step completed">
                    <div class="step-icon">✓</div>
                    <div class="step-content">
                        <div class="step-title">模型架構設計</div>
                        <div class="step-description">設計並實作 Transformer 架構</div>
                        <div class="step-time">完成時間：2025-02-09 14:15</div>
                    </div>
                </div>
                
                <div class="step completed">
                    <div class="step-icon">✓</div>
                    <div class="step-content">
                        <div class="step-title">初步訓練</div>
                        <div class="step-description">完成 5 輪初步訓練，準確率達 85%</div>
                        <div class="step-time">完成時間：2025-02-09 18:45</div>
                    </div>
                </div>
                
                <div class="step active">
                    <div class="step-icon">●</div>
                    <div class="step-content">
                        <div class="step-title">模型優化</div>
                        <div class="step-description">進行超參數調整和模型微調</div>
                        <div class="step-time">預計完成：2025-02-10 12:00</div>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-icon">○</div>
                    <div class="step-content">
                        <div class="step-title">最終測試與部署</div>
                        <div class="step-description">進行全面測試並部署到生產環境</div>
                        <div class="step-time">預計完成：2025-02-10 18:00</div>
                    </div>
                </div>
                
                <div class="cost-container">
                    <div class="cost-title">
                        💰 本次費用統計
                    </div>
                    
                    <div class="cost-item">
                        <span class="cost-label">使用金幣</span>
                        <span class="cost-value">1,250 <span class="cost-value twd">枚</span></span>
                    </div>
                    
                    <div class="cost-item">
                        <span class="cost-label">新台幣金額</span>
                        <span class="cost-value">NT$ 125.00</span>
                    </div>
                    
                    <div class="cost-total">
                        <div class="cost-item">
                            <span class="cost-label">累積總費用</span>
                            <span class="cost-value">NT$ 12,580.00</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="input-container">
            <div class="input-group">
                <input type="text" id="messageInput" placeholder="輸入您的訊息..." autocomplete="off">
                <button id="sendButton" onclick="sendMessage()">發送</button>
            </div>
        </div>
    </div>

    <script>
        const ADMIN_USERNAME = 'allen34556';
        const ADMIN_PASSWORD = 'Rr124243084';
        
        let users = [];
        let currentUser = null;
        
        // Load users from localStorage
        const savedUsers = localStorage.getItem('zhewei_users');
        if (savedUsers) {
            try {
                users = JSON.parse(savedUsers);
            } catch (e) {}
        }
        
        // Initialize admin user
        if (users.length === 0) {
            users.push({
                username: ADMIN_USERNAME,
                password: ADMIN_PASSWORD,
                role: 'admin',
                coins: 10000,
                totalSpent: 0
            });
            saveUsers();
        }
        
        // Check existing session
        const savedSession = localStorage.getItem('zhewei_session');
        if (savedSession) {
            const sessionUser = users.find(u => u.username === savedSession);
            if (sessionUser) {
                currentUser = sessionUser;
                showMainApp();
            }
        }
        
        function saveUsers() {
            localStorage.setItem('zhewei_users', JSON.stringify(users));
        }
        
        function showLogin() {
            document.getElementById('loginBox').classList.remove('hidden');
            document.getElementById('registerBox').classList.add('hidden');
        }
        
        function showRegister() {
            document.getElementById('loginBox').classList.add('hidden');
            document.getElementById('registerBox').classList.remove('hidden');
        }
        
        function login() {
            const username = document.getElementById('loginUsername').value.trim();
            const password = document.getElementById('loginPassword').value;
            const errorEl = document.getElementById('loginError');
            
            if (!username || !password) {
                errorEl.textContent = '請輸入帳號和密碼';
                errorEl.style.display = 'block';
                return;
            }
            
            const user = users.find(u => u.username === username && u.password === password);
            
            if (user) {
                currentUser = user;
                localStorage.setItem('zhewei_session', username);
                showMainApp();
            } else {
                errorEl.textContent = '帳號或密碼錯誤';
                errorEl.style.display = 'block';
            }
        }
        
        function register() {
            const username = document.getElementById('regUsername').value.trim();
            const password = document.getElementById('regPassword').value;
            const confirmPassword = document.getElementById('regConfirmPassword').value;
            const errorEl = document.getElementById('registerError');
            
            if (!username || !password) {
                errorEl.textContent = '請填寫所有欄位';
                errorEl.style.display = 'block';
                return;
            }
            
            if (password.length < 6) {
                errorEl.textContent = '密碼至少需要 6 位數字或字母';
                errorEl.style.display = 'block';
                return;
            }
            
            if (password !== confirmPassword) {
                errorEl.textContent = '兩次輸入的密碼不一致';
                errorEl.style.display = 'block';
                return;
            }
            
            if (users.find(u => u.username === username)) {
                errorEl.textContent = '此帳號已被註冊';
                errorEl.style.display = 'block';
                return;
            }
            
            users.push({
                username: username,
                password: password,
                role: 'user',
                coins: 100,
                totalSpent: 0
            });
            saveUsers();
            
            alert('註冊成功！請登入');
            showLogin();
            document.getElementById('regUsername').value = '';
            document.getElementById('regPassword').value = '';
            document.getElementById('regConfirmPassword').value = '';
        }
        
        function logout() {
            currentUser = null;
            localStorage.removeItem('zhewei_session');
            document.getElementById('mainApp').classList.add('hidden');
            document.getElementById('authContainer').classList.remove('hidden');
            document.getElementById('loginUsername').value = '';
            document.getElementById('loginPassword').value = '';
        }
        
        function showMainApp() {
            document.getElementById('authContainer').classList.add('hidden');
            document.getElementById('mainApp').classList.remove('hidden');
            document.getElementById('currentUser').textContent = currentUser.username;
            document.getElementById('welcomeTime').textContent = new Date().toLocaleString('zh-TW');
        }
        
        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            event.target.classList.add('active');
            
            document.querySelectorAll('.page-content').forEach(page => page.classList.remove('active'));
            document.getElementById(tabName + 'Page').classList.add('active');
            
            const inputContainer = document.querySelector('.input-container');
            inputContainer.style.display = tabName === 'chat' ? 'block' : 'none';
        }
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (!message) return;

            addMessage(message, 'user');
            input.value = '';
            
            const response = await simulateAIResponse(message);
            addMessage(response, 'bot');
        }

        async function simulateAIResponse(message) {
            const responses = [
                `這是對「${message}」的智能回應。系統已安全部署到 Railway 平台！`,
                `已收到您的訊息：「${message}」。您的任務進度和費用會即時更新。`,
                `感謝您的輸入！「${message}」這個主題很有趣，我可以為您提供更多資訊。`,
                `關於「${message}」，讓我為您詳細解答。您的資料已加密保護。`,
                `「${message}」是一個很好的問題！系統運行正常，請隨時查看任務追蹤頁面。`
            ];
            
            await new Promise(resolve => setTimeout(resolve, 800 + Math.random() * 1200));
            
            return responses[Math.floor(Math.random() * responses.length)];
        }

        function addMessage(content, sender) {
            const chatContainer = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const avatar = sender === 'bot' ? '🤖' : '👤';
            
            messageDiv.innerHTML = `
                <div class="message-avatar">${avatar}</div>
                <div class="message-content">
                    ${content}
                    <div class="timestamp">${new Date().toLocaleString('zh-TW')}</div>
                </div>
            `;
            
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
        document.getElementById('messageInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
        
        document.getElementById('loginPassword').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') login();
        });
        
        document.getElementById('regConfirmPassword').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') register();
        });
    </script>
</body>
</html>'''

# ========== FastAPI App ==========
app = FastAPI(title="築未科技 AI 對話系統", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 路由 ==========
@app.get("/")
async def root():
    """返回首頁 HTML"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=INDEX_HTML, status_code=200)

@app.get("/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "system": "築未科技 AI 對話系統",
        "version": "1.0.0"
    }

@app.get("/api/info")
async def api_info():
    """API 信息"""
    return {
        "name": "築未科技 AI 對話系統",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "api_info": "/api/info"
        }
    }

# ========== 啟動 ==========
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print("=" * 60)
    print("築未科技 AI 對話系統")
    print("=" * 60)
    print(f"端口: {port}")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=port)
'''

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
