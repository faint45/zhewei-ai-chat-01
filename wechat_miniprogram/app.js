// app.js
App({
  onLaunch() {
    // 展示本地存储能力
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)

    // 登录
    wx.login({
      success: res => {
        // 发送 res.code 到后台换取 openId, sessionKey, unionId
        console.log('登录成功', res.code)
      }
    })
    
    // 检查网络状态
    this.checkNetworkStatus()
  },
  
  onShow() {
    console.log('小程序显示')
  },
  
  onHide() {
    console.log('小程序隐藏')
  },
  
  // 全局配置
  globalData: {
    userInfo: null,
    serverUrl: 'http://localhost:8003', // 远程控制服务器地址
    apiKey: 'zhuwei-tech-2026', // API密钥
    version: '1.0.0'
  },
  
  // 检查网络状态
  checkNetworkStatus() {
    wx.getNetworkType({
      success: (res) => {
        console.log('网络类型:', res.networkType)
        if (res.networkType === 'none') {
          wx.showToast({
            title: '网络连接失败',
            icon: 'none',
            duration: 2000
          })
        }
      }
    })
  },
  
  // 通用API调用方法
  callAPI(endpoint, data = {}, method = 'POST') {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${this.globalData.serverUrl}${endpoint}`,
        data: data,
        method: method,
        header: {
          'Content-Type': 'application/json',
          'Authorization': this.globalData.apiKey
        },
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data)
          } else {
            reject(new Error(`API错误: ${res.statusCode}`))
          }
        },
        fail: (err) => {
          reject(err)
        }
      })
    })
  },
  
  // 发送AI指令
  sendAICommand(command) {
    return this.callAPI('/api/command', {
      type: 'ai',
      command: command
    })
  },
  
  // 发送系统指令
  sendSystemCommand(command) {
    return this.callAPI('/api/command', {
      type: 'sys',
      command: command
    })
  },
  
  // 检查服务器状态
  checkServerStatus() {
    return this.callAPI('/health', {}, 'GET')
  }
})