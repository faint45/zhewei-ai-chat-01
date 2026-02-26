/**
 * 築未科技 — Ntfy 推播訂閱模組 (隱形植入版)
 *
 * 用法：
 *   <script src="/static/modules/mod-ntfy-push.js"></script>
 *   <script>
 *     ZheweiPush.init({
 *       topic: "project_b_building",   // 必填：Ntfy topic
 *       onMessage: (msg) => { ... },   // 選填：自訂訊息處理
 *     });
 *   </script>
 *
 * 環境變數（由後端注入或寫死）：
 *   NTFY_SERVER  — Ntfy 伺服器 URL（預設 https://notify.zhewei.tech）
 *   NTFY_USER    — 唯讀帳號（預設 client_general）
 *   NTFY_PASS    — 唯讀密碼（預設空，需設定）
 *
 * 功能：
 *   1. 自動偵測 iOS PWA / Android / Desktop
 *   2. 嵌入唯讀認證（Base64 Authorization）
 *   3. SSE (EventSource) 即時監聽
 *   4. Notification API 彈出通知
 *   5. iOS fallback：偵測到 iOS 且非 PWA 時，引導加入主畫面
 *   6. 連線斷線自動重連（指數退避）
 *   7. 訊息歷史佇列（最近 50 則）
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.ZheweiPush = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  // ── 預設配置 ──────────────────────────────────────────────────
  var DEFAULTS = {
    server: "https://notify.zhewei.tech",
    user: "client_general",
    pass: "",                // ← 部署時填入唯讀密碼
    topic: "",
    icon: "/static/img/zhewei-icon-192.png",
    badge: "/static/img/zhewei-badge-72.png",
    brand: "\u54F2\u7DAD\u901A\u77E5",  // 哲維通知
    maxHistory: 50,
    reconnectBaseMs: 2000,
    reconnectMaxMs: 60000,
    debug: false,
  };

  // ── 內部狀態 ──────────────────────────────────────────────────
  var _cfg = Object.assign({}, DEFAULTS);
  var _eventSource = null;
  var _reconnectMs = DEFAULTS.reconnectBaseMs;
  var _reconnectTimer = null;
  var _history = [];
  var _listeners = {
    message: [],
    connect: [],
    disconnect: [],
    error: [],
    permission: [],
  };
  var _connected = false;
  var _permissionGranted = false;

  // ── 工具函式 ──────────────────────────────────────────────────

  function _log() {
    if (_cfg.debug) console.log.apply(console, ["[ZheweiPush]"].concat(Array.prototype.slice.call(arguments)));
  }

  function _warn() {
    console.warn.apply(console, ["[ZheweiPush]"].concat(Array.prototype.slice.call(arguments)));
  }

  function _emit(event, data) {
    (_listeners[event] || []).forEach(function (fn) {
      try { fn(data); } catch (e) { _warn("listener error:", e); }
    });
  }

  // ── 平台偵測 ──────────────────────────────────────────────────

  function _isIOS() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
      (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  }

  function _isAndroid() {
    return /Android/i.test(navigator.userAgent);
  }

  function _isPWA() {
    return window.matchMedia("(display-mode: standalone)").matches ||
      window.navigator.standalone === true;
  }

  function _isNotificationSupported() {
    return "Notification" in window;
  }

  // ── 權限請求 ──────────────────────────────────────────────────

  function _requestPermission() {
    return new Promise(function (resolve) {
      if (!_isNotificationSupported()) {
        _log("Notification API not supported");
        _emit("permission", { granted: false, reason: "not_supported" });
        resolve(false);
        return;
      }

      if (Notification.permission === "granted") {
        _permissionGranted = true;
        _emit("permission", { granted: true });
        resolve(true);
        return;
      }

      if (Notification.permission === "denied") {
        _warn("Notification permission denied by user");
        _emit("permission", { granted: false, reason: "denied" });
        resolve(false);
        return;
      }

      Notification.requestPermission().then(function (result) {
        _permissionGranted = result === "granted";
        _emit("permission", { granted: _permissionGranted, reason: result });
        resolve(_permissionGranted);
      }).catch(function () {
        _emit("permission", { granted: false, reason: "error" });
        resolve(false);
      });
    });
  }

  // ── 通知顯示 ──────────────────────────────────────────────────

  function _showNotification(msg) {
    if (!_permissionGranted) return;

    var title = msg.title || _cfg.brand;
    var options = {
      body: msg.message || msg.body || "",
      icon: msg.icon || _cfg.icon,
      badge: _cfg.badge,
      tag: msg.id || ("zw-" + Date.now()),
      data: { url: msg.click || msg.url || "", raw: msg },
      silent: false,
    };

    // 附件圖片
    if (msg.attachment && msg.attachment.url) {
      options.image = msg.attachment.url;
    }

    // 動作按鈕（最多 2 個）
    if (msg.actions && Array.isArray(msg.actions)) {
      options.actions = msg.actions.slice(0, 2).map(function (a) {
        return { action: a.action || a.label, title: a.label || a.action };
      });
    }

    try {
      if ("serviceWorker" in navigator && navigator.serviceWorker.controller) {
        // PWA 模式：透過 Service Worker 顯示
        navigator.serviceWorker.ready.then(function (reg) {
          reg.showNotification(title, options);
        });
      } else {
        // 一般模式：直接顯示
        var n = new Notification(title, options);
        n.onclick = function () {
          if (options.data.url) window.open(options.data.url, "_blank");
          n.close();
        };
      }
    } catch (e) {
      _warn("showNotification failed:", e);
    }
  }

  // ── SSE 連線 ──────────────────────────────────────────────────

  function _buildUrl() {
    var base = _cfg.server.replace(/\/+$/, "");
    var topic = encodeURIComponent(_cfg.topic);
    return base + "/" + topic + "/sse";
  }

  function _connect() {
    if (_eventSource) {
      try { _eventSource.close(); } catch (_) {}
    }

    var url = _buildUrl();

    _log("connecting to", url);

    // EventSource 不支援自訂 header，改用 URL query auth
    // Ntfy 支援 ?auth=Base64(user:pass) 格式
    if (_cfg.user && _cfg.pass) {
      var token = btoa(_cfg.user + ":" + _cfg.pass);
      url += (url.indexOf("?") >= 0 ? "&" : "?") + "auth=" + token;
    }

    try {
      _eventSource = new EventSource(url);
    } catch (e) {
      _warn("EventSource creation failed:", e);
      _scheduleReconnect();
      return;
    }

    _eventSource.onopen = function () {
      _log("connected");
      _connected = true;
      _reconnectMs = _cfg.reconnectBaseMs;
      _emit("connect", { server: _cfg.server, topic: _cfg.topic });
    };

    _eventSource.onmessage = function (event) {
      try {
        var data = JSON.parse(event.data);
        // Ntfy SSE 會送 keepalive 事件（event: keepalive）
        if (data.event === "keepalive" || data.event === "open") {
          _log("keepalive/open");
          return;
        }
        _handleMessage(data);
      } catch (e) {
        _log("parse error:", e, event.data);
      }
    };

    _eventSource.onerror = function (e) {
      _log("connection error", e);
      _connected = false;
      _emit("disconnect", { reason: "error" });
      try { _eventSource.close(); } catch (_) {}
      _eventSource = null;
      _scheduleReconnect();
    };
  }

  function _handleMessage(data) {
    var msg = {
      id: data.id || "",
      time: data.time ? new Date(data.time * 1000) : new Date(),
      title: data.title || "",
      message: data.message || "",
      priority: data.priority || 3,
      tags: data.tags || [],
      click: data.click || "",
      attachment: data.attachment || null,
      actions: data.actions || [],
      raw: data,
    };

    _log("message:", msg.title || msg.message);

    // 加入歷史
    _history.unshift(msg);
    if (_history.length > _cfg.maxHistory) {
      _history = _history.slice(0, _cfg.maxHistory);
    }

    // 顯示系統通知
    _showNotification(msg);

    // 觸發回調
    _emit("message", msg);
  }

  function _scheduleReconnect() {
    if (_reconnectTimer) clearTimeout(_reconnectTimer);
    _log("reconnecting in", _reconnectMs, "ms");
    _reconnectTimer = setTimeout(function () {
      _reconnectTimer = null;
      _connect();
    }, _reconnectMs);
    // 指數退避
    _reconnectMs = Math.min(_reconnectMs * 1.5, _cfg.reconnectMaxMs);
  }

  // ── iOS PWA 引導 ──────────────────────────────────────────────

  function _showIOSGuide() {
    if (!_isIOS() || _isPWA()) return false;

    var overlay = document.createElement("div");
    overlay.id = "zw-pwa-guide";
    overlay.style.cssText = [
      "position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;",
      "background:rgba(0,0,0,0.85);display:flex;align-items:center;",
      "justify-content:center;padding:20px;font-family:-apple-system,sans-serif;",
    ].join("");

    overlay.innerHTML = [
      '<div style="background:#fff;border-radius:16px;padding:32px 24px;max-width:340px;text-align:center;">',
      '  <div style="font-size:48px;margin-bottom:12px;">\uD83D\uDCF1</div>',
      '  <h2 style="margin:0 0 8px;font-size:20px;color:#1a1a1a;">\u52A0\u5165\u4E3B\u756B\u9762</h2>',
      '  <p style="margin:0 0 16px;font-size:14px;color:#666;line-height:1.5;">',
      '    \u8ACB\u9EDE\u64CA Safari \u5E95\u90E8\u7684 <strong style="font-size:20px;">\u2B06\uFE0F</strong> \u5206\u4EAB\u6309\u9215\uFF0C',
      '    \u7136\u5F8C\u9078\u64C7\u300C<strong>\u52A0\u5165\u4E3B\u756B\u9762</strong>\u300D\uFF0C',
      '    \u5373\u53EF\u63A5\u6536\u5373\u6642\u901A\u77E5\u3002',
      '  </p>',
      '  <div style="background:#f5f5f5;border-radius:8px;padding:12px;margin-bottom:16px;">',
      '    <div style="font-size:12px;color:#999;margin-bottom:4px;">Step 1</div>',
      '    <div style="font-size:14px;">Safari \u2192 \u2B06\uFE0F \u5206\u4EAB</div>',
      '    <div style="font-size:12px;color:#999;margin:8px 0 4px;">Step 2</div>',
      '    <div style="font-size:14px;">\u52A0\u5165\u4E3B\u756B\u9762 \u2192 \u65B0\u589E</div>',
      '    <div style="font-size:12px;color:#999;margin:8px 0 4px;">Step 3</div>',
      '    <div style="font-size:14px;">\u5F9E\u684C\u9762\u958B\u555F App</div>',
      '  </div>',
      '  <button id="zw-pwa-guide-close" style="',
      '    background:#2563eb;color:#fff;border:none;border-radius:8px;',
      '    padding:10px 24px;font-size:15px;cursor:pointer;width:100%;">',
      '    \u6211\u77E5\u9053\u4E86',
      '  </button>',
      '</div>',
    ].join("");

    document.body.appendChild(overlay);
    document.getElementById("zw-pwa-guide-close").onclick = function () {
      overlay.remove();
      localStorage.setItem("zw_pwa_guide_dismissed", "1");
    };

    return true;
  }

  // ── Ntfy App Fallback（iOS 推播不穩定時）────────────────────

  function _getNtfyAppLink() {
    var base = _cfg.server.replace(/\/+$/, "");
    var topic = _cfg.topic;
    if (_cfg.user && _cfg.pass) {
      var token = btoa(_cfg.user + ":" + _cfg.pass);
      return "ntfy://" + base.replace(/^https?:\/\//, "") + "/" + topic + "?auth=" + token;
    }
    return "ntfy://" + base.replace(/^https?:\/\//, "") + "/" + topic;
  }

  // ── 公開 API ──────────────────────────────────────────────────

  var ZheweiPush = {

    /**
     * 初始化推播模組
     * @param {Object} opts - 配置選項
     * @param {string} opts.topic - Ntfy topic（必填）
     * @param {string} [opts.server] - Ntfy 伺服器 URL
     * @param {string} [opts.user] - 唯讀帳號
     * @param {string} [opts.pass] - 唯讀密碼
     * @param {Function} [opts.onMessage] - 訊息回調
     * @param {Function} [opts.onConnect] - 連線回調
     * @param {Function} [opts.onDisconnect] - 斷線回調
     * @param {boolean} [opts.debug] - 除錯模式
     */
    init: function (opts) {
      if (!opts || !opts.topic) {
        _warn("topic is required");
        return Promise.resolve({ ok: false, error: "topic is required" });
      }

      // 合併配置
      _cfg = Object.assign({}, DEFAULTS, opts);

      // 註冊快捷回調
      if (typeof opts.onMessage === "function") {
        _listeners.message.push(opts.onMessage);
      }
      if (typeof opts.onConnect === "function") {
        _listeners.connect.push(opts.onConnect);
      }
      if (typeof opts.onDisconnect === "function") {
        _listeners.disconnect.push(opts.onDisconnect);
      }

      _log("init", { server: _cfg.server, topic: _cfg.topic, platform: ZheweiPush.platform() });

      // iOS 非 PWA：顯示引導
      if (_isIOS() && !_isPWA()) {
        if (!localStorage.getItem("zw_pwa_guide_dismissed")) {
          _showIOSGuide();
        }
      }

      // 請求通知權限 → 建立 SSE 連線
      return _requestPermission().then(function (granted) {
        _log("permission:", granted);
        _connect();
        return {
          ok: true,
          platform: ZheweiPush.platform(),
          permissionGranted: granted,
          topic: _cfg.topic,
        };
      });
    },

    /** 斷開連線 */
    disconnect: function () {
      if (_reconnectTimer) {
        clearTimeout(_reconnectTimer);
        _reconnectTimer = null;
      }
      if (_eventSource) {
        try { _eventSource.close(); } catch (_) {}
        _eventSource = null;
      }
      _connected = false;
      _emit("disconnect", { reason: "manual" });
      _log("disconnected");
    },

    /** 重新連線 */
    reconnect: function () {
      ZheweiPush.disconnect();
      _reconnectMs = _cfg.reconnectBaseMs;
      _connect();
    },

    /** 切換 topic（自動重連） */
    switchTopic: function (newTopic) {
      if (!newTopic) return;
      _cfg.topic = newTopic;
      ZheweiPush.reconnect();
      _log("switched to topic:", newTopic);
    },

    /**
     * 註冊事件監聽
     * @param {string} event - message | connect | disconnect | error | permission
     * @param {Function} fn - 回調函式
     */
    on: function (event, fn) {
      if (_listeners[event] && typeof fn === "function") {
        _listeners[event].push(fn);
      }
    },

    /** 移除事件監聽 */
    off: function (event, fn) {
      if (_listeners[event]) {
        _listeners[event] = _listeners[event].filter(function (f) { return f !== fn; });
      }
    },

    /** 取得訊息歷史 */
    getHistory: function () { return _history.slice(); },

    /** 清除訊息歷史 */
    clearHistory: function () { _history = []; },

    /** 取得連線狀態 */
    isConnected: function () { return _connected; },

    /** 取得平台資訊 */
    platform: function () {
      if (_isIOS()) return _isPWA() ? "ios-pwa" : "ios-browser";
      if (_isAndroid()) return _isPWA() ? "android-pwa" : "android-browser";
      return "desktop";
    },

    /** 取得 Ntfy App 深連結（iOS fallback 用） */
    getNtfyAppLink: function () { return _getNtfyAppLink(); },

    /** 手動觸發通知（測試用） */
    testNotification: function (title, body) {
      _handleMessage({
        id: "test-" + Date.now(),
        time: Math.floor(Date.now() / 1000),
        title: title || "\u6E2C\u8A66\u901A\u77E5",
        message: body || "\u9019\u662F\u4E00\u5247\u6E2C\u8A66\u901A\u77E5\uFF0C\u5982\u679C\u60A8\u770B\u5230\u4EE3\u8868\u63A8\u64AD\u6A21\u7D44\u904B\u4F5C\u6B63\u5E38\u3002",
        priority: 3,
        tags: ["test"],
      });
    },

    /**
     * 透過後端 API 發送推播（需 admin 權限）
     * @param {Object} payload - { topic, title, message, priority, tags, click }
     * @param {string} [apiBase] - 後端 API 基底 URL
     */
    send: function (payload, apiBase) {
      var base = (apiBase || "").replace(/\/+$/, "") || "";
      var token = localStorage.getItem("jarvis_token") || "";
      return fetch(base + "/api/ntfy/send", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": token ? ("Bearer " + token) : "",
        },
        body: JSON.stringify(payload),
      }).then(function (resp) {
        return resp.json();
      }).catch(function (e) {
        return { ok: false, error: e.message };
      });
    },

    /** 取得當前配置（除密碼外） */
    getConfig: function () {
      return {
        server: _cfg.server,
        topic: _cfg.topic,
        user: _cfg.user,
        brand: _cfg.brand,
        debug: _cfg.debug,
        maxHistory: _cfg.maxHistory,
      };
    },

    /** 版本 */
    version: "1.0.0",
  };

  return ZheweiPush;
});
